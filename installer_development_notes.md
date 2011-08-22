Mac OS Building Notes
=====================

At first I had a tester using Mac OS 10.5 so I endeavoured to build
the C components of this system (python, gpgme, etc) as universal
binaries for 10.5 and 10.6, i386 and x86_64. Since that time she's
upgraded to 10.6 so I no longer am personally testing on that
platform. Additionally, 10.7 has come out, and I haven't tested there
yet, either.  Here's some notes, though, that I took while getting an
early version to run on 10.5

pythonbrew install --as="2.7.1univ" --configure="--enable-shared --with-universal-archs=intel --enable-universalsdk=/" 2.7.1
get pip:
curl -O http://python-distribute.org/distribute_setup.py
python distribute_setup.py
curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
python get-pip.py


brewed i386/x86_64 (-mmacosx-version-min=10.5 -arch i386 -arch x86_64):
libassuan
gnupg
gpgme
libgpg-error

when building pyme I had to export CFLAGS="-O -mmacosx-version-min=10.5 -arch i386 -arch x86_64"


Windows Building Notes
======================

* Win7Pro x86_64
* installed MinGW tools (20110802) to c:\MinGW, got the latest
  catalog, installed everything except fortran and objc
* installed Python 2.7.2 from python.org (which is a 32bit python)
* built libgpg-error 1.10 with ./configure ; make ; make install in
  the MinGW shell.  It hung on po/pl.po and pl/ru.po, but killed the
  iconv.exe program hanging and it finished the install just fine
* built libassuan 2.02, gpgme 1.3.1, pcre-8.13, swig-2.04 with
  ./configure ; make ; make install in the MinGW shell.
* building pyme was a little bit more complicated.  Starting with the
  stock pyme 0.8.1 I had to do the following.  Might have fixed this
  in [my version](https://github.com/woodwardjd/pyme), though, by the time you read this.
  This is all in the MinGW shell.
  * edit Makefile to set swig path
  * before running make, exported c:\MinGW\msys\1.0\local\include in
    C_INCLUDE_PATH
  * before running make, exported c:\MinGW\msys\1.0\local\lib in
    LIBRARY_PATH
  * ran make 
  * edit setup.py to add libassuan in the list of DLLs to pull in
  * python setup.py bdist_wininst
  * run the resulting installer .exe it builds in ./dist
* PyYAML 3.10 (needed by Watchdog) needs to be installed by its .exe
  installer on windows (building it was unsuccessful)
    
