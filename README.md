About
=====

The primary goal of this project is to provide [Dropbox](http://db.tt/nN0Obnw) users with
end-to-end strong encryption of a portion of their documents with a
user experience which matches the normal Dropbox experience as closely
as possible, including Dropbox's superb sharing experience.

The strategy is to create a watched folder, similar to the existing
Dropbox folder, in which changed files get encrypted and copied into
the Dropbox folder.  Files updated in the Dropbox folder are decrypted
and copied to the lockbox folder when they're updated.

Your entire Dropbox is not encrypted with lockbox.  Only files stored
in the special lockbox directory are encrypted. 

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
would otherwise have the legitimate ability to read your data.

This makes some folks uncomfortable.  The lockbox software's goal is
eliminate this uncertainty of who can read your data, while
maintaining the Just Works (tm) semantics of regular Dropbox.

Other Strategies
================

The approach taken by this software isn't the only one you can take,
but we think it has advantages over some of the other ways.

* TrueCrypt volume in your Dropbox - has trouble with the cool sharing
  mechanism in DropBox
* Manual encryption of your files - lockbox more or less automates this
* Alternate providers like SpiderOak - sharing isn't as dead simple as Dropbox

Requirements
============

This is a very early version.  While some bits are configurable I
wouldn't warrant this as generally user friendly yet.

Broadly, you'll need:

* ruby (I'm using 1.9.2 via rvm on Mac OS X 10.6.6)
* gpg2 (I'm using 2.0.17 from http://www.gpgtools.org/installer/index.html)

Installation
============

    $ git clone git://github.com/woodwardjd/lockbox.git
    $ cd lockbox
    $ bundle install

Then, edit lockbox.rb to change your paths and keynames (see?  told
you it wasn't very configurable yet).  Then run it.

    $ ruby lockbox.rb

Now, edit files inside your cleartext Lockbox directory (`~/Lockbox` by
default).  They'll be automatically encrypted and copied into your
ciphertext Lockbox directory (`~/Dropbox/Lockbox` by default).

Currently, this is only while the lockbox.rb program is running.  And
it doesn't decrypt yet.

TODO
====

* Configuration without editing the .rb file
* Multiple Lockbox directories instead of just the one (more suitable
  for using with Dropbox's fantastic sharing mechanism)
* Automatic discovery of multiple Lockbox directories
* Daemonizing / automatic startup
* selection of public key vs. symmetric key encryption (the latter
  being easier for some folks when sharing)
* Packaging of the software into an executable suitable for running
  standalone (without having to install dependencies) on multiple operating systems
* Updating the dependent gpgr gem to include the decryption functions
  built as part of this project
