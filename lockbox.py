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

import M2Crypto
from M2Crypto import BIO, EVP, Rand, m2

## TODO: on Mac OS, check that we're using FSEvents

logger.info('Using m2crypto version %s with %s', M2Crypto.version, m2.OPENSSL_VERSION_TEXT)

logger.debug("starting...")

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
        if stem.startswith('.lockbox'):
            logger.info("Not going to handle .lockbox config directories")
            return
        self.q[stem] = { 'collided': False,
                         'action': action,
                         'stem': stem,
                         'share_name': share_name,
                         'config_dir_path': os.path.join(self.cleartext_dir, share_name, '.lockbox'),
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

## http://code.activestate.com/recipes/510399-byte-to-hex-and-hex-to-byte-string-conversion/
def ByteToHex( byteStr ):
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """
    return ''.join( [ "%02X" % ord( x ) for x in byteStr ] ).strip()

def HexToByte( hexStr ):
    """
    Convert a string hex byte values into a byte string. The Hex Byte values may
    or may not be space separated.
    """
    bytes = []

    hexStr = ''.join( hexStr.split(" ") )

    for i in range(0, len(hexStr), 2):
        bytes.append( chr( int (hexStr[i:i+2], 16 ) ) )

    return ''.join( bytes )

def main():

    q = LockboxOrderedDict()
    observer = Observer()
    observer.schedule(CleartextEventHandler(q, cleartext_dir, ciphertext_dir), path=cleartext_dir, recursive=True)
    observer.schedule(CiphertextEventHandler(q, cleartext_dir, ciphertext_dir), path=ciphertext_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
            try:
                while True:
                    (stem, deets) = q.first()  #just read, don't pop here because we need it to stay in the OrderedDict in case another event comes in on this file before we're done
                    logger.debug('%s %s', stem, deets)
                    if not deets['collided']:
                        check_for_collided_after_operation = False
                        if deets['action'] == 'encrypt':
                            logger.debug('encrypting from %s to %s', deets['cleartext_full_path'], deets['ciphertext_full_path'])
                            check_for_collided_after_operation = True
                            target_path = deets['ciphertext_full_path']
                            (tmp_fd, tmp_path) = tempfile.mkstemp()
                            os.close(tmp_fd)


                            rio = BIO.openfile(deets['cleartext_full_path'], 'rb')
                            rio.write_close()
                            wrio = BIO.openfile(tmp_path, 'wb')

                            cf = BIO.CipherStream(wrio)

                            salt = Rand.rand_pseudo_bytes(8)[0]
                            logger.debug("salt=%s",ByteToHex(salt))

                            passphrase_f = open(os.path.join(deets['config_dir_path'], 'key.txt'), 'r')  ## TODO cache this
                            passphrase = passphrase_f.readline().rstrip()
                            passphrase_f.close()

                            (key, iv) = m2.bytes_to_key(m2.aes_256_cbc(), m2.md5(), passphrase, salt, 1)
                            logger.debug("key=%s", ByteToHex(key))
                            logger.debug("iv=%s", ByteToHex(iv))

                            cf.set_cipher('aes_256_cbc', key, iv, 1)
                            wrio.write('Salted__')  # magic - see openssl's enc.c
                            wrio.write(salt)

                            while True:
                                out = rio.read(4096)
                                if not out:
                                    break
                                cf.write(out)

                            cf.flush()
                            cf.write_close()
                            cf.close()
                            wrio.flush()
                            wrio.write_close()
                            wrio.close()

                        elif deets['action'] == 'decrypt':
                            logger.debug('decrypting from %s to %s', deets['ciphertext_full_path'], deets['cleartext_full_path'])
                            check_for_collided_after_operation = True
                            target_path = deets['cleartext_full_path']
                            (tmp_fd, tmp_path) = tempfile.mkstemp()
                            os.close(tmp_fd)
                            ## TODO: handle failure of decryption

                            rio = BIO.openfile(deets['ciphertext_full_path'], 'rb')
                            rio.write_close()
                            wrio = BIO.openfile(deets['cleartext_full_path'], 'wb')

                            cf = BIO.CipherStream(wrio)

                            header = rio.read(size=len('Salted__'))
                            if header != 'Salted__':
                                print "uh, this doesn't look like an encrypted file"
                                exit()
                            salt = rio.read(size=8)
                            logger.debug("salt=%s",ByteToHex(salt))

                            passphrase_f = open(os.path.join(deets['config_dir_path'], 'key.txt'), 'r')  ## TODO cache this
                            passphrase = passphrase_f.readline().rstrip()
                            passphrase_f.close()

                            (key, iv) = m2.bytes_to_key(m2.aes_256_cbc(), m2.md5(), passphrase, salt, 1)
                            logger.debug("key=%s", ByteToHex(key))
                            logger.debug("iv=%s", ByteToHex(iv))

                            cf.set_cipher('aes_256_cbc', key, iv, 0)

                            while True:
                                out = rio.read(4096)
                                if not out:
                                    break
                                cf.write(out)

                            cf.flush()
                            cf.write_close()
                            cf.close()
                            wrio.flush()
                            wrio.write_close()
                            wrio.close()


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

                        time.sleep(0)  ## http://stackoverflow.com/questions/787803/how-does-a-threading-thread-yield-the-rest-of-its-quantum-in-python
                        (stem, deets) = q.popitem(False)

                        if check_for_collided_after_operation:
                            ## now, if it got marked as collided in the interim while we were encrypting/decrypting then we don't want to overwrite 
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
                        (stem, deets) = q.popitem(False)
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

