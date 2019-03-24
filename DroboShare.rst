
Droboshare Support
------------------

Droboshare is not directly supported by drobo utils running on a linux host.
However, the droboshare itself is a linux host, and it is possible to run
drobo-utils un-modified on the droboshare itself.  A python interpreter is needed
to run drobo-utils.  A python interpreter has, itself, a number of dependencies.
So you number of packages need to be installed on the droboshare.
This is where DARFS comes in.

DARFS
=====
The Droboshare Augmented Root File System (darfs) is a 60 MB or so download
you can get from drobo-utils.sf.net.  There isn't any source code, because,
well, nothing from any of the packages has been modified.  there are
instructions on how to build DARFS in DEVELOPERS_

DARFS is a standard droboshare root file system, with some packages added:
openssl, openssh, berkeleydb, bzip2, a fairly complete Python 2.6.2.  drobo-
utils is a python app. and it works in line and API mode, natively, on
the droboshare.  for example, I've used it to replace the firmware. no
problem at all.

People un-afraid of the command line can upgrade drobo firmware, query
status, and take diagnositc dumps, from the command line on the droboshare
itself, just as they would on any linux host computer.  But a full GUI
would be too much for the little processor and more importantly the limited
memory in the droboshare, so that is not provided.

DARFS Installation
==================
Download it from drobo-utils.sf.net:
steps:

   1. copy the tar file onto somewhere on your share.
   2. log in via DropBear ssh as a root user on the droboshare.
   3. cd /mnt/DroboShares/YourDrobo (root of drobo file system, for example)
   4. tar -xzf darfs.tgz (root of drobo file system, for example)
   5. the root directory of the tar is 'slash'.. it will be under YourDrobo
   6. export PATH="/mnt/DroboShares/YourDrobo/slash/usr/bin:${PATH}"  (which is where python and drobom are.)
   7. drobom status

you're done!

Enable SFTP Support
===================

all you need to do is:

ln -s /usr/libexec /mnt/Droboshares/YourDrobo/slash/usr/libexec

Try an sftp from another machine (as root...) and it ought to work.

(explanation: when one tries to sftp to a droboshare, it gives an error
about trying to exec '/usr/libexec/sftp-server'.  Openssh builds the
right binary, but Dropbear doesn't know where to look for it.  the
libexec directory isn't there on the droboshare, so there is no harm
in creating it and linking into DARFS.)


Droboshare Firmware
===================

With DARFS, and the third party software you can get from drobospace and
drobo.com, the droboshare is very open and hackable.   However, there
remains a one limitation: There is no open source way to upgrade or modify
droboshare firmware.  If you want to re-flash to a factory original
state, you need the vendor dashboard.



Building DARFS or a Droboshare Development Environment
------------------------------------------------------

DARFS was build in late 2008 as a technology demonstration.  There was not
much interest at the time, so it has not been followed up since that time.
If there is sufficient interest, may take it up again.  The quality of the
build documentation procedure is, well, poor.  It would have been necessary
to perform the entire procedure from scratch to verify the details.  The
information here is basically notes to the author.  YMMV.

