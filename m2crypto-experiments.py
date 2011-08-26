from M2Crypto import BIO, EVP, Rand, m2
import os

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


rio = BIO.openfile(os.path.expanduser('~/Lockbox/foobar/firsttest.txt'), 'rb')
rio.write_close()
wrio = BIO.openfile(os.path.expanduser('~/Dropbox/LOCKBOX-foobar/firsttest.txt'), 'wb')

cf = BIO.CipherStream(wrio)

salt = Rand.rand_pseudo_bytes(8)[0]
#salt = '\x00\x00\x00\x00\x00\x00\x00\x00'
print "salt=%s" % ByteToHex(salt)

passphrase = 'foo bar'

(key, iv) = m2.bytes_to_key(m2.aes_256_cbc(), m2.md5(), passphrase, salt, 1)
print "key=%s" % ByteToHex(key)
print "iv=%s" % ByteToHex(iv)

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






print "Encrypted... now Decrypting..."



rio = BIO.openfile(os.path.expanduser('~/Dropbox/LOCKBOX-foobar/firsttest.txt'), 'rb')
rio.write_close()
wrio = BIO.openfile(os.path.expanduser('~/Lockbox/foobar/firsttest.txt-new'), 'wb')


## read salt from RIO stream
header = rio.read(size=len('Salted__'))
if header != 'Salted__':
    print "uh, this doesn't look like an encrypted file"
    exit()
salt = rio.read(size=8)
print "salt=%s" % ByteToHex(salt)

cf = BIO.CipherStream(wrio)


(key, iv) = m2.bytes_to_key(m2.aes_256_cbc(), m2.md5(), passphrase, salt, 1)
print "key=%s" % ByteToHex(key)
print "iv=%s" % ByteToHex(iv)

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
wrio.close()

