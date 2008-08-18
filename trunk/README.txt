This software is copyright under GPL.  See near end file for details...

WHAT IS THIS?

Drobo-utils is a set of linux tools to query and manage Data Robotics
Drobo storage systems.   If you fire up droboview, it should look pretty
familiar to those who have seen the dashboard on other operating systems. 
Droboview is built on a little programmer interface which can be installed 
on the system and used by other applications as well.

For experienced Linux hands, there is a command line interface, drobom,
which offers the same functionality as droboview.


COMPONENTS:

  droboview   - Graphical User interface to see how the Drobo is doing.
                this is a bit like the ´dashboard´ app for other OS´s.
  drobom      - CLI script, accesses Drobo.py with no GUI stuff.
  DroboGUI.py - implements GUI. uses Drobo.py for Drobo related stuff.
  Drobo.py   -- overall Drobo io manager, provides API & "python CLI"
                uses DroboDMP.c to do raw io.
  DroboDMP.c -- python module to perform the detailed drobo ioctls.
                only platform specific stuff is in here...
  setup.py --   python version of a Makefile


Getting a Snapshot:

   svn co https://drobo-utils.svn.sourceforge.net/svnroot/drobo-utils/trunk

   For commit access, you need a sourceforge user account.

 

REQUIREMENTS:

drobo-utils was developed on pre-release version of Kubuntu Hardy Heron.
Any similarly recent distro ought to do.

To get drobo-utils running, you need packages something like (these are
ubuntu packages, names may vary on other distros):

essential:
  python      -- interpreter for python language
  python-qt4  -- python-qt4... This is actually a new version only in 
                              the newest distros.
  libsgutils1-dev -- ioctl support.
  python-dev      -- to build DroboDMP extension.

options:
  gtksudo or kdesudo - searches on startup for one or the other.
           if neither are around, then get a graphical sudo of you choice
	   and add it to the search list at the end of DroboGUI.__init__ 
  parted   for >= 2TB file systems, need GPT support.
           just use fdisk  for smaller stuff.

To get a complete list, it is best to use a shell window to grep in the 
Debian package control file (which defines what the dependencies are for the
build system):

peter@pepino% grep Depend debian/control
Build-Depends: debhelper (>= 5), python2.5-dev, libc6-dev, libsgutils1-dev
Depends: ${shlibs:Depends}, ${misc:Depends}, python-qt4, libsgutils1
peter@pepino%      
peter@pepino% grep Recommend debian/control
Recommends: parted, gparted, kdesudo, gtksudo
peter@pepino% 

INSTALLING pre-requisites.:  
On ubuntu, it would typically look like so:

	open a shell window. Enter the following package installation commands:

        % sudo aptitude install python-qt4 libsgutils1 
        % sudo aptitude install debhelper python2.5-dev, libc6-dev libsgutils1-dev 
	% sudo aptitude install parted kdesudo

If you have received a pre-built binary package,then you only need the first line.
If you want to build from source, then you need the second line.  The third line
just has useful optional tools.

On redhat/fedora distros, it would more likely be 'yum' instead of 'aptitude' and
some of the package names will change.  A typical difference is that packages for developers
have the -devel suffix on Redhat derived distributions, instead of the -dev favoured
by debian derived ones.

here is an exmple from fedora 7 (courtesy of help4death on the google group):

% yum install python
% yum install sg3_utils
% yum install PyQt4
% yum install python-devel
% yum install libsgutils.so.1
% yum install sg3_utils-devel 


INSTALL:
Assuming you have all of the above parts, you should be able to just do:

	python setup.py build

