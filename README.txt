
-----------
Drobo-Utils
-----------

Drobo-utils is a set of linux tools to query and manage `Data Robotics`_
Drobo storage systems.  Fire up drobom view, and it should look 
familiar to those who have seen the dashboard on other operating systems. 
Drobom view is built on a little python programmer interface which can be installed 
on the system and used by other applications as well.  For experienced Linux hands, 
the rest of the command line interface is provided by other sub-commands of 
drobom, and offer the same functionality as the view graphical interface.  

.. _`Data Robotics`: http://www.drobo.com

Compatibility Matrix
--------------------

If you can get your drobo device to be associated with a /dev/sdX [#GenSCSI]_ 
file, then you will be able to partition, build file systems and
read & write data to it using ordinary system tools (see Setup_.)

Drobo-utils accesses drobos via the same files.  The software 
scans those files, and asking each device if it is a Drobo.
Unfortunately, the way Drobos respond varies, so not all of them respond
in a way that the software understands.  Even for the same
device, different physical interconnects may work with different functionality.
There are two levels of access to Drobos: data (being able to read and 
write data, and full meaning that the drobo responds to the full
command and control language.

With that in mind, the compatibility matrix of each device vs. the
physical channel is below:

+--------+-------------------------------------------+---------+
| Model  |      Interface                            | Maximum |
|        |      ( Performance MB/s )                 | LUN Size|
+--------+------+------+---------+-----------+-------+---------+
| interf | USB  |  FW  | TCP/IP  | iSCSI     | eSATA |  ext3   |
+--------+------+------+---------+-----------+-------+---------+
| Drobo  | full | n/a  |   n/a   |  n/a      |  n/a  |   2     |
| (Gen1) | (15) | (0)  |   (0)   |  (0)      |  (0)  |         |
+--------+------+------+---------+-----------+-------+---------+
| Drobo  | full | full?|   n/a   |  n/a      |  n/a  |   2     |
| (Gen2) | (15) | (?)  |   (0)   |  (0)      |  (0)  |         |
+--------+------+------+---------+-----------+-------+---------+
| Drobo  | n/a  | n/a  | data*1  |  n/a      |  n/a  |   2     |
| Share  | (0)  | (0)  | (15)    |  (0)      |  (0)  |         |
+--------+------+------+---------+-----------+-------+---------+
| Drobo  | full | ?    |  n/a    | full*2    |  n/a  |   8-?   |
| Pro    | (15) | (?)  |  (0)    | (80)      |  (0)  |         |
+--------+------+------+---------+-----------+-------+---------+
| Drobo  | ?    | n/a  |  n/a    |  ?        |  n/a  |   8?    |
| Elite  | (?)  | (0)  |  (0)    |  (?)      |  (0)  |         |
+--------+------+------+---------+-----------+-------+---------+
| Drobo  | full | ?    |  n/a    |   n/a     | data  |   8     |
|   S    | (15) | (?)  |  (0)    |   (?)     | (0)   |         |
+--------+------+------+---------+-----------+-------+---------+

.. parsed-literal::

  full - Find/Full: drobo-utils will find the device on it's own (auto-discover)
  data - works: device functions for data i/o, but Drobo-utils cannot access it for configuration.
  n/a - not applicable (device does not have this interface.)
  \*1 - Droboshare is not usable with drobo-utils on a linux server. If you 
       install Droboshare Augmented Root File System (DARFS_) then one can 
       run a drobo-utils in line mode on the droboshare itself.
  \*2 - Will not detect, out of the box, an iSCSI drobo.  One must configure 
       the iSCSI subsystem to obtain a /dev/sdX file.  see `iSCSI Setup`_ for 
       details on that initial configuration.  After that point, Drobo-utils 
       will function properly over iSCSI.


.. [#GenSCSI] Linux drivers make disk, cdrom, and other peripherals, look
   like SCSI peripherals to applications.  Regardless of the physical connection, 
   it is a normal part of the linux kernel to make the device appear as a 
   so-called "generic SCSI" one.


COFFEE IS HOT
-------------

People sued a national fast food chain because their `coffee was hot`_, but did not 
have a warning on the cup stating that.  For most people, the risk of scalding 
should be fairly obvious. 

.. _`coffee was hot`: http://en.wikipedia.org/wiki/Liebeck_v._McDonald's_Restaurants

Drobo has made it so much easier to obtain much more secure storage, that some with 
little or no professional storage management experience are getting Drobos.
Some have the expectation that Drobo´s, because they allow for disk failures, 
replace the need for backups.  Sad stories have been told about people putting 
data only on the drobo, and no-where else, and then something happens and they 
lose the data.


.. PLEASE, PLEASE, PLEASE::  Do not store all your data on a Drobo (or any 
   other single device, from any vendor) with no backups or alternate copies.   
   Eventually, Something very bad will happen.
  
You need to look at your data and determine the backup/data security strategy.
If you have never done this, or do not know what it means, please consult the
Deployment_ section in this page for examples.



INSTALLATION: Easiest
---------------------

On Ubuntu 9.10 [#Distro]_ or later (or Debian unstable or other debian derived 
distributions), drobo-utils is included in the repositories, and installation 
from a shell prompt is simply::

  % sudo apt-get install drobo-utils

to run at least the command line utility.  Users on servers often want only 
command line functionality.  On the other hand, to enable the graphical user 
interface, one more package must be installed::

  % sudo apt-get install python-qt4

That is the easiest installation method, this method ensures that any packages 
required are automatically installed on the system as part of the above 
installation.  On other distributions, or if the version in the repositories is 
too old, more complicated methods might be needed.  For all other installation 
methods, one must ensure the packages that drobo-utils requires are installed.  
These packages are called Dependencies.

.. [#Distro] Drobo-utils is developed for release on the stable version of 
   Kubuntu at the time it is released.  Development started on kubuntu 7.10 
   and continued to 9.10 at the end of 2009.  Any similarly recent distribution 
   ought to do.  The package is accepted into Debian unstable, so all debian 
   derived distributions (debian, \*ubuntu, MEPIS, PCLinux-OS, etc...) should 
   inherit the package in due course.  


Dependencies
============

Before one can install drobo-utils itself, the other packages needed are something 
like those below (these examples are ubuntu packages, names may vary on other 
distributions)::

     python      -- interpreter for python language
     parted      -- partitioner, usually included with the distro.

If using Redhat Enterprise Linux (RHEL, aka. CentOS, Scientific Linux etc...), 
which have python 2.4 [#python]_, then the following are necessary::

     python-ctypes -- module for C-interface

.. [#python] I'm not sure that python-2.4 will work, for other reasons.  the utility is built on 
   python-2.5 and python-2.6 and it should work on them.  python-2.4 is not tested.  python-3 will
   definitely not work.

On RPM-based distros (such as Redhat & SuSe), it would more likely be 'yum' instead of 
'aptitude' and some of the package names will change.  A typical difference is that 
packages for developers have the -devel suffix on Redhat derived distributions, instead 
of the -dev favoured by debian derived ones.

Here is an example from fedora 7 (courtesy of help4death on the google group)::

    % yum install python
    % yum install PyQt4
    % yum install python-devel

NOTE: if X or QT is missing, it will only disable the GUI.  Line mode will 
work without issues.  The package should work fine on headless servers using 
only the command line.


Install From Package
====================

Once dependencies are satisfied,  one can install the latest stable package manually.

Point a browser at: http://sourceforge.net/project/showfiles.php?group_id=222830 

where the most current packages are available.  after downloading a .deb, it is simply a matter of::

  # dpkg -i drobo-utils-<version>.deb

done!

Redhat/Fedora users.  alien may be used to convert the package. I don't know if it works.  Someone to take on RPM packaging would be very welcome!  This is a pure python package, so the chances are good that it does work without issue.

There is a `Fedora Package`_

.. _Fedora Package: http://olea.org/paquetes-rpm/repoview/drobo-utils.html

Install From TAR file
=====================

Assuming the dependencies are installed/satisfied, the package will actually run fine 
without being installed in any systemish places.  Source code can be directly downloaded
run it explicitly from the directory.  

Point a browser at: http://sourceforge.net/project/showfiles.php?group_id=222830 

download the .tgz preferred, then unpack it::

  # tar -xzvf drobo-utils-<version>.tgz
  # cd drobo-utils-<version>
  # ./drobom status

for all of the examples in the manual one just needs to prepend './' before drobom.  


Install from GIT
================

When a new model comes out, or the stable version is missing a feature, one may elect to
follow along with the latest development version.  installation of git_, is necessary,
then use it can be used to get a copy of the source tree::

  # apt-get install git
  # git clone git://drobo-utils.git.sourceforge.net/gitroot/drobo-utils/drobo-utils
  # cd droo-utils
  # ./drobom status
  # git pull

This gives a read-only copy of the source code that can be updated with the latest 
changes with 'git pull'.  One can also select any stable version of drobo-utils by use of
'git branch -r', and 'git checkout'.  For details, consult git documentation.

So, one way or another, drobo-utils is installed. The next step is to try it out.

.. _git: http://www.git-scm.com

Try Out the CLI
===============

The first item to verify after installation is to invoke the 
command line interface (CLI.) and see if something sensible happens... 
on my system with a drobo[#sdz] the following happens::

 % sudo drobom status
 /dev/sdz /drobo01 100% full ( ['Red alert', 'Bad disk', 'No redundancy'], 0 )
 %

.. [#sdz] in examples, drive always changed to sdz to avoid copy/paste errors.

very scary, but my drobo is in bad shape right now... normal result is: []
as a status, which means there is nothing wrong.   To get all kinds of 
information about the drobo, try 'drobom info.'  Invocation  
without arguments at all which will cause it to print out a list of the 
commands available through the command line interface.

Try Out the GUI
===============

Once the command line functionality is verified, and assuming 
python-qt4 is installed::

 # drobom view

as root starts a GUI for each drobo attached to a computer.
There are various tabs to allow one to obtain information from the Drobo,
and also change its configuration.  For example, one can use the Format 
tab of the GUI to partition the device and create a single file system 
for a given LUN.  

There are two choices to make when setting up a Drobo: file system type, and LUN size.
For a discussion of these choices, please consult:  `LUNSIZE fits all`_ 
and `Filesystem Choice`_.

.. _Setup:

Manual Setup Drobo with Linux
-----------------------------

This section provides an illustrative example of the most common configuration.
An ext3 file system is built on a Drobo with whatever LUNSIZE is already in place.
The GUI and line modes produce exactly the same result, and simply
execute standard linux partitioning using parted, and the appropriate
file system builder for the type in question. Sample CLI run::

 PleaseEraseMyData# drobom -d /dev/sdz format ext3 
 peter@pepino:~/drobo/drobo-utils$ sudo ./drobom format ext3
 /dev/sdz - Drobo disk pack 00% full - ([], 0)
 preparing a format script for a ext3 file system as you requested
 OK, I built the script but nothing is erased yet...
 You can have a look at it with: cat /tmp/fmtscript
 If you are really sure, go ahead and do: sh /tmp/fmtscript
 WARNING: Ready to destroy all your data. Continue? (y/n) n
 Phew... You stopped just in time!
 peter@pepino:~/drobo/drobo-utils$

 # cat /tmp/fmtscript
 #!/bin/sh
 parted /dev/sdz mklabel gpt
 parted /dev/sdz mkpart pri ext3 0 100%
 parted /dev/sdz print; sleep 5
 mke2fs -j -i 262144 -L Drobo01 -m 0 -O sparse_super,^resize_inode /dev/sdz1

The above sets up the drobo as one big partition, with a label that says
it ought to contain an ext3[#mke3fs] file system.  For an NTFS file system,
write ´ntfs´ in place of ext3.  The next step is to add the file
system into the partition.  while parted's are instantaneous, the mke2fs 
takes a while, just have a little patience, it´ll be fine.
The ´coffee is hot´ disclaimer is necessary at this point::

 WARNING: THE FOLLOWING LINES WILL ERASE ALL DATA ON YOUR DROBO!
 WARNING: NO, IT WILL NOT ASK ANY QUESTIONS!
 WARNING: ASK YOURSELF, before you start: ARE YOU SURE? 
 WARNING: AFTER THE SECOND LINE, YOU ARE TOAST.
 WARNING: BEST TO BACKUP YOUR DATA BEFOREHAND...

 sh -x /tmp/fmtscript

(For an ntfs file system, use mkntfs -f -L Drobo01 /dev/sdz1 
... For ext3, be prepared to wait[#mkext3time]_ ) 

.. [#mke3fs] The proper command to build an ext3 file system is mke2fs -j.  This
   confuses people who wonder why one doesn't use some sort of ext3 mkfs.  There isn't one,
   an ext3 is an ext2 with a journal.

.. [#mkext3_time] mke2fs takes a very long time to run, on the order of ten minutes 
   per Terabyte. the display format button just turns red while the format
   is in progress. Have not determined a method to monitor progress yet from
   the GUI yet.  other file systems are much more quickly created, so less of 
   an issue.

Sample run::

 root@alu:~# parted -i /dev/sdz
 GNU Parted 1.7.1
 Using /dev/sdz
 Welcome to GNU Parted! Type 'help' to view a list of commands.
 (parted) mklabel gpt
 (parted) mkpart pri ext2 0 100%
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


.. _`LUNSIZE fits all`:

LUNSIZE Fits All?
=================

By default, Drobo creates a separate 'disk' visible to the computer for every 2 
Terabytes (TiB) of parity-protected capacity on the unit.   The natural usage 
that a drobo invites in users is to have a single, large device covering all the 
data on device.  For example, on Mac OS/X, users often create 16 TB LUNS on HFS.  
This allows all the storage to fit on one large pool.  The downside of larger 
LUNS has to do with startup time, and the time to perform a file system check.

Under Linux unfortunately, with a first generation Drobo, one should limit the 
volume size to 2 TiB[#gen12TiB]_.  It is hoped, but not confirmed, that later 
products support LUNS larger than 2 TiB on Linux.  Drobom view therefore limits 
lunsize to 2 TiB for the moment.  The command line interface can be used to 
create larger LUNS, they just might not work.

ON LUNSIZES >= 2TB:
 -- On older distributions, there are a couple of gotchas related to 
    linux tools which aren't 2TB ready...  to exceed 2 TB, you need to:
    	-- use GPT partitions, which aren´t supported by older fdisk
	   versions.  Tools based on libparted work fine, mostly.
    
        -- gparted fails, and seems to have a 1 TB limit on devices.
           (bug #524948 reported to bugzilla.gnome.org) It's just the GUI, 
           as libparted is fine, and other tools based on it
           still work. 

  -- on linux kernel < 2.6.24, the USB layer won't let one address 
     LUNs/offsets > 2 TB.  For example, Ubuntu hardy (8.04) released in Spring 
     2008 has a 2.6.24, and so is OK.  I've never been able to test this problem. 

  -- On linux kernel < 2.6.31 there is are reported firewire problem that will
     prevent devices > 2 TiB from working.

  -- ext3 with 4K blocks is supposed to allow file system capacity of 8 TiB.
     4K blocks seem to be assigned by default. So I think a good max. 
     It would be fun to set the LunSIZE to 8 TiB and test it out...

  -- Windows XP does not support LUNS > 2 TiB 

.. [#gen12TiB] Many tests have been performed with first generation products 
   and several different failure modes have been found when exceeding 2 TiB.  
   `Data Robotics`_ has addressed several failure modes, via fixes to the kernel 
   in 2.6.24, and for firewire in 2.6.31, and continues to address them in 
   later generation products.

.. _`Filesystem Choice`:

What Kind of File System?
=========================

Drobos work well under linux with ext3.  One can, of course, set up an NTFS or 
HFS+ or FAT32 if necessary, but it seems actively counter-intuitive on Linux.  
Developers of Drobo-utils have not tested HFS.  Linux does not write to Journalled HFS+
at this point, so HFS support is not present.  Good success is reported with Ntfs-3g,
but the performance is much lower than what is typically reported with ext3.
Unless physical movement of the disk to between systems is required, the 
native (ext3) format is the best option.

.. _`iSCSI Setup`:

iSCSI Setup
===========

This is a procedure for configuring a Drobo Pro for access via iSCSI.  This 
information is based on a post by Lemonizer on the Google Group 2009/05/16, with
updates based on improvements and tests by others in the fall of 2009::

  1. Connect the Pro via USB, and manually configure the ip of the dbpro

  # drobom info settings
  # drobom set IPAddress 192.168.2.80
  # drobom set NetMask   255.255.255.0
  # drobom set UseStaticIPAddress True

The next step is to  disconnect USB, and connect by iSCSI::

  2. Install open-iscsi (http://www.open-iscsi.org/): sudo apt-get install open-iscsi
  3. Connect the dbpro to host machine via iscsi
  4. Query dbpro's id: sudo iscsiadm --mode discovery --type sendtargets --portal 192.168.2.80
  5. Copy the id string returned by iscsiadm, something like "iqn.2005-06.com.datarobotics:drobopro.tdb091840080.node0"
  6. Connect to the dbpro: sudo iscsiadm --mode node --targetname iqn.2005-06.com.datarobotics:drobopro.tdb091840080.node0 --portal 192.168.2.80:3260 --login

If everything went well, your drobopro should show up under /dev. Also check /var/log/messages to 
confirm that the iscsi device connected successfully.  After that, drobo-utils should be able 
to detect the Drobo and manage it over ethernet/iSCSI.

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

when it's done, check if it worked using::

 root@pepino# drobom status
 /dev/sdf - 00% full - (['New firmware installed'], 0)

If the status is like that, then do::

 root@pepino:/home/peter/drobo/drobo-utils/trunk# drobom shutdown

lights will flash etc... wait until Drobo goes dark.
Wait another five seconds, then un-plug the USB / connector.
   
Plug it back in, and wait 10 seconds.
it should start up with the latest firmware available for the drobo.
   
The drobom commands, like DRI's dashboard, will normally
get the latest and greatest firmware and upgrade.  If necessary 
one can load arbitrary firmware from the CLI with fwload command.


SAFETY
======

Those worried about safety of using this software should know:  it was 
developed with assistance from the vendor (`Data Robotics`_ Inc.), and 
in every case, based on vendor documentation, and with at least encouragement,
if not outright support.  For each release, a QA.txt file is built, demonstrating the functionality tests run.  There are multiple checksum verifications built 
into the firmware upgrade process, so it is next to impossible to brick a drobo 
using the tools.  Drobo-utils verifies firmware checksums before attempting 
to upload the image to the device, and the device checks the firmware against 
the checksums as well.  New firmware is loaded into an alternate location 
from the currently active one, and if activation of the new firmware fails, 
the drobo will simply boot the old one.  
 
On the other hand, common sense rules do apply.  Setting the LUN size, or 
re-formatting a Drobo will erase all data whether it is done on Linux or 
any other operating system.  These are power tools, and they can do some 
damage data if used without proper care.  For example, the reliability 
of any storage unit does not reduce the need for backups it only makes doing them 
easier. A Drobo is an excellent place to put backups, but not a substitute for 
them.  Backups are the only way to address error 18 (the number of inches in 
front of the keyboard the source of the issue lies.) and no storage unit can 
protect against fire or flood.

Firmware Compatibility
======================

Drobo has been tested with every old firmware version. Any Drobo should
be upgradable to modern firmware using the dashboard.

for Drobo v1's (only models available to me used for QA)

   NOTE: really need at least 1.1.1 to use Linux & ext3.
         just use the tools to upgrade firmware ASAP.

   1.01  - very old... bad idea to install this, need to write
           a script to get out, because it isn't in the revision
           table.  not much works except firmware upgrade.
           DO NOT USE. UPGRADE ASAP

   1.0.2 - works ok in CLI And GUI to view, and upgrade firmware.
           DO NOT USE. UPGRADE ASAP

   1.0.3 - GUI and CLI work OK, can upgrade firmware.
           Used ntfs3g for a few months under ubuntu 7.10 Linux.
           Used 2 TB LUN, with 1.5 TB of physical space available.
           DO NOT USE. UPGRADE ASAP
            
   1.1.0 - dashboard works no issues.
         - from this point, you don't seem to need to unplug the USB
           connector to complete the upgrade.

         - firmware prior to here deals badly with ext3.

   1.1.1 - 1.2.4 works without issues. 
           ('name' not supported by firmware)

   1.3.0 - works without issues.
   1.3.5 - works without issues.


.. _Deployment:

Deployment
----------

No storage unit ever constructed, at any price point, can live upto the expectation 
of never losing data.  There is no magic wand to wave to solve the data security 
problem.  People still need a strategy around backups and their maintenance.  
Drobo makes it easier to implement a strategy, but does not replace it.
Data Robotics has a `best practices`_ page that says it well, but the phrasing
is a bit enterprisy, and while it provides general concepts, it is not 
prescriptive enough for people to easily apply.

.. _`best practices`:  http://www.drobo.com/support/best_practices.php

This section gives some examples & use cases to help people 
develop the appropriate strategy for them.  Try to keep it simple & concrete.

General Concepts
================

*Don't rely on a single device, ever!*  Before deploying a storage unit,
one should perform the thought experiment of what will happen if all data on
it is lost.  There are always levels of risk.  For personal use, one might 
accept the risk that if the house burns down, only have infrequent offsite 
backups are available and months or years of data may be lost.  If someone 
is running their business out of their home, this risk will likely not be 
acceptable. 

The simplest method of backing up your data is to put it in a humungous 
single place, and backup the whole thing.  That is a valid strategy, but
consider the following realistic case:

A company does incremental backups[#incrbkup] once a day, and full backup
once a week.  Once a month, a second full backup is kept as monthly, while the
weeklies are recycled.  Monthly backups are kept for a year, and each
year, one backup is kept for five years. So if you write data once and
keep it unchanged for five years, you will have 3 weekly backups, 11 monthlies,
and 4 yearly backups of that data, or 17 copies.  This strategy is not
unusual or particularly excessive, many corporate policies end up with 50 
or more copies of the data.

With that in mind, if you avoid backing up what you don´t need to, then you
are not saving just one byte, but all the copies too.  With a little thought, 
one can usually reduce the total storage needs by classifying data appropriately.

.. [#incrbkup] An incremental backup is where only what has changed since the last full backup is saved.   a full backup is a complete copy of all data.  

Different Drobo models have very different performance.  Deploying a Drobo
using a USB interface as primary storage is likely to disappoint.
See the compatibility matrix for details.


*Classify Your Data* 

There are different levels of value for data.  Things that are downloaded 
from the internet, or source code that is pushed to a repository on the internet, 
have natural backups in most cases.  The loss of data being queued for printing, 
might not be a terrible loss.   The loss of videos recorded off the air from 
television, might not be terrible either.

Any kind of data which is either not worth backing up, or for which a backups
already exist, does not need to be backed up locally.  The other end of the 
spectrum is proprietary data, for which copies on the internet are not be 
appropriate, and which is irreplaceable if lost.  In a photographic business,
the photos, Tax records, accounts, etc...  In a personal realm, these would 
include family photos, etc... lets call this sort of information *precious data*

That irreplaceable data is what you need to safeguard.   So the classification
can be done in a number of ways, but the simplest is just to only put precious 
data in the home directory.  So far that´s normal.  The unusual thing comes next: Do not put anything else there.  Internet downloads, easily replicable data, etc...
should go somewhere else.  In general, keep the home directories of users as small
and precious as possible.

As another example, in my personal use case, Linux is readily downloadable, so 
there are no system backups at all.  Configurations are relatively straightforward,
only credentials, and special configurations are backed up, by having copies
of the information in an normal /home directory of a user.  The restoral time 
for a single system is not an issue for my personal use, and by the time a 
restore is necessary, there will probably a new OS version to try out,
so the value of system backups is quite limited.

The only thing backed up, is the personal (/home) directories of a few users.


Primary Storage
===============

If a Drobo is used for primary storage for precious data, a second one should be 
obtained as a backup device.  It´s as simple as that.  Keeping all data on 
one device that cannot be backed up is asking for trouble.  

Zealots will say that the second unit should be off-site.  
The Gen 1 / Gen 2 Drobo´s are also have limited performance, and are perhaps not
well suited to a role as primary storage.


Scratch Storage
===============

If the data there is all space that either exists elsewhere (mirrors of internet
sites), can be regenerated  (object files of compilation, recordings from on-air 
broadcasts in a media server), none of this data is particularly precious, and
all of it can be recovered over time in the event of a data loss on one unit.

Again, one argument against such usage is performance.  First and second generation
units are a bit on the slow side for use in say.  On the other hand, media
serving is a streaming application with typically low instantaneous bandwidth
requirements, so even first generation Drobos should be fine for that.


Backup Repository
=================
A rational means of configuring the Drobo is as a backup repository.
The drobo is destination of the backups.  Primary copies are on the 
desktops & laptops being backed up.  Viewed in that way, backup data
is easily recovered in the event of a data loss: just backup the system
again.  Of course the history of backups is lost, but the important
thing is usually being able to recover current data.



Troubleshooting
---------------

No Drobos Discovered 
====================

To find Drobo on a system, drobo-utils queries all the attached devices for indications
it is made by `Data Robotics`_.  These strings change from product to product.
If the (new model) Drobo is not detected, then run the command line interface
with the hardware detection debugging output turned out.  like so::

 # drobom -v 16 status 
 examining:  /dev/sda 
 id:  (0, 0, 0, 0, 'ATA     ') 
 rejected: vendor is ATA      (not from DRI) 
 examining:  /dev/sdb 
 id:  (2, 0, 0, 0, 'ATA     ') 
 rejected: vendor is ATA      (not from DRI) 
 examining:  /dev/sdc 
 id:  (8, 0, 0, 0, 'Drobo   ') 
 rejected: vendor is Drobo    (not from DRI) 
 returning list:  [] 
 No Drobos discovered 

Here you see that the vendor string is 'Drobo' which was not a known vendor string
at the time this example was run.  so then try::

 # drobom -s Drobo status

In other words, take the unknown vendor string and feed it as -s option to tweak 
detection of drobom.  Your drobo will likely then be picked up.


Only One LUN Shows up?
======================

LUN is an abbreviation of 'Logical UNit'. The origin of the term is 
SCSI[#SCSI]_ terminology.
When RAID units became too large for support in the past, and were sub-divided 
to present smaller units the operating system.  The default LUNSIZE on Drobos 
is 2 TiB (adjustable using the tools.) If more disk space (after allowing for 
parity/redundancy) than LUNSIZE is installed in a unit, Drobo will show a 
second (or even third) LUN.  Each LUN shows up in Linux as a separate disk 
(examples if the first LUN shows up as /dev/sde, the next will be /dev/sdf, 
then /dev/sdg.)

If you think you should see multiple LUNS and you don't, you might have a look at 
some kernel settings: make sure that scsi_mod kernel module is loaded, make 
sure /sys/module/scsi_mod/parameters/max_luns is > 1.

Drobom view will start up one GUI per drobo, regardless of the number
of LUNS.  If asked to format, all LUNS for the device will be formatted.

.. [#SCSI] Small Computer System Interface. A ubiquitous standard for computers to
   communicate with storage hardware.  SCSI includes hardware cabling specifications,
   which are mostly obsolete, but what remains is the "command set", the language used
   by the computer to make requests to the device.  In that sense, All Drobos are SCSI devices.
   The SCSI commands are tunnelled within other protocols used to transport data between
   computer and device (Firewire, USB, eSATA, and, yes... ISCSI)

Getting Help from DRI
=====================

DRI intends Drobospace.com for owners to talk with one another, except no non-owner 
can see the discussions, and early on, there was a lot of input from DRI staff, so 
it looked a lot like a support forum, but it really isn't.   A lot of owners 
objected to these forums being private, so a google group was started for people 
to talk with one another, and the discussions to remain public:
 
http://groups.google.com/group/drobo-talk/topics?hl=en
 
There is still a great role for Drobo space, in that Tier 3 support analysts 
(essentially developers.) sometimes look over there. For tier 3 support, one 
cannot expect guaranteed response time, but one may be able to provide some 
input into future products or firmware features.  It turns out that the 
Drobospace forums aren't really for support.  but don't take my word for it,
here is above was DRI's take (verbatim from a post on 
drobospace by MarkF 2008/08/29) on things:

To contact `Data Robotics`_ Inc. for support your options are:

1. phone support - technical issues: 1-866-426-4280, Mon-Fri from 8am-5pm PST, excluding Holidays. 

2. phone support - presales questions: 1-866-99ROBOT 

3. email support - technical issues: support@drobo.com

4. email support - presales questions: sales@drobo.com

5. web-based support request: http://www.drobo.com/Support/Request_Support.html

All technical support calls, emails, and web requests are assigned a case number 
and tracked. DRI has 3 tiers of customer support. Tier 1 and 2 handle the majority 
of cases. They are responsible for tracking phone, email, an web cases and 
resolving them. Some cases are escalated to Tier 3 whose personnel reside 
in our corporate headquarters and have access to engineering staff.

Support on Drobospace.com:

Drobospace.com is a user community and relies on the volunteer efforts of its members to help each other. Because it is run by volunteers response to problems varies. Tier 3 support personel monitor the Drobospace forums -- tiers 1 and 2 are focused directly on customers, and they are not required to read drobospace.com. By design Tier 3 personnel do not immediately respond to each posting in order to allow the community to function. Depending on the nature of the problem, tier 3 may post in the forum or contact the member directly through a private message to facilitate problem resolution.

Because Drobospace is owned and run by a third party, Capable Networks LLC, there is no linkage with DRI's database systems. Posts here are not assigned case numbers and tracked - that only happens with cases opened directly with DRI.

-------------------------------------------------------------------------




FAQ
---

What LUNSIZE should I use?
==========================

2 Terabytes is the biggest you should use for now.  There are lots
of experiments on the google groups, summarized here: `LUNSIZE fits all`_
Also consult the compatibility matrix indicates best guesses at the
current state of affairs.  DRI announced new firmware 1.1.4 for Drobo PRO
which is supposed to remove the 2 TiB restriction, but that isn't confirmed
yet.

What Happens When I Used A Bigger LUNSIZE?
==========================================

That's actually a bit nasty.  Nothing happens at first, everything seems
to work fine.  After a while, it fails to reclaim space when files are deleted.
The blue capacity lights don't show much relation to how full the file system 
is, as reported by the operating system.  Drobo may become insatiable, always
asking for more and more disk space, even though the amount of data used
on the file system doesn't warrant it.  In extreme cases, data may become 
in-accessible.


How Do I Check That a LUNSIZE Works?
====================================

DRI naturally releases new versions of firmware and may fix these issues
at some point.  If you are willing to test it out on your new Drobo, the
procedure to do so is simple::

   1.  Create a file system as per normal.  
   2.  Fill the physical space up.  (blue lights should light up.)
   3.  Remove alot of the data. 

If the problem is not there, then blue lights will function properly and go
out to correspond to the deleted data after a while.  If the blue lights
do not go out after step 3, then do not trust your data to this file system.
Re-create with a smaller LUN, and try again.  2 Terabytes is the only case
of documented success so far.

Can I user ReiserFS, XFS, BTRFS, xxfs ? 
=======================================

Short answer: no.

For Drobo to perform storage management, it has to know what space is free, so it 
needs to understand the file system you are using.  The list of file systems 
it official understands is: FAT32, NTFS, HFS+, ext3.  That's it, so if you want 
to use reiserfs, or xfs, or GFS, or whatever... you are doing research. The 
vendors says those other file systems types will not work. 


If my Drobo breaks, Can I Get My Data back?
===========================================

No. The way the data is placed on the disks is completely proprietary.
You cannot take the drives and connect them individually to a server, and read
the data off that way, because it isn't a linux md or lvm format that can easily
be reconstructed.  You cannot give the disk pack to a data recovery company, 
because they do not know the data format either, and you will have to pay them
to reverse engineer DRI's format, which will get expensive quickly.

You need either a backup, or another Drobo.  Even among Drobos there
are limits to compatibility see the Drobo.com web site for details.


My USB Drobo always comes up as a different Disk!
=================================================

The order and timing of disks being connected to hot-plug busses will
determine the device name (it might be /dev/sdb one time, and /dev/sdc another.)
So putting /dev/sdX in the fstab to mount their disks, as is traditionally done,
won't work.  Instead, do::

 peter@pepino:~$ ls -l /dev/disk/by-uuid
 total 0
 lrwxrwxrwx 1 root root 10 2009-12-15 04:54 2C88743C8874071C -> ../../sda3
 lrwxrwxrwx 1 root root 10 2009-12-15 04:54 32a41d0a-b193-41f3-86fa-29bbee8cd2b3 -> ../../sda8
 lrwxrwxrwx 1 root root 10 2009-12-26 12:08 3cd5d9cc-c227-4ed8-bab2-60c2d71f6e9d -> ../../sdf1
 lrwxrwxrwx 1 root root 10 2009-12-15 04:54 72b0ee8c-d0e8-479d-b79c-3dbda1581f55 -> ../../sda6
 lrwxrwxrwx 1 root root 10 2009-12-15 04:54 814472db-dbee-411c-8870-7ca59f32e7c1 -> ../../sda5
 lrwxrwxrwx 1 root root 10 2009-12-26 12:16 8ed93296-9be2-4576-9ae4-9d9c78363fb6 -> ../../sdg1
 lrwxrwxrwx 1 root root 10 2009-12-15 04:54 a4bc252e-0eb7-489c-94e7-688efd528665 -> ../../sda7
 lrwxrwxrwx 1 root root 10 2009-12-15 04:54 bc1ab400-df49-457d-8700-c77dde19e450 -> ../../sda2
 lrwxrwxrwx 1 root root 10 2009-12-15 04:54 C2EE700DEE6FF7D5 -> ../../sda1
 peter@pepino:~$
 
The UUID is a name that is constant for a partition.  Each time a partition
is mounted, a link will be created in this directory towards the correct
/dev/sdX.  A UUID related /etc/fstab entry looks like::

 UUID=3cd5d9cc-c227-4ed8-bab2-60c2d71f6e9d  /drobo01   ext3 defaults 0 2 
 

How come the command to build a file system builds an ext2 file system?
=======================================================================

because an ext3 file systems is an ext2 file system with a journal.  
The normal command to build an ext3 file system is mke2fs -j.  

Can you have different LUNS with different file systems on them?
================================================================

DRI: Multiple partitions per LUN is supported. Having any combination of file
supported file systems on the different LUNS and partitions is fine as well.

Does Drobo work with LVM?
=========================

`Some people do it`_. I would not risk it.

.. _`Some people do it`: http://www.norio.be/blog/2008/11/setting-drobo-linux

The Linux Volume Manager is a layer of software which is shimmed between the file system layer, and the physical disks.  It provides a 'fake' (virtual) volume on which file systems are built.  This gives flexibility to concatenate several physical volumes together to make a single file system, or allocate a single volume to different file systems over time, as needs dictate rather than all at the outset.

For Drobo, LVM would be especially cool in that one could initially allocate only 
the physical space actually available within the LUN, and thus applications which
key on avoiding filling file systems would function correctly, instead of always 
asking to insert more storage, and not managing the storage available.  When more
physical space (new drives!) becomes available, one could allocate more space to 
the virtual volume, and then grow the file system.   So Drobo would still take 
care of the drudgery of RAID set maintenance, relay operations, etc... but the 
user would have more control on how space was allocated at the OS level.

For that to work, Drobo firmware would have to understand LVM to some extent.  
Initial experiments showed that the firmware didn't appreciate LVM.   Being 
able to add a Drobo unit as an pv to an LVM unit would be very cool.


Does Drobo Support Full Disk Encryption?
========================================

Drobo works by knowing how the file system is laid out and pretending to have 
more space than is physically present.   Drobo does some sleight of hand to 
manage disk space and move things around optimally as hard disks fail or are 
added.
 
Full disk encryption implemented by the operating system makes the Drobo unable 
to understand the file system, so it doesn't know which blocks are in use, and 
the unit will always believe the system is completely full.  Drobo will not 
behave well.  Among the methods that will not work are any that operate on a 
raw disk partition, such as truecrypt, or any of the linux cryptoloop based solutions.
 
Instead of whole disk encryption, a method that uses an underlying file system 
that is well known to the Drobo (the list is short: FAT32, NTFS, HFS, EXT2) is 
needed. On windows, encrypting directories with standard NTFS will work fine.  
On Linux, a good choice would be EncFS http://www.arg0.net/encfs, which encrypts 
file names and data over an ext file system, or some other method which uses 
FUSE  http://fuse.sourceforge.net.  is reported to work well.
 

I have read everything. Help?
=============================

Best first stop is the google Group_.


What is Drobo-utils' License?
=============================

General Public License  - Gnu - GPL .  


Credits
-------

who did what::

 Peter Silva:    wrote most all of it.
 Chris Atlee:    the proper debian packaging. 
 Brad Guillory:  some help with diagnostics and patches.
 Joe Krahn:      lots of inspiration.
 Andy Grover:    some elegance cleanups. 
 Sebastian Sobolewski:  DroboPro patches, and testing.

Testers (of DroboPRO):
robj, Sebastian (aka Tom Green), ElliotA, Andrew Chalaturnyk 

 
Administrivia
-------------

version 9999, somewhen



copyright:

Drobo Utils Copyright (C) 2008,2009  Peter Silva (Peter.A.Silva@gmail.com)
Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.
