#!/usr/bin/env python
# import pdb; pdb.set_trace()
import pdb
import os, errno, tempfile
import platform
import time
import string
from collections import OrderedDict
from threading import Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.events import LoggingEventHandler

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('lockbox')

import sys
from pyme import core, constants, errors, pygpgme
import pyme.constants.validity

if not core.check_version('1.3.0'):
    logger.error('this program is designed to run against GPGME version 1.3.0')
    exit()

if not core.engine_check_version(pygpgme.GPGME_PROTOCOL_OpenPGP):
    logger.error('According to my checks, you do not have GPG installed.  Or at least I was unable to find it.  This needs to be remedied')
    exit()

## TODO: check to see that gpg-agent is a) configured correctly and b) running
## TODO: on Mac OS, check that we're using FSEvents

OpenPGPInfo = [x for x in core.get_engine_info() if x.protocol == pygpgme.GPGME_PROTOCOL_OpenPGP][0]
logger.info('Using gpg version %s in %s', OpenPGPInfo.version, OpenPGPInfo.file_name)

logger.debug("starting...")


def email2key_for_encrypt_sign(gpgme_context, email):
    """try to get a gpgme_key_t (for passing in gpgme_op_encrypt_sign()'s array of recipients) from email address"""
    ## TODO: convert this loop into an iterator / generator of some sort.  this looks ugly.
    gpgme_context.op_keylist_start(email, 0)
    r = gpgme_context.op_keylist_next()
    some = (r != None)
    while some:
        if r.can_encrypt:
            if email in [x.email for x in r.uids]:
                return r
        r = gpgme_context.op_keylist_next()
        some = (r != None)
    return None

# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise

class LockboxOrderedDict(OrderedDict):
    def __init__(self):
        self.lock = Lock()
        OrderedDict.__init__(self)
    def first(self):
        i = iter(self).next()
        return (i, self[i])
    def __setitem__(self, key, value):
        with self.lock:
            if key in self:
                if self[key]['action'] in ('delete-cypher','delete-clear'):
                    ## err on the side of caution. if we get a later FS event saying a file has been created, then just replace this deletion in the queue
                    ## note that this update/insertion moves this key to the "back of the line"
                    del self[key]
                    OrderedDict.__setitem__(self, key, value)
                else:
                    self[key]['collided'] = True
            else:
                OrderedDict.__setitem__(self, key, value)
    def popitem(self, v):
        with self.lock:
            r = OrderedDict.popitem(self, v)
        return r

root_dir = '~'
if platform.system() == 'Windows':
    root_dir = os.path.join('~','Documents')

# TODO: make these configurable
ciphertext_dir = os.path.expanduser(os.path.join(root_dir, 'Dropbox'))
cleartext_dir = os.path.expanduser(os.path.join(root_dir,'Lockbox'))

## TODO: load up the queue with changes made since the last time we ran (do a directory scan, compare against what is stored in Clear-share/.lockbox/dircache

def common_handle_event(self, event, clear_or_cipher, action):
    if not event.is_directory and not event.src_path.endswith('.DS_Store'):
        if event.src_path.endswith('-from-dropbox-collision') or os.path.exists(event.src_path + '-from-dropbox-collision'):
            logger.info('Not going to work with %s due to presence of collision marker', event.src_path)
            return
        if clear_or_cipher == 'clear':
            stem_and_share = string.replace(event.src_path, self.cleartext_dir, '', 1)
        else:
            stem_and_share =  string.replace(event.src_path, self.ciphertext_dir, '', 1)
        if stem_and_share.startswith(os.sep):
            stem_and_share = stem_and_share[1:]
        stem_and_share = stem_and_share.split(os.sep)
        (share_name, stem) = (stem_and_share[0], os.path.join(*stem_and_share[1:]))
        if share_name.startswith('LOCKBOX-'):
            if clear_or_cipher == 'clear':
                # this probably isn't a necessary check, but whatevs
                logger.info('Not going to handle a share name in the Lockbox directory prefixed with LOCKBOX-: %s', event.src_path)
                return
            share_name = share_name[len('LOCKBOX-'):]
        self.q[stem] = { 'collided': False,
                         'action': action,
                         'stem': stem,
                         'share_name': share_name,
                         'cleartext_full_path': os.path.join(self.cleartext_dir, share_name, stem),
                         'ciphertext_full_path': os.path.join(self.ciphertext_dir, 'LOCKBOX-' + share_name, stem)
                        }        

## TODO: should be straight forward to consolidate these two handler classes

class CleartextEventHandler(LoggingEventHandler):
    def __init__(self, q, cleartext_dir, ciphertext_dir):
        self.q = q
        self.cleartext_dir = cleartext_dir
        self.ciphertext_dir = ciphertext_dir
        LoggingEventHandler.__init__(self)
    def on_moved(self, event):
        super(CleartextEventHandler, self).on_moved(event)
        logger.error('Not sure what to do with an on_moved event on %s', event.src_path)
    def on_created(self, event):
        super(CleartextEventHandler, self).on_created(event)
        common_handle_event(self, event, 'clear', 'encrypt')
    def on_deleted(self, event):
        super(CleartextEventHandler, self).on_deleted(event)
        common_handle_event(self, event, 'clear', 'delete-cipher')
    def on_modified(self, event):
        super(CleartextEventHandler, self).on_modified(event)
        common_handle_event(self, event, 'clear', 'encrypt')
        