I used this procedure on ubuntu jaunty, but the same packages ought to work
identically on Debian Lenny.  the idea here is to use the fabulous scratchbox2_
tools developed [#recipe]_ for use with the Nokia Maemo.

.. _scratchbox2: http://www.freedesktop.org/wiki/Software/sbox2

.. [#recipe] http://www.linux-archive.org/ubuntu-mobile-embedded/332-building-packages-chinook-armel-scratchbox2.html

Cross compiling is usually a PITA (excuse me.) you want to use a nice fast,
powerful desktop machine (the "host") to compile something that will run on a
much less muscular embedded systems (the "target")  Scratchbox 2 looks at a
binary, and if it is for the target cpu to run, then it invokes the qemu
processor emulator so that it will run on the host platform under emulation.
When the binary found is a host binary, it just runs it normally.  This makes
cross-compilation very transparent.  The other magick that it does is to
invoke the cross-compiler when the package's normal build procedure will try
to invoke a native compiler.  Scratchbox removes a great deal of pain from
cross-compiling.

So the steps that follow will allow you to build an environment where it is
easy to build additional software as desired.  It is worth noting that the
droboshare has a cpu that is relatively powerful, and relatively idle in
most cases.  It is only prevented from being really useful by the limite
memory available.

Step -1:  Stuff you need:
=========================

You need a droboshare, with a drobo on it.
You need also need to download some stuff::

  mkdir ~/drobo
  cd ~/drobo
  mkdir droboshare
  cd droboshare
  mkdir Downloads
  cd Downloads
  Drobo SDK:  http://www.drobospace.com/download/11742/Data-Robotics-SDK/
  You need to get root access via Drobbear, read the SDK documentation for that.
  # which ought to get you ... SDK.zip
  cd ..

  mkdir sdk
  cd sdk
  unzip ../SDK.zip

You also need (as per the SDK) a code sourcery toolchain:  http://www.codesourcery.com/sgpp/lite/arm/releases/2006q1-6 with target platform: ARM Gnu/Linux



Step 0: install scratchbox2
===========================

sudo apt-get install scratchbox2... it might look like this::

  trestler:/etc/apt# apt-get install scratchbox2
  Reading package lists... Done
  Building dependency tree
  Reading state information... Done
  The following packages were automatically installed and are no longer required:
    libisc44
  Use 'apt-get autoremove' to remove them.
  The following extra packages will be installed:
    bochsbios debootstrap libbrlapi0.5 libicu38 libvdemgmt0 libvdeplug2 openbios-sparc
    openhackware proll qemu vde2 vgabios
  Suggested packages:
    sudo samba sbrsh vde2-cryptcab kvm
  The following NEW packages will be installed:
    bochsbios debootstrap libbrlapi0.5 libicu38 libvdemgmt0 libvdeplug2 openbios-sparc
    openhackware proll qemu scratchbox2 vde2 vgabios
  0 upgraded, 13 newly installed, 0 to remove and 0 not upgraded.
  Need to get 17.7MB of archives.
  After this operation, 49.2MB of additional disk space will be used.
  Do you want to continue [Y/n]?
  Get:1 http://gulus.usherbrooke.ca lenny/main libicu38 3.8.1-3 [5918kB]
  Get:2 http://gulus.usherbrooke.ca lenny/main libvdemgmt0 2.2.2-3 [12.4kB]
  Get:3 http://gulus.usherbrooke.ca lenny/main libvdeplug2 2.2.2-3 [11.6kB]
  Get:4 http://gulus.usherbrooke.ca lenny/main openhackware 0.4.1-4 [76.4kB]
  Get:5 http://gulus.usherbrooke.ca lenny/main proll 18-4 [248kB]
  Get:6 http://gulus.usherbrooke.ca lenny/main libbrlapi0.5 3.10~r3724-1+b1 [62.7kB]
  Get:7 http://gulus.usherbrooke.ca lenny/main vgabios 0.6b-1 [79.1kB]
  Get:8 http://gulus.usherbrooke.ca lenny/main bochsbios 2.3.7-1 [155kB]
  Get:9 http://gulus.usherbrooke.ca lenny/main openbios-sparc 1.0~alpha2+20080106-2 [229kB]
  Get:10 http://gulus.usherbrooke.ca lenny/main qemu 0.9.1-10 [10.5MB]
  Get:11 http://gulus.usherbrooke.ca lenny/main vde2 2.2.2-3 [181kB]
  Get:12 http://gulus.usherbrooke.ca lenny/main debootstrap 1.0.10lenny1 [52.1kB]
  Get:13 http://gulus.usherbrooke.ca lenny/main scratchbox2 1.99.0.24-2 [150kB]
  Fetched 17.7MB in 34s (518kB/s)
  Selecting previously deselected package libicu38.
  (Reading database ... 54086 files and directories currently installed.)
  Unpacking libicu38 (from .../libicu38_3.8.1-3_i386.deb) ...
  Selecting previously deselected package libvdemgmt0.
  Unpacking libvdemgmt0 (from .../libvdemgmt0_2.2.2-3_i386.deb) ...
  Selecting previously deselected package libvdeplug2.
  Unpacking libvdeplug2 (from .../libvdeplug2_2.2.2-3_i386.deb) ...
  Selecting previously deselected package openhackware.
  Unpacking openhackware (from .../openhackware_0.4.1-4_all.deb) ...
  Selecting previously deselected package proll.
  Unpacking proll (from .../archives/proll_18-4_all.deb) ...
  Selecting previously deselected package libbrlapi0.5.
  Unpacking libbrlapi0.5 (from .../libbrlapi0.5_3.10~r3724-1+b1_i386.deb) ...
  Selecting previously deselected package vgabios.
  Unpacking vgabios (from .../vgabios_0.6b-1_all.deb) ...
  Selecting previously deselected package bochsbios.
  Unpacking bochsbios (from .../bochsbios_2.3.7-1_all.deb) ...
  Selecting previously deselected package openbios-sparc.
  Unpacking openbios-sparc (from .../openbios-sparc_1.0~alpha2+20080106-2_all.deb) ...
  Selecting previously deselected package qemu.
  Unpacking qemu (from .../qemu_0.9.1-10_i386.deb) ...
  Selecting previously deselected package vde2.
  Unpacking vde2 (from .../archives/vde2_2.2.2-3_i386.deb) ...
  Selecting previously deselected package debootstrap.
  Unpacking debootstrap (from .../debootstrap_1.0.10lenny1_all.deb) ...
  Selecting previously deselected package scratchbox2.
  Unpacking scratchbox2 (from .../scratchbox2_1.99.0.24-2_i386.deb) ...
  Processing triggers for man-db ...
  Setting up libicu38 (3.8.1-3) ...
  Setting up libvdemgmt0 (2.2.2-3) ...
  Setting up libvdeplug2 (2.2.2-3) ...
  Setting up openhackware (0.4.1-4) ...
  Setting up proll (18-4) ...
  Setting up libbrlapi0.5 (3.10~r3724-1+b1) ...
  Setting up vgabios (0.6b-1) ...
  Setting up bochsbios (2.3.7-1) ...
  Setting up openbios-sparc (1.0~alpha2+20080106-2) ...
  Setting up qemu (0.9.1-10) ...
  Setting up vde2 (2.2.2-3) ...
  Setting up debootstrap (1.0.10lenny1) ...
  Setting up scratchbox2 (1.99.0.24-2) ...
  trestler:/etc/apt#

Step 1) Get a root File system
==============================

The idea here is to get a starting point by making a copy of the root file
system from a droboshare.  After downloading the the SDK from drobospace.com,
and enabling root shell access, just log into the droboshare and::

  trestler:/etc/apt# ssh root@droboshare
  The authenticity of host 'droboshare (172.25.5.13)' can't be established.
  RSA key fingerprint is 90:75:3d:ca:f1:42:65:92:71:97:48:d7:6b:ff:d7:8b.
  Are you sure you want to continue connecting (yes/no)? yes
  Warning: Permanently added 'droboshare,172.25.5.13' (RSA) to the list of known hosts.
  root@droboshare's password:


  Welcome to Embedded Linux
             _  _
            | ||_|
            | | _ ____  _   _  _  _
            | || |  _ \| | | |\ \/ /
            | || | | | | |_| |/    \
            |_||_|_| |_|\____|\_/\_/

            A Data Robotics Product.

  http://www.drobo.com/



  BusyBox v1.1.2 (2007.06.18-15:03+0000) Built-in shell (ash)
  Enter 'help' for a list of built-in commands.

  ~ $cd /
  / $  tar -cvf /mnt/Droboshare/Dro*/droboshare_root.tar bin dev fs.ls lib opt sbin src usr version boot etc home linuxrc root serial tmp var


  on your Debian or Ubuntu system,

  mkdir slash
  cd slash
  tar -xvf slash.tar

  #in the SDK there is some libz stuff,  add it into the appropriate places (/usr/lib for libz, and /usr/include for a .h)

  cd slash
  cd tmp
  tar -xvf ~/drobo/droboshare/sdk/libz.tgz
  mv *.so ../usr/lib
  mv *.h ../usr/include
  cd ../..
  tar -xjvf arm-2006q1-6-arm-none-linux-gnueabi-i686-pc-linux-gnu.tar.bz2
  creates the ~/drobo/droboshare/armx directory for the toolchaimkdir slash
  cd slash
  tar -xvf slash.tar

  #in the SDK there is some libz stuff,  add it into the appropriate places (/usr/lib for libz, and /usr/include for a .h)

  cd slash
  cd tmp
  tar -xvf ~/drobo/droboshare/sdk/libz.tgz
  mv *.so ../usr/lib
  mv *.h ../usr/include

  # add includes from the cross-compilation environment...
  # this isn't quite right,  the includes came from somewhere else... have to look around...

  cd ~/drobo/droboshare/
  dirs="`find armx -type d -name include`"
  #copy all the include from the sub-directories in armx into slash/usr/include...
  #something like this might work:
  for i in $dirs; do
      cd $i ; tar -cf - . | (cd ~/drobo/droboshare/slash/usr/include; tar -xvf - )
  done

  #but a lot of them seem to be repeats, the only really interesting one is:
  ./arm-none-linux-gnueabi/libc/usr/include






Step 2) Configure Scratchbox2
=============================

