==================
Drobo Utils README
==================

Drobo-utils is a set of linux tools to query and manage Data Robotics
Drobo storage systems.  If you fire up droboview, it should look pretty
familiar to those who have seen the dashboard on other operating systems. 
Droboview is built on a little programmer interface which can be installed 
on the system and used by other applications as well.

For experienced Linux hands, there is a command line interface, drobom,
which offers the same functionality as droboview.   For real hackers, fire
up a python interpreter, 'import Drobo', help(Drobo), and you are off to 
the races...  Command-line access is also bundled into a set of improvements
to a standards droboshare called 'Droboshare Augmented Root File System' (DARFS)



.. contents::

INSTALLATION
------------

Drobo utils installation.

REQUIREMENTS
============

Drobo-utils was developed on pre-release version of Kubuntu (Hardy, 
Intrepid, and now Jaunty) Any similarly recent distro ought to do.

To get drobo-utils running, you need packages something like (these are
ubuntu packages, names may vary on other distros):

essential::
  python      -- interpreter for python language
  parted      -- partitioner, usually included with the distro.

  if using RHEL, which has python 2.4...
     python-ctypes -- module for C-interface

for the GUI:
  python-qt4  -- the python bindings for version 4 of the QT toolkit

To get a complete list, it is best to use a shell window to grep in the 
Debian package control file (which defines what the dependencies are for the
build system)::

 peter@pepino% grep Depend debian/control
 Build-Depends: debhelper (>= 5), python2.5-dev, python-docutils
 Depends: ${shlibs:Depends}, ${misc:Depends}, parted
 peter@pepino%      

INSTALLING pre-requisites  
=========================

On ubuntu, it would typically look like so: Open a shell window. Enter the following package installation commands::

 % sudo aptitude install python-qt4 parted 
 % sudo aptitude install debhelper python2.5-dev
 % sudo aptitude install python-docutils

If you have received a pre-built binary package,then you only need the 
first line.  If you want to build from source, then you need the second line.  
The third line install what you need to build documentation.

On redhat/fedora distros, it would more likely be 'yum' instead of 'aptitude' 
and some of the package names will change.  A typical difference is that 
packages for developers have the -devel suffix on Redhat derived 
distributions, instead of the -dev favoured by debian derived ones.

here is an example from fedora 7 (courtesy of help4death on the google group)::

 % yum install python
 % yum install PyQt4
 % yum install python-devel

NOTE: if X or QT is missing, it will only disable the GUI.  Line mode will work without issues.  the package should work fine on headless servers using only the command line.


Install From Package
====================
Point your browser at: http://sourceforge.net/project/showfiles.php?group_id=222830 
where current packages are available.  after downloading a .deb, it is simply a matter of:

  dpkg -i drobo-utils-<version>.deb

done!

Install from Source
===================

See DEVELOPER.txt


Try Out the CLI
===============

Assuming you have all of the above parts, in the directory where you
downloaded the source, you should be able to invoke the command line 
interface as follows::

         drobom status 

see if something sensible happens... on my system with a drobo
the following happens::

 % sudo drobom status
 /dev/sdz /drobo01 100% full ( ['Red alert', 'Bad disk', 'No redundancy'], 0 )
 %

Note: drive changed to sdz to avoid copy/paste errors.

very scary, but my drobo is in bad shape right now... you should just get []
as a status, which means there is nothing wrong.   To get all kinds of 
information on your drobo, try 'drobom info.'  You can then invoke it 
with no arguments at all which will cause it to print out a list of the 
commands available through the command line interface.

Try Out the GUI
===============

Once the command line stuff that is working, and assuming you 
have python-qt4 installed, try::

 % droboview

