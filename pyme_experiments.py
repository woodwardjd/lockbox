import sys
from pyme import core, constants

if not core.check_version('1.3.0'):
    logger.error('this program is designed to run against GPGME version 1.3.0')
    exit()


# Set up our input and output buffers.
 
plain = core.Data('This is my message.')
plain = core.Data(file='/Users/jdw5/Lockbox/foobar/firsttest.txt')
outf = open('/Users/jdw5/out.t','wb')
cipher = core.Data(file=outf)
 
# Initialize our context.
 
c = core.Context()
c.set_armor(1)
 
# Set up the recipients.
 
#sys.stdout.write("Enter name of your recipient: ")
#name = sys.stdin.readline().strip()
name = 'jason@jwoodward.com'
c.op_keylist_start(name, 0)
r = c.op_keylist_next()
 
# Do the encryption.
 
c.op_encrypt_sign([r], 1, plain, cipher)
#cipher.seek(0,0)
#print cipher.read()
outf.flush()
outf.close()