class CiphertextEventHandler(LoggingEventHandler):
    def __init__(self, q, cleartext_dir, ciphertext_dir):
        self.q = q
        self.cleartext_dir = cleartext_dir
        self.ciphertext_dir = ciphertext_dir
        LoggingEventHandler.__init__(self)
    def on_moved(self, event):
        super(CiphertextEventHandler, self).on_moved(event)
        logger.error('Not sure what to do with an on_moved event on %s', event.src_path)
    def on_created(self, event):
        super(CiphertextEventHandler, self).on_created(event)
        common_handle_event(self, event, 'cipher', 'decrypt')
    def on_deleted(self, event):
        super(CiphertextEventHandler, self).on_deleted(event)
        common_handle_event(self, event, 'cipher', 'delete-clear')
    def on_modified(self, event):
        super(CiphertextEventHandler, self).on_modified(event)
        common_handle_event(self, event, 'cipher', 'decrypt')

def main():

    q = LockboxOrderedDict()
    observer = Observer()
    observer.schedule(CleartextEventHandler(q, cleartext_dir, ciphertext_dir), path=cleartext_dir, recursive=True)
    observer.schedule(CiphertextEventHandler(q, cleartext_dir, ciphertext_dir), path=ciphertext_dir, recursive=True)
    observer.start()

    gpgme_context = core.Context()
    #gpgme_context.set_armor(1)
    ## TODO: read this on a per-queue-entry basis from Clear-share/.lockbox/config.yml
    keys = [email2key_for_encrypt_sign(gpgme_context, 'jason@jwoodward.com')]

    try:
        while True:
            time.sleep(1)
            try:
                while True:
                    (stem, deets) = q.first()
                    logger.debug('%s %s', stem, deets)
                    if not deets['collided']:
                        check_for_collided_after_operation = False
                        if deets['action'] == 'encrypt':
                            logger.debug('encrypting from %s to %s', deets['cleartext_full_path'], deets['ciphertext_full_path'])
                            check_for_collided_after_operation = True
                            target_path = deets['ciphertext_full_path']
                            (tmp_fd, tmp_path) = tempfile.mkstemp()
                            os.close(tmp_fd)
                            ## TODO: handle multiple recipients
                            ## TODO: handle failure of encryption
                            inf = open(deets['cleartext_full_path'], 'rb')
                            inf_d = core.Data(file=inf)
                            outf = open(tmp_path,'w+b')
                            outf_d = core.Data(file=outf)
                            x = gpgme_context.op_encrypt_sign(keys, core.pygpgme.GPGME_ENCRYPT_ALWAYS_TRUST,
                                                              inf_d, outf_d )
                            outf.flush()
                            outf.close()
                            inf.close()
                        elif deets['action'] == 'decrypt':
                            logger.debug('decrypting from %s to %s', deets['ciphertext_full_path'], deets['cleartext_full_path'])
                            check_for_collided_after_operation = True
                            target_path = deets['cleartext_full_path']
                            (tmp_fd, tmp_path) = tempfile.mkstemp()
                            os.close(tmp_fd)
                            ## TODO: handle failure of decryption
                            inf = open(deets['ciphertext_full_path'], 'rb')
                            inf_d = core.Data(file=inf)
                            outf = open(tmp_path, 'w+b')
                            outf_d = core.Data(file=outf)
                            gpgme_context.op_decrypt_verify(inf_d,outf_d)
                            outf.flush()
                            outf.close()
                            inf.close()
                        elif deets['action'] == 'delete-cipher':
                            logger.debug('deleting %s', deets['ciphertext_full_path'])
                            if os.path.exists(deets['ciphertext_full_path']):
                                os.unlink(deets['ciphertext_full_path'])

                        elif deets['action'] == 'delete-clear':
                            logger.debug('deleting %s', deets['cleartext_full_path'])
                            if os.path.exists(deets['cleartext_full_path']):
                                os.unlink(deets['cleartext_full_path'])

                        else:
                            logger.error('Unknown action %s on %s', deets['action'], deets)

                        if check_for_collided_after_operation:
                            ## now, if it got marked as collided in the interim while we were encrypting/decrypting then we don't want to overwrite 
                            time.sleep(0)  ## http://stackoverflow.com/questions/787803/how-does-a-threading-thread-yield-the-rest-of-its-quantum-in-python
                            (stem, deets) = q.popitem(False)
                            if not deets['collided']:
                                ## move from temp location to real location
                                if platform.system() == 'Windows':
                                    ## TODO: this can throw an exception on windows if the target_place is locked.  need to think about how to deal with this
                                    if os.path.exists(target_path):
                                        logger.debug('windows only: unlink %s', target_path)
                                        os.unlink(target_path)
                                logger.debug('rename %s to %s', tmp_path, target_path)
                                mkdir_p(os.path.dirname(target_path))
                                os.rename(tmp_path, target_path)
                            else:
                                ## TODO: if it was a decrypt, move the newly decrypted file to stem-from-dropbox-collision
                                ##       if it was an encrypt, immediately decrypt ciphertext version to stem-from-dropbox-collision
                                ## TODO: delete tmp_path in the case that we're no longer using it (it was an encrypt that we no longer can copy to the ciphertext location)
                                pass
                    else:
                        if deets['action'] in ('delete-clear','delete-cipher'):
                            logger.error('should not get a collided delete because they should be removed from the queue in our OrderedDict subclass')
                        else:
                            ## TODO: immediately decrypt and put it into stem-from-dropbox-collision
                            pass

            except StopIteration:
                #print "nada"
                pass
    except KeyboardInterrupt:
        pass
    observer.stop()
    observer.join()


## TODO: daemonize / other pretty os-dependent thingies (menu bar, dock, etc)
## TODO: add a WHAT-IS-THIS-SHARE.txt file with a description of the Lockbox project

if __name__ == "__main__":
    main()

