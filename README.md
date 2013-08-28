About
=====

The primary goal of this project is to provide [Dropbox](http://db.tt/nN0Obnw) users with
end-to-end strong encryption of a portion of their documents with a
user experience which matches the normal Dropbox experience as closely
as possible, including Dropbox's superb sharing experience.

The strategy is to create a watched folder, similar to the existing
Dropbox folder, in which changed files get encrypted and copied into
the Dropbox folder.  Files updated in the Dropbox folder are decrypted
and copied to the Lockbox folder when they're updated.

Your entire Dropbox is not encrypted with Lockbox.  Only files stored
in the special Lockbox directory are encrypted. 

Motivation
==========

Dropbox provides an excellent service.  Notably, its user experience
is refined to the point where it Just Works (tm).  This includes the
single-user experience and when sharing a folder among collaborators.

The Dropbox architecture and team have gone to great lengths to make
it extremely difficult for unauthorized individuals to read the files
you store on their service.

However, it is still possible for individuals to read your files
without your authorization.  In particular, Dropbox employees have
this ability even though they are limited by strict policy and access
control mechanisms.  By extension, your data could be read by other
parties under a number of circumstances, including court order (public
or secret), or through social engineering attacks on individuals who
would otherwise have the legitimate ability to read your data. Indeed, [Kholia and Węgrzyn, 2013](https://www.usenix.org/system/files/conference/woot13/woot13-kholia.pdf) show it is (was) possible to hijack Dropbox folders on a LAN.

This makes some folks uncomfortable.  The Lockbox software's goal is
eliminate this uncertainty of who can read your data, while
maintaining the Just Works (tm) semantics of regular Dropbox.

Other Strategies
================

The approach taken by this software isn't the only one you can take,
but we think it has advantages over some of the other ways.

* TrueCrypt volume in your Dropbox - has trouble with the cool sharing
  mechanism in DropBox
* Manual encryption of your files - Lockbox more or less automates this
* Alternate providers like SpiderOak - sharing isn't as dead simple as Dropbox

Requirements
============

This is still a very early version.  While some bits are configurable I
wouldn't warrant this as generally user friendly yet.

Broadly, you'll need the following, in this order more or less:

* python (I'm using 2.7.1 via pythonbrew on Mac OS X 10.6.8)
* distribute and pip as described in the [Prerequisites and Using the installer sections](http://www.pip-installer.org/en/latest/installing.html)
* On Windows, install PyYAML 3.10 [from their installer](http://pyyaml.org/wiki/PyYAML)
* [watchdog](http://pypi.python.org/pypi/watchdog), on Mac OS you'll
  need the latest
  [version from github](https://github.com/gorakhargosh/watchdog).
  This is for the working FSEvents-based observer.  The kqueue
  observer can easily get overwhelmed with many files in your Dropbox
* m2crypto 0.21.1 with a patch
* their dependencies (including Xcode for installing brew)

On Windows I built the C modules (m2crypto, etc) and installer using the
(MinGW toolchain)[http://www.mingw.org/]. See the file
installer_development_notes.md for more details

A note on the Mac OS build environment:  There's a good chance this'll
work with the apple-shipped version of python.  However, I haven't
delved too deeply into making that happen, notably because the
[GPGTools builds](http://www.gpgtools.org/) weren't universal (i386
and x86_64) last time I worked with them, and python.org's 2.7 seemed
to ship x86_64 only.  That's a TODO to cut down on having to build
your own python.  Probably pretty straight forward, but it isn't a
priority for me right now.

Installation
============

First, install all the stuff as seen in Requirements above. Setup.py
is pretty much just a stub right now, and doesn't do much.

    $ git clone git://github.com/woodwardjd/lockbox.git
    $ cd lockbox

Then, edit lockbox.py to change your default paths and keynames (see?  told
you it wasn't very configurable yet).  Then run it.

    $ python lockbox.py

Now, edit files inside your cleartext Lockbox directory (`~/Lockbox` by
default).  Folders (called "shares") in this directory map to folders
in your Dropbox, with LOCKBOX- prepended to the name.  When you
edit files in these directories they'll be automatically encrypted and
copied into the associated ciphertext Lockbox directory.  For
instance, `~/Lockbox/secretproject/stuff/information.txt` will get encrypted
to `~/Dropbox/LOCKBOX-secretproject/stuff/information.txt`.  

When friends share a new LOCKBOX- prefixed folder with you in Dropbox
(using Dropbox's regular sharing mechanism) Lockbox will automatically
detect that and begin decrypting its contents, assuming you and your
friend have already exchanged encryption keys, and your friend has
configured their copy of Lockbox to specify you as a recipient.

Currently, Lockbox does not start up automatically or run in the
background.  You'll need to start it manually and keep it running.  It
will, however, catch up when you run it next time.

Finally, the encryption scheme isn't necessarily upgrade friendly
yet.  What I mean by this is several things.  First, it is currently
not possible to have two or more people using a Dropbox share with
Lockbox versions that don't match.  Second, since the encryption and
configuration formats have yet to stablize there is a chance that
you'll have to delete the encrypted version (in Dropbox) completely
upon a future Lockbox upgrade (though this absolutely does not mean
you have to delete files in the Lockbox folder!)

TODO
====

In no particular order, though mostly from more important/likely to be
implemented to less important/likely to be implemented.

* Recipient key configuration in Lockbox/ShareName/.lockbox/config.yml
* Daemonizing / automatic startup, with catch-up to account for
  changes made while Lockbox isn't running
* Cut down on the amount of non-stock building of python, etc that
  is recommended above
* addition of public key encryption
* Encrypt filenames
* Pretty OS-specific eye candy (system tray applet, menu bar applet, etc)

Random History Notes
====================
* Had a lot of trouble working with the combination of gpg, gpg-agent,
  passphrase callbacks and such, so I switched to m2crypto which uses
  the openssl libs for the cryptography operations
* Switched from asymmetric keys to symmetric key encryption to
  simplify early version usability
* The first version (0.0.0) I wrote was in Ruby, but I abandoned that
  for Python soon after the proof of concept was built due to what
  seemed like better OS-specific packaging and distribution
  capabilities in the Python world. YMMV.