#some of these helped... not sure which one, have to try again::

  sb2-init -c /usr/bin/qemu-arm gcc-armel /home/peter/drobo/droboshare/armx/bin/arm-none-linux-gnueabi-gcc
  sb2-init -c "qemu-arm" -t /home/peter/drobo/droboshare/armx
  sb2-init gcc /home/peter/arm-2006q3/bin/arm-linux-gcc


Step 3) Build anything...
=========================

Build procedures is basically out of the box after this point::

  cd bzip2
  make
  make install PREFIX=/home/peter/drobo/droboshare/slash/usr


  cd ../db*
  cd build_unix
  export CC=/home/peter/drobo/droboshare/armx/bin/arm-none-linux-gnueabi-gcc
  ./configure --prefix...
  make
  make install

  cd ../ncur*
  ./configure --prefix=...
  make
  make install

  cd ../openssl*
  ./config --prefix=...
  make
  make install

  cd ../Pyth*
  ./configure --prefix=
  make

  Failed to find the necessary bits to build these modules:
  _sqlite3 _tkinter bsddb185
  gdbm readline sunaudiodev
  To find the necessary bits, look in setup.py in detect_modules() for the module's name.


  Failed to build these modules:
  _curses _curses_panel

  running build_scripts
  make install

  cd ../drobo-utils/trunk
  /python setup.py install


  cd into usr/bin
  vi drobom
  #!/usr/bin/env python
  :wq

  cd ~/drobo/droboshare/src
  tar -xzvf ../Downloads/libpcap-1.0.0.tar.gz
  cd libpcap*
  sb2
  ./configure --prefix=/home/peter/drobo/droboshare/slash/usr
  make
  make install
  exit

  cd ..
  tar -xzvf ../Downloads/tcpdump-4.0.0.tar.gz
  cd tcpdu*
  ./configure --prefix=/home/peter/drobo/droboshare/slash/usr
  make
  fails with:
  /usr/lib/libcrypto.a(dso_dlfcn.o): In function `dlfcn_bind_func':
  dso_dlfcn.c:(.text+0x2d4): undefined reference to `dlsym'
  dso_dlfcn.c:(.text+0x344): undefined reference to `dlerror'
  /usr/lib/libcrypto.a(dso_dlfcn.o): In function `dlfcn_bind_var':
  dso_dlfcn.c:(.text+0x400): undefined reference to `dlsym'
  dso_dlfcn.c:(.text+0x46c): undefined reference to `dlerror'
  /usr/lib/libcrypto.a(dso_dlfcn.o): In function `dlfcn_unload':
  dso_dlfcn.c:(.text+0x4e8): undefined reference to `dlclose'
  /usr/lib/libcrypto.a(dso_dlfcn.o): In function `dlfcn_load':
  dso_dlfcn.c:(.text+0x56c): undefined reference to `dlopen'
  dso_dlfcn.c:(.text+0x5d4): undefined reference to `dlclose'
  dso_dlfcn.c:(.text+0x5ec): undefined reference to `dlerror'
  collect2: ld returned 1 exit status
  make: *** [tcpdump] Error 1

  vi Makefile
  /-lc
  a-ldl
  :wq

  make
  make install


so there you go, samples of building a whole bunch of packages.






copyright:

Drobo Utils Copyright (C) 2008,2009  Peter Silva (Peter.A.Silva@gmail.com)
Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.