which on my system looks like this:
alu% python ./setup.py build
running build
running build_py
creating build
creating build/lib.linux-i686-2.5
copying Drobo.py -> build/lib.linux-i686-2.5
copying DroboGUI.py -> build/lib.linux-i686-2.5
running build_ext
building 'DroboDMP' extension
creating build/temp.linux-i686-2.5
gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.5 -c DroboDMP.c -o build/temp.linux-i686-2.5/DroboDMP.o
gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions build/temp.linux-i686-2.5/DroboDMP.o -o build/lib.linux-i686-2.5/DroboDMP.so
running build_scripts
creating build/scripts-2.5
copying and adjusting drobom -> build/scripts-2.5
copying and adjusting droboview -> build/scripts-2.5
changing mode of build/scripts-2.5/drobom from 644 to 755
changing mode of build/scripts-2.5/droboview from 644 to 755
alu%   

It should create a build/lib<something> sub-directory.  It will also
compile DroboDMP.c and put the result in a shared object object library 
in that directory.   The normal package wants to find the libraries
in system installed places.  If you want to test things without
installing, then you can do either:

Look in Drobo.py, and uncomment these lines:

#m = re.compile("lib.*")
#for l in os.listdir("build"):
#    if m.match(l) :
#        sys.path.insert(1, os.path.normpath("build/" + l ))

This is fine for testing, but will only work if invoked
from the directory containg the drobo-utils files.  Once
installed using 'install' or a built package, these lines
are not needed.

Another way to enable testing without installing is to:

C-ish shells:
setenv PYTHONPATH `pwd`/build/lib.linux*

Bournish shells:
export PYTHONPATH=`pwd`/build/lib.linux*

If all has gone well, you can kick the tires 
by starting it up with: 
         
        ./drobom status 

see if something sensible happens... on my system with a drobo
the following happens:

% ./drobom status
/dev/sdd 100% full - ['Red alert', 'Bad disk', 'No redundancy']
%
very scary, but my drobo is in bad shape right now... you should just get []
as a status, which means there is nothing wrong.   If you get an error
like it isn't detecting any drobos:

No Drobo discovered, is one connected?

Try to start up drobom from the root account. (sudo drobom..., or 
sudo bash, or su - ) To get all kinds of information on your drobo, 
try './drobom info.'  You can then invoke it with no arguments at all 
which will cause it to print out a list of the commands available 
through the command line interface.

Once the command line stuff that is working, and assuming you have python-qt4 
installed, try:

	./droboview