which should start a GUI for each drobo attached to your machine, that
you have permission to access (depends on the setup, usually USB devices 
on desktops are accessible to users, so you can see them.  

         
Try Out the Python API
======================

   See DEVELOPERS.txt

Building debian & ubuntu packages
=================================

   See DEVELOPERS.txt


Setup Drobo with Linux
----------------------

One can use the Format tab of the GUI to partition the device
and create a single file system for a given LUN.  

NOTE:  mke2fs takes a very long time to run, on the order of ten minutes 
per Terabyte. the display format button just turns red while the format
is in progress,and you have to wait until it finishes.  Have not
determined a method to monitor progress yet.  other file systems are
much more quickly created, so less of an issue.

I actually prefer to use the system tools manually, as described below:

Drobos with firmware 1.1.1 or later work well under linux with ext3.
You can, of course set up an NTFS or HPS+ or FAT32 if you really want,
but it seems actively counter-intuitive on Linux.  Have not tested
HPS, but ntfs-3g worked fine initially.  However, unless you are
going to physically move the disk to between systems, the native (ext3) 
format has many advantages.  The ´coffee is hot´ disclaimer is 
necessary at this point::

 WARNING: THE FOLLOWING 4 LINES WILL ERASE ALL DATA ON YOUR DROBO!
 WARNING: NO, IT WILL NOT ASK ANY QUESTIONS!
 WARNING: ASK YOURSELF, before you start: ARE YOU SURE? 
 WARNING: AFTER THE SECOND LINE, YOU ARE TOAST.
 WARNING: BEST TO BACKUP YOUR DATA BEFOREHAND...

If you didn't use the GUI, Here is what you have to type::

 # drobom -d /dev/sdz format ext3 PleaseEraseMyData
 You asked nicely, so I will format ext3 as you requested
 if you are really sure, go ahead and do: sh /tmp/fmtscript

 # cat /tmp/fmtscript
 #!/bin/sh
 parted /dev/sdz mklabel gpt
 parted /dev/sdz mkpart ext2 0 100%
 parted /dev/sdz print; sleep 5
 mke2fs -j -i 262144 -L Drobo01 -m 0 -O sparse_super,^resize_inode /dev/sdz1


The above sets up the drobo as one big partition, with a label that says
it ought to contain an ext2 file system.  If you want an NTFS file system,
then write ´ntfs´ in place of ext2.  The next step is to add the file
system into the partition.  while parted's are instantaneous, the mke2fs 
takes a while, just have a little patience, it´ll be fine.

 sh -x /tmp/fmtscript

(If you want an ntfs file system, then mkntfs -f -L Drobo01 /dev/sdz1 
ought to work too... ) 

On my system the process looked like this::

 root@alu:~# parted -i /dev/sdz
 GNU Parted 1.7.1
 Using /dev/sdz
 Welcome to GNU Parted! Type 'help' to view a list of commands.
 (parted) mklabel gpt
 (parted) mkpart ext2 0 100%
 (parted) quit
 root@alu:~# fdisk /dev/sdz
 GNU Fdisk 1.0
 Copyright (C) 1998 - 2006 Free Software Foundation, Inc.
 This program is free software, covered by the GNU General Public License.
 
 This program is distributed in the hope that it will be useful, but WITHOUT ANY
 WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 PARTICULAR PURPOSE.  See the GNU General Public License for more details.
 
 Using /dev/sdz
 Command (m for help): p
 
 Disk /dev/sdz: 2199 GB, 2199020382720 bytes
 255 heads, 63 sectors/track, 267349 cylinders
 Units = cylinders of 16065 * 512 = 8225280 bytes
 
    Device Boot      Start         End      Blocks   Id  System
 /dev/sdz1               1      267350  2147488843   83  Linux
 Command (m for help): q
 root@alu:~# mke2fs -j -i 262144 -L Drobo01 -m 0 -O sparse_super,^resize_inode /dev/sdz1
 mke2fs 1.40.8 (13-Mar-2008)
 Filesystem label=Drobo01
 OS type: Linux
 Block size=4096 (log=2)
 Fragment size=4096 (log=2)
 8388608 inodes, 536870886 blocks
 0 blocks (0.00%) reserved for the super user
 First data block=0
 16384 block groups
 32768 blocks per group, 32768 fragments per group
 512 inodes per group
 Superblock backups stored on blocks:
         32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
         4096000, 7962624, 11239424, 20480000, 23887872, 71663616, 78675968,
         102400000, 214990848, 512000000
 
 Writing inode tables: done
 Creating journal (32768 blocks): done
 Writing superblocks and filesystem accounting information: done
 
 This filesystem will be automatically checked every 26 mounts or
 180 days, whichever comes first.  Use tune2fs -c or -i to override.
 root@alu:~#
 root@alu:~# mount /dev/sdz1 /mnt


Getting Source 
==============

See DEVELOPERS.txt
 

Multiple LUNS
=============

LUN is an abbreviation of 'Logical UNit'. The origin of the term is SCSI terminology.
When RAID units became too large for support in the past, and were sub-divided 
to present smaller units the operating system.  The default LUNSIZE on Drobos 
is 2 TiB (adjustable using the tools.) If more disk space (after 
allowing for parity/redundancy) than LUNSIZE is installed in a 
unit, Drobo will show a second (or even third) LUN.  Each LUN 
shows up in Linux as a separate disk (examples if the first
LUN shows up as /dev/sde, the next will be /dev/sdf, then /dev/sdg.)

If you think you should see multiple LUNS and you don't, you
might have a look at some kernel settings:
make sure that scsi_mod kernel module is loaded, make 
sure /sys/module/scsi_mod/parameters/max_luns is > 1.

Droboview will start up one GUI per drobo, regardless of the number
of LUNS.  If asked to format, all LUNS for the device will be formatted.


ON LUNSIZES >= 2TB:
 -- On older distributions, there are a couple of gotchas related to 
    linux tools which aren't 2TB ready...  to exceed 2 TB, you need to:
    	-- use GPT partitions, which aren´t supported by older fdisk
	   versions.  Tools based on libparted work fine, mostly.
    
        -- gparted fails, and seems to have a 1 TB limit on devices.
           (bug #524948 reported to bugzilla.gnome.org) It's just the GUI, 
           as libparted is fine, and other tools based on it
           still work. 

  -- on linux kernel < 2.6.24 supposedly, the USB layer won't let one address 
     LUNs/offsets > 2 TB.  For example, Ubuntu hardy (8.04) released in Spring 
     2008 has a 2.6.24, and so is OK.  I've never been able to test this problem. 

  -- ext3 with 4K blocks is supposed to allow file system capacity of 8 TiB.
     4K blocks seem to be assigned by default. So I think a good max. 
     It would be fun to set the LunSIZE to 8 TiB and test it out...


Drobo Pro
=========

Drobo-utils depends on the linux generic scsi layer.  I suspect that 
there is just a basic ethernet connection now, and you a few additional driver layers
set up before it will work.   You need to configure the iscsi driver to recognize 
the device.  Lemonizer on the Google Group 2009/05/16 reported good luck with:

I had to manually configure the ip of the dbpro from the Drobo
Dashboard on my macbook to do this as I'm not sure how to get the
portal ip for iscsiadm. In my case it was 192.168.2.80 port 3260 and
I'll use that ip in the example below

1. Configure iscsi ip address via drobo dashboard on win/osx
2. Install open-iscsi (http://www.open-iscsi.org/): sudo apt-get install open-iscsi
3. Connect the dbpro to host machine via iscsi
4. Query dbpro's id: sudo iscsiadm --mode discovery --type sendtargets --portal 192.168.2.80
5. Copy the id string returned by iscsiadm, something like "iqn.2005-06.com.datarobotics:drobopro.tdb091840080.node0"
6. Connect to the dbpro: sudo iscsiadm --mode node --targetname iqn.2005-06.com.datarobotics:drobopro.tdb091840080.node0 --portal 192.168.2.80:3260 --login

If everything went well, your dbpro should show up under /dev. Also
check /var/log/messages to confirm that the iscsi device connected
successfully.

After that, drobo-utils should be able to detect the Drobo and manage
it over ethernet.

(source: http://groups.google.com/group/drobo-talk/browse_frm/thread/453e02e105e9b41?hl=en )

Some people reported data corruption.  This link claims to fix one such
issue:
http://www.drobospace.com/forum/thread/13951/Dropped-iSCSI-connections/?page=2#24792


Drobo Firmware
--------------

Upgrading firmware is pretty self-explanatory in the GUI.  the first time you 
press the Update button, it checks to see if a new firmware is available.  If 
it there is newer firmware, it offer to upgrade, with suitable prompts. 
Similarly, the line mode interface has two commands to deal with firmware,
fwcheck will tell you if an upgrade is required.  the fwupgrade 
will do the job.  It takes a few minutes, and prints a status 
you you can see how it is progressing.  Have patience::

 root@pepino:/home/peter/drobo/drobo-utils/trunk# drobom fwupgrade
 
 validateFirmware start...
 Magic number validated. Good.
 484 + 2937552 = 2938036 length validated. Good.
 CRC from header: 4260378881, calculated using python zlib crc32: 398201869
 yeah, the header CRCs do not match. For now they never do ... ignoring it.
 CRC for body from header: 1852877921, calculated: 1852877921
 32 bit Cyclic Redundancy Check correct. Good.
 validateFirmware successful...
 writeFirmware: i=484, start=484, last=2938036 fw length= 488
 .
 wrote  32768  bytes... total: 33252
 wrote  32768  bytes... total: 66020
 .
 .
 .
 wrote  32768  bytes... total: 2720228
 wrote  32768  bytes... total: 2752996
 wrote  32768  bytes... total: 2785764
 wrote  32768  bytes... total: 2818532
 wrote  32768  bytes... total: 2851300
 wrote  32768  bytes... total: 2884068
 wrote  32768  bytes... total: 2916836
 wrote  21200  bytes... total: 2938036
 writeFirmware Done.  i=2938036, len=2938036
 root@pepino:/home/peter/drobo/drobo-utils/trunk# 

when it's done, you can check if it worked using::

 root@pepino# drobom status
 /dev/sdf - 00% full - (['New firmware installed'], 0)

If the status is like that, then do::

 root@pepino:/home/peter/drobo/drobo-utils/trunk# drobom shutdown

lights will flash etc... wait until Drobo goes dark.
Wait another five seconds, then un-plug the USB / connector.
   
Plug it back in, and wait 10 seconds.
it should start up with the latest firmware available for your drobo.
   
The drobom commands, like DRI's dashboard, will normally
get the latest and greatest firmware and upgrade.  If you have
the need, you can load arbitrary firmware from the CLI with
fwload command.


SAFETY
======

Those worried about safety of using this software should know:  it was 
developed with assistance from the vendor (Data Robotics Inc.), and 
in every case, based on vendor documentation, and with at least encouragement,
if not outright support.  For each release, a QA.txt file is built, demonstrating the functionality tests run.  There are multiple checksum verifications built 
into the firmware upgrade process, so it is next to impossible to brick a drobo 
using the tools.  Drobo-utils verifies firmware checksums before attempting 
to upload the image to the device, and the device checks the firmware against 
the checksums as well.  New firmware is loaded into an alternate location 
from the currently active one, and if activation of the new firmware fails, 
the drobo will simply boot the old one.  
 
On the other hand, common sense rules do apply.  Setting the LUN size, or 
re-formatting a Drobo will erase all your data whether you do it on Linux or 
any other operating system.  These are power tools, and they can do some 
damage to your data if used without proper care.  For example, the reliability 
of any storage unit does not reduce the need for backups it only makes doing them 
easier. A Drobo is an excellent place to put backups, but not a substitute for 
them.  Backups are the only way to address error 18 (the number of inches in 
front of the keyboard the source of the issue lies.) and no storage unit can 
protect against fire or flood.

Compatibility
=============

Drobo has been tested with every old firmware version. Any Drobo should
be upgradable to modern firmware using the dashboard.

   NOTE: really need at least 1.1.1 to use Linux & ext3.
         just use the tools to upgrade your firmware ASAP.

   1.01  - very old... bad idea to install this, need to write
           a script to get out, because it isn't in the revision
           table.
           not much works except firmware upgrade.

   1.0.2 - works ok in CLI And GUI to view, and upgrade firmware.

   1.0.3 - GUI and CLI work OK, can upgrade firmware.
           Used ntfs3g for a few months under ubuntu 7.10 Linux.
           Used 2 TB LUN, with 1.5 TB of physical space available.
            
   1.1.0 - dashboard works no issues.
         - from this point, you don't seem to need to unplug the USB
           connector to complete the upgrade.

         - firmware prior to here deals badly with ext3.

   1.1.1 - 1.2.4 works without issues. 
           ('name' not supported by firmware)

   1.3.0 - works without issues.


   
KNOWN BUGS
----------

droboview isn't suited to run continuously for long periods, 
as it has a memory leak...  total foot print starts out at 32M
with a 15 MB resident set size, of which 10 MB are shared, so only 
about 4M of real memory consumed.   but the RSS grows at about 
2MB/hour.

  29m  11m S    1  2.9   9:44.50 droboview

best to restart it daily, or use it when necessary, but not leave it
on for days.

After you resize luns, droboview gets confused, you need to exit and
restart.

We have a report that dumping diagnostics does not work over firewire.
Work-around:  connect via USB.


Droboshare Support
------------------

Droboshare is not directly supported by drobo utils running on a linux host.
However, the droboshare itself is a linux host, and it is possible to run
drobo-utils un-modified on the droboshare itself.  In order to do run drobo-utils, you need to build a python interpreter.  A python interpreter has, itself,
a bunch of dependencies.  So you need to install a whack of packages on the droboshare in order to get a working drobo-utils.  This is where DARFS comes in.

DARFS
=====
The Droboshare Augmented Root File System (darfs) is a 60 MB or so download 
you can get from drobo-utils.sf.net.  There isn't any source code, because,
well, nothing from any of the packages has been modified.  there are
instructions on how to build DARFS in DEVELOPERS.html

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


Building Droboshare applications
================================
    See DEVELOPERS.txt

Droboshare Firmware
===================

With DARFS, and the third party software you can get from drobospace and 
drobo.com, the droboshare is very open and hackable.   However, there
remains one remaining limitation: There is no open source way to upgrade 
or modify droboshare firmware.  If you want to re-flash to a factory 
original state, you need the vendor dashboard.


Credits
-------

who did what::

 Peter Silva:    wrote most all of it.
 Chris Atlee:    the proper debian packaging. 
 Brad Guillory:  some help with diagnostics and patches.
 Joe Krahn:      lots of inspiration.
 Andy Grover:    some elegance cleanups. 


Administrivia
-------------

version 9999, somewhen



copyright:

Drobo Utils Copyright (C) 2008,2009  Peter Silva (Peter.A.Silva@gmail.com)
Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.