which should start a GUI for each drobo attached to your machine, that
you have permission to access (depends on the setup, usually USB devices 
on desktops are accessible to users, so you can see them.  Servers might be 
setup differently, haven't worked out how to install it correctly yet.


Setup Drobo with Linux:

There is no functionality in the UI´s or API to partition or build
file systems on the Drobo.  Just use the system tools...

Drobos with firmware 1.1.1 or later work fine under linux with ext3.
You can, of course set up an NTFS or HPS+ or FAT32 if you really want,
but it seems actively counter-intuitive on Linux.  Have not tested
HPS, but ntfs-3g worked fine initially.  However, unless you are
going to physically move the disk to between systems, the native (ext3) 
format has many advantages.  The ´coffee is hot´ disclaimer is 
necessary at this point:

WARNING: THE FOLLOWING 4 LINES WILL ERASE ALL DATA ON YOUR DROBO!
WARNING: NO, IT WILL NOT ASK ANY QUESTIONS!
WARNING: ASK YOURSELF, before you start: ARE YOU SURE? 
WARNING: AFTER THE SECOND LINE, YOU ARE TOAST.
WARNING: BEST TO BACKUP YOUR DATA BEFOREHAND...

Here is what you have to type:
parted -i /dev/sdd 
mklabel gpt
mkpart ext2 0 100%
quit

The above sets up the drobo as one big partition, with a label that says
it ought to contain an ext2 file system.  If you want an NTFS file system,
then write ´ntfs´ in place of ext2.  The next step is to add the file
system into the partition.  while the above step was instantaneous, the step 
below takes a while, just have a little patience, it´ll be fine.

From the Doboshare forums, building a file system:

mke2fs –j –i 262144 –L Drobo01 -m 0 –O sparse_super,^resize_inode  /dev/sdd1

(If you want an ntfs file system, then mkntfs -f -L Drobo01 /dev/sdd1 
ought to work too... )
On my system the process looked like this:

-------------------
root@alu:~# parted -i /dev/sdd
GNU Parted 1.7.1
Using /dev/sdd
Welcome to GNU Parted! Type 'help' to view a list of commands.
(parted) mklabel gpt
(parted) mkpart ext2 0 100%
(parted) quit
root@alu:~# fdisk /dev/sdd
GNU Fdisk 1.0
Copyright (C) 1998 - 2006 Free Software Foundation, Inc.
This program is free software, covered by the GNU General Public License.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

Using /dev/sdd
Command (m for help): p

Disk /dev/sdd: 2199 GB, 2199020382720 bytes
255 heads, 63 sectors/track, 267349 cylinders
Units = cylinders of 16065 * 512 = 8225280 bytes

   Device Boot      Start         End      Blocks   Id  System
/dev/sdd1               1      267350  2147488843   83  Linux
Command (m for help): q
root@alu:~# mke2fs -j -i 262144 -L Drobo01 -m 0 -O sparse_super,^resize_inode /dev/sdd1
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
root@alu:~# mount /dev/sdd1 /mnt

-------------------

NOTES:

drobo-utils is completely untested with multiple LUNS.  Best to make LUN
large enough to span all your space.  starting up droboview will probably 
spawn a GUI for each LUN, so you may end up seeing double...

Probably not a good idea to run two GUI's for a single drobo.  the GUI
polls continuously for changes to the device, and that might interfere
if you try to, say, upgrade the firmware, with the other GUI.

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


Firmware manipulation:
   The line mode interface has two commands to deal with firmware,
   fwcheck will tell you if an upgrade is required.
   fwupgrade will do the work.  It takes a few minutes, and prints 
   a status you you can see how it is progressing.  have patience.

   Before you start, please any file systems using the Drobo so
   that one is free to re-start it once the firmware is loaded.

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

   when it's done, you can check if it worked using:

   root@pepino:/home/peter/drobo/drobo-utils/trunk# drobom status
   /dev/sdf 00% full - ['New firmware installed']

   If the status is like that, then do:

   root@pepino:/home/peter/drobo/drobo-utils/trunk# drobom standby

   lights will flash etc... wait until Drobo goes dark.
   Wait another five seconds, then un-plug the USB / connector.
   
   Plug it back in, and wait 10 seconds.
   it should start up with the latest firmware available for your drobo.
   

   The drobom commands, like DRI's dashboard, will only permit you
   to get the latest and greatest firmware and upgrade.  if you
   don't mind using python, you can also load arbitrary firmware
   files like so:

   #!/usr/bin/python
   import Drobo
   l=Drobo.Drobo("/dev/sdf")
   if l.PickFirmware("/home/peter/.drobo-utils/v1.10.tdf"):
      l.writeFirmware()
   else:
      print 'failed to validate firmware'

   
Caveats:
   droboview isn't suited to run continuously for long periods, 
   as it has a memory leak...  total foot print starts out at 32M
   with a 15 MB resident set size, of which 10 MB are shared, so only 
   about 4M of real memory consumed.   but the RSS grows at about 
   2MB/hour.

   29m  11m S    1  2.9   9:44.50 droboview

   best to restart it daily, or use it when necessary, but not leave it
   on for days.




Building a debian package:

   (assumes you have installed the Build dependencies...)

   cd trunk
   dpkg-buildpackage -rfakeroot
   cd ..
   su
   dpkg -i droboutils_0.1.1-1_i386.deb

   (Doesn't work on amd64... no clue why... help welcome...)


Firmware Compatibility:
  If your Drobo has firmware version:

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

   1.1.1 - works without issues.

   1.1.2 - works without issues.


Revision date: 2008/08/10

copyright:

Drobo Utils Copyright (C) 2008  Peter Silva (Peter.A.Silva@gmail.com)
Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.
