"""

  This module is used to get configuration data 
  from a Data Robotics Inc. "Drobo" storage unit.
  
  Information here is based on the:
        DROBO Management Protocol Specification Rev. A.0 03/08

  referred herein as 'DMP Spec'
  droboprotocoldefs.h is the other source of info.  They conflict. A lot.
  referred to in here as dmp.h

  This program is copyright (C) 2008 Peter Silva. All Rights Reserved.
  (Peter.A.Silva@gmail.com)

  ( Drobo is a trademark of Data Robotics Inc. )

  search for ERRATA for the stuff that confused me...

  was tested with firmware: 1.0.3 and now using 1.1.1

copyright:
Drobo Utils Copyright (C) 2008  Peter Silva (Peter.A.Silva@gmail.com)
Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.

"""

import fcntl, struct, socket, array, commands, time
import exceptions
import os, sys, re
import types

#only for fw download...
import os.path
import urllib2
import zipfile,zlib

#only for simulation mode...
import random

# maximum transaction ID before wrapping...
MAX_TRANSACTION = 250

# obviously need to update this with every release.
VERSION = 'running trunk at: ' + time.ctime(time.time())


# set to non-zero to increase verbosity of library functions.
DEBUG = 0
# It's a bit field, 
DBG_Chatty = 0x01 
DBG_HWDialog = 0x02
DBG_Instantiation = 0x04
#DBG_DMP = 0x08 # C-layer...  not used here...
DBG_Detection = 0x10
DBG_General = 0x20 

# This isn't entirely simulation mode.  It is to aid development
# when no drobo is available.  you can format random disks, including 
# non-drobos.  So do not activate unless you read what the code does first.
DBG_Simulation = 0x80

#for generic SCSI IO details...
import DroboIOctl


class DroboException(exceptions.Exception):
  """  If there is a problem accessing the Drobo, this exception is raised.
  """
  def __init__(self):
     return

  def __str__(self):
     print " problem accessing a Drobo"


#def hexstr(hexstring): 
#    """ convert an array into a string representing hex...  """
#
#    i=0
#    for c in hexstring:
#       if ( i % 8 ) == 0:
#          print "\n%02x -" % i,
#       print "%02x" % ord(c),
#       i=i+1
#    print

def _ledstatus(n):
    """ return colors decoded, given numeric slot status 
            goal: match what the lights are doing on the unit.

        STATUS: working with ERRATA:
        Developer Notes:
        The spec says: status is high order 3 bits, and starting from 0, goes:
		green, yellow, Red, ( Green Yellow )

        dmp.h says:
        forget the high order 3 bits, it's the whole byte.
        off is supposed to be 0, but doesn't match when flashing red green..
           off, red, yellow, green, yellow-green, red-green, red-off, red-yellow 

        my drobo says: 
                high order bits always 0. status seems to use whole byte.
		green is 3,  
		flashing red-green is 4...  which dmp.h says is yellow green
                flashing red-black is 6...  agrees with dmp.h
		0x80 is indeed an empty slot, as per dmp.h
                unknown-- yellow-green...
        matches neither... hmm...        
    """
    colourstats=[ 'black', 'red', 'yellow', 'green', ['red', 'green'], 
      [ 'red', 'yellow' ], ['red', 'black'] ] 
    if DEBUG & DBG_General:
         print 'colourstats, argument n is: ', n
    if ( n == 0x80 ):  # empty
       return 'gray'
    return colourstats[n & 0x0f ]


def _unitstatus(n):
    """ return string, given numeric unit status 
   
    STATUS: working with ERRATA:
        here is what the spec says should work (integers...):
    ust = [ 'Normal', 'Red Threshold Exceeded', 'Yellow Threshold Exceeded',
      'No Disks',  'Bad Disk',  'Multiple Disks Removed', 'No Redundancy', 
      'No Magic Hotspare', 'Unit Full', 'Relay Out in Progress', 
      'Format in Progress' ]
    return ust[n]   

    the .h files says... no stupid... it's bit fields.  I don't much care
    as long as folks make up their mind. I have a higher regard for the .h
    so that implementation is active.
    """
    f = []
    if ( n & 0x0002 ):
       f.append( 'Red alert' )
    if ( n & 0x0004 ):
       f.append( 'Yellow alert' )
    if ( n & 0x0008 ):
       f.append( 'No disks' )
    if ( n & 0x0010 ):
       f.append( 'Bad disk' )
    if ( n & 0x0020 ):
       f.append( 'Too many missing disks' )
    if ( n & 0x0040 ):
       f.append( 'No redundancy' )
    if ( n & 0x0080 ):
       f.append( 'No magic hotspare' )
    if ( n & 0x0100 ):
       f.append( 'no space left' )
    if ( n & 0x0200 ):
       f.append( 'Relay out in progress' )
    if ( n & 0x0400 ):
       f.append( 'Format in progress' )
    if ( n & 0x0800 ):
       f.append( 'Mismatched disks' )
    if ( n & 0x1000 ):
       f.append( 'Unknown version' )
    if ( n & 0x2000 ):
       f.append( 'New firmware installed' )
    if ( n & 0x4000 ):
       f.append( 'New LUN available after reboot' )
    if ( n & 0x10000000):# was going to say 'Let us pray...', but no need to alarm people.
       f.append( 'Unknown error' ) 

    return f

def _partformat(n):
    """ return Drobo's idea of what the partition type is

        STATUS: working with ERRATA: 
           the codes are wonky...

           dmp.h says 0x08 for EXT3, but my Drobo says, 0x80 
                 says 0x01 is 'no format', but my Drobo says that is NTFS.
           tried added >>4 but that

	   says only one bit is supposed to be set, but, I dunno if I trust it.

           returning a tuple for now.
    """
    f = []
    
    if ( n & 0x01 ):
       f.append( 'NTFS' )
    if ( n & 0x02 ):
       f.append( 'NO FORMAT' )
    if ( n & 0x04 ):
       f.append( 'HFS' )
    if ( n & 0x80 ): # on Peter's...
       f.append( 'EXT3' )
    #if ( n & 0x08 ): # on Matthew Mastracci's
    #   f.append( 'EXT3' )
    if ( n & 0xFF ) == 0:
       f.append( 'FAT32' )

    if (len(f) != 1):
      print 'hoho! multiple partition types! Brave are we not?' 

    return f


def _partscheme(n):
   """ return what drobo thinks the partition scheme is

       STATUS: working, no issues.
       Have set all of them on my drobo using parted, was detected correctly.
   """
   if (n == 0):
     return "No Partitions"
   if (n == 1):
     return "MBR"
   if (n == 2):
     return "APM"
   if (n == 3):
     return "GPT"
   
def _unitfeatures(n):
    """ return a list of features supported by a unit
    
        STATUS: working.
        this comes straight from dmp.h.. what they mean isn't documented.
        stuff that looks wrong:	
		-- USED_CAPACITY... should be USE_CAPACITY ... no 'D'
		-- all the 'SUPPORTS' texts are redundant. every bit is about
                   what is supported.  It should be just LUNINFO2
         etc...			
    """
    f = []
    if ( n & 0x0001 ):
       f.append( 'NO_AUTO_REBOOT' )
    if ( n & 0x0002 ):
       f.append( 'NO_FAT32_FORMAT' )
    if ( n & 0x0004 ):
       f.append( 'USED_CAPACITY_FROM_HOST' )
    if ( n & 0x0008 ):
       f.append( 'DISKPACKSTATUS' )
    if ( n & 0x0010 ):
       f.append( 'ENCRYPT_NOHEADER' )
    if ( n & 0x0020 ):
       f.append( 'CMD_STATUS_QUERIABLE' )
    if ( n & 0x0040 ):
       f.append( 'VARIABLE_LUN_SIZE_1_16' )
    if ( n & 0x0080 ):
       f.append( 'PARTITION_LUN_GPT_MBR' )
    if ( n & 0x0100 ):
       f.append( 'FAT32_FORMAT_VOLNAME' )
    if ( n & 0x0300 ):
       f.append( 'SUPPORTS_DROBOSHARE' )
    if ( n & 0x0400 ):
       f.append( 'SUPPORTS_NEW_LUNINFO2' )
    if ( n & 0x80000000 ):
       f.append( 'SUPPORTS_SINGLE_LUN_FORMAT' )
    if ( n & 0x40000000 ):
       f.append( 'SUPPORTS_VOLUME_RENAME' )
    return f

class Drobo:
  """
  Drobo the class for data exchange with the storage units.
  
  briefly, communicates using SCSI sub_page blocks. 
  There are member functions for each page type...

  See the DMP Spec for details.

  All capacity returned are in bytes.

  the rest of this comment is destined only for Drobo.py developers, not users:
  DMP Spec ERRATA, by subpage:
         - in config, last Q is capacity, manual says bytes, sample code 
           says *512, which works better... so actual quantity is 512 byte blocks.
         - in slotinfo, 
            'managed capacity' is always 0, is that OK? 

         - in version, seems to want an extra byte. BB fails, but BBB works... returns  
         - in settings, the 32 byte name starts with a null byte before 
            'TRUSTED DATA', is that normal?
  """


  def __init__(self,chardevs,debugflags=0):
     """ chardev is /dev/sdX... 
         the character device associated with the drobo unit
     """   
     global DEBUG

     DEBUG=debugflags

     if DEBUG & DBG_Instantiation :
        print '__init__ '

     self.fd=None

     if type(chardevs) is types.ListType:
        self.char_dev_file = chardevs[0]
        self.char_devs = chardevs
     else:
        self.char_dev_file = chardevs
        self.char_devs = [ chardevs ]

     self.features = []    
     self.transactionID=random.randint(1,MAX_TRANSACTION)

     self.relaystart=0
 
     if DEBUG & DBG_Simulation == 0:
        self.fd=DroboIOctl.DroboIOctl(self.char_dev_file,0,debugflags)
        if self.fd == None :
            raise DroboException

        # more thorough checks for Drobohood...
        # for some reason under ubuntu intrepid, start getting responses of all bits set.
        # need some ways to spot a real drobo.  
        cfg = self.GetSubPageConfig()
        if DEBUG & DBG_Detection:
            print "cfg: ", cfg

        if ( len(cfg) != 3 ): # We ask this page to return three fields...
            if DEBUG & DBG_Detection:
              print "%s length of cfg is: %d, should be 3" % (self.char_dev_file, len(cfg))
	    raise DroboException 

        if ( cfg[0] != 4 ): 
            if DEBUG & DBG_Detection:
              print "%s cfg[0] = %s, should be 4. All Drobos have 4 slots" % (self.char_dev_file, cfg[0])
	    raise DroboException # Assert: All Drobo have 4 slots.
 
        set=self.GetSubPageSettings()
        if DEBUG & DBG_Detection:
            print "settings: ", set

        fw=self.GetSubPageFirmware()
        if ( len(fw) < 8 ) and (len(fw[7]) < 5):
            if DEBUG & DBG_Detection:
              print "%s length of fw query: is %d, should be < 8." % (self.char_dev_file, len(fw))
              print "%s len(fw[7]) query: is %d, should be < 5." % (self.char_dev_file, len(fw[7]))
            raise DroboException

        if ( fw[6].lower() != 'armmarvell' ):
            if DEBUG & DBG_Detection:
              print "%s fw[6] is not armmarvell." % self.char_dev_file
            raise DroboException
        



 
  def __del__(self):

     if DEBUG & DBG_Instantiation :
        print '__del__ '

     if self.fd != None :
           self.fd.closefd()

     self.fd=None


  def format_script(self,fstype='ext3'):
     """ return a shell script giving the code to commands required to 
     format the single LUN represented by a given drobo...
     
     pscheme is one of: mbr, apt, gpt,  
          gpt - >= 2 TB, linux or windows...
          mbr <= 2 TB good for FAT32

     fstype is one of:  fat32, ext3, ntfs (HPS+ is not supported on linux)
     sizes in terabytes

     not implemented yet...
     each lun is formatted as a single primary partition.
     partitions are never marked bootable.

     need to detect each lun...
     ok, but if a single drobo has multiple luns, how do we know which
     LUNS refer to a given drobo?

     algorithm:
	do discoverLUNs()
        figure out which LUNs belong to the current Drobo... How?
          -- do not want to partition LUNS on another Drobo!
             That would be bad!

        for l in LUN:
            parted /dev/sd?? mklabel gpt mkpart pri ext2 0 -1
            mke2fs -j ... /dev/sd??

     """    

     format_script='/tmp/fmtscript'
     fd=open(format_script, 'w')
     fd.write( "#!/bin/sh\n" )

     if fstype == 'FAT32':
         ptype='msdos'
     else:
         ptype='gpt' 

     fd.write( "parted %s mklabel %s\n" % (self.char_dev_file, ptype) )

     # there is a bit of a race condition creating the partition special file.
     # the parted print gives a little time before starting the mkfs, to ensure
     # file is there...

     if fstype == 'ext3': 
         # -m 0 -- Drobo takes care of complaining when near the size limit.
         #         little point in complaining early, pretending you have less space.
         # ^resize_inode -- Drobo makes the file system much bigger than the actual space
         #       available ( >= 2TB ) , so it doesn't make sense to allow space for future
         #       inode expansion beyond that.  only makes sense in LVM, that's why this
         #       option is 'off' (the '^' at the beginning.)
         # sparse_super -- there are lots too many superblock copies made by default.
         #       safe enough with fewer.
         fd.write( "parted %s mkpart ext2 0 100%%\n" % self.char_dev_file )
         fd.write( "parted %s print; sleep 5\n" % self.char_dev_file )
         fd.write( 'mke2fs -j -i 262144 -L Drobo01 -m 0 -O sparse_super,^resize_inode %s1\n' % self.char_dev_file )
     elif fstype == 'ntfs':
         fd.write( "parted %s mkpart ntfs 0 100%%\n" % self.char_dev_file )
         fd.write( "parted %s print; sleep 5\n" % self.char_dev_file )
         fd.write( 'mkntfs -f -L Drobo01  %s1\n' % self.char_dev_file )
     elif fstype == 'FAT32':
         fd.write( "parted %s mkpart primary fat32 0 100%%\n" % self.char_dev_file )
         fd.write( "parted %s print; sleep 5\n" % self.char_dev_file )
         fd.write( 'mkdosfs -v -v -F 32 -S 4096 -n Drobo01 %s1\n' % self.char_dev_file )
     else:
         print 'unsupported  partition type %s, sorry...' % fstype
     fd.close()
     os.chmod(format_script,0700)

     #if DEBUG & DBG_Simulation !=0:
     return format_script 
     #fmt_process = subprocess.Popen( format_script, close_fds=True )
     #pid, sts = os.waitpid(fmt_process.pid, 0)
     

  def __getsubpage(self,sub_page,pack): 
    """ Retrieve Sub page from drobo char device.
        uses DroboIOctl class to run the raw ioctl.

        sub_page: selection code from DMP Spec...
        pack: the pattern of fields in the subpage...

       returns: a list unpacked according to the  structure 

       Each sub_page has a standard header:
           pack is prepended with a standard header '>BBH'
       Drobo is bigendian.
       first byte has some flags and a vendor code.
       second byte is the sub-page code.
       following two bytes have the length of the record (max: 65535)
    """
    if DEBUG & DBG_HWDialog:
       print 'getsubpage'

    if DEBUG & DBG_Simulation:
       return ()

    mypack = '>BBH' + pack
    paklen=struct.calcsize(mypack)

    modepageblock=struct.pack( ">BBBBBBBHB", 
         0x5a, 0, 0x3a, sub_page, 0, 0, 0, paklen, 0 )

    cmdout = self.fd.get_sub_page(paklen, modepageblock,0, DEBUG)

    if ( len(cmdout) == paklen ):
      result = struct.unpack(mypack, cmdout)
      if DEBUG & DBG_HWDialog :
          print 'the 4 byte header on the returned sense buffer: ', result[0:3]
          #print 'result is: ', result[3:]
      return result[3:]
    else:
      raise DroboException


  def __transactionNext(self):
    """ Increment the transaction member for some modeSelect pages.
    """
    if (self.transactionID > MAX_TRANSACTION):
       self.transactionID=0
    self.transactionID=self.transactionID+1


  def __issueCommand(self,command):
    """ issue a command to a Drobo...
     0x06 - blink.
     0x0d - Standby

     returns nothing, look at the drobo to see if it worked.
     note: command is asynchronous, returns before operation is complete.
    """

    if DEBUG & DBG_HWDialog:
        print 'issuecommand...'

    if DEBUG & DBG_Simulation:
        self.__transactionNext()
        return

    modepageblock=struct.pack( ">BBBBBBBHB", 
         0xea, 0x10, 0x00, command, 0x00, self.transactionID, 0x01 <<5, 0x01, 0x00 )

    try:
       cmdout = self.fd.get_sub_page(1, modepageblock,1,DEBUG)

    except:
       print 'IF you see, "bad address", it is because you need to be the super user...'
       print " try sudo or su ...       "
       sys.exit()

    self.__transactionNext()

    if ( len(cmdout) != 1 ):
       raise DroboException
    # only way to verify success is to look at the Drobo...

  def Sync(self,NewName=None):
    """  Set the Drobo's current time to the host's time,
	 and the name to selected value.

     STATUS: works, maybe...
        DRI claims Drobos are all in California time.  afaict, it ignores TZ completely.
        I feed it UTC, and when I read the time, normal routines convert to local time.
        so it looks perfect.  but diagnostics might not agree.
    """
    now=int(time.time())
    payload="LH32s"
    payloadlen=struct.calcsize(payload)
    if NewName==None:
    	NewName=self.GetSubPageSettings()[2]

    buffer=struct.pack( ">BBH" + payload , 0x7a, 0x05, payloadlen, now, 0 , NewName )
    sblen=len(buffer)

    # mode select CDB. 
    modepageblock=struct.pack( ">BBBBBBBHB", 0x55, 0x01, 0x7a, 0x05, 0, 0, 0, sblen, 0)
    self.fd.put_sub_page( modepageblock, buffer, DEBUG )


  def SetLunSize(self,tb):
    """
       SetLunSize - Sets the maximum LUN size to 'tb' terabytes

       status:  works with no issues!
    """
    if (DEBUG & DBG_Chatty):
       print 'set lunsize to %d TiB' % tb

    buffer=struct.pack( ">l", tb )
    sblen=len(buffer)

    # mode select CDB. 
    modepageblock=struct.pack( ">BBBBBBBHB", 
      0xea, 0x10, 0x0, 0x0f, 0, self.transactionID, (0x01 <<5)|0x01, sblen, 0x00 )

    self.fd.put_sub_page( modepageblock, buffer, DEBUG )
    self.__transactionNext()


  def Blink(self):
    """ asks the Drobo nicely to blink it's lights. aka. Identification 
        If you happen to have five in a row (drool), you can know which is which.

        STATUS: works, no issues.
    """
    self.__issueCommand(6)


  def Standby(self):
    """ asks the Drobo nicely to shutdown, flushing all manner of caches.

        STATUS: command itself works, no issues.... only light tests so far.
                still testing umount code.
    """
    toumount = self.DiscoverMounts()
    if len(toumount) > 0:
       for i in toumount:
           if DEBUG & DBG_Chatty:
              print "initiating umount command for: ", i
           umresult=os.system("umount " + i )
           if umresult != 0:
                return

    self.__issueCommand(0x0d)


  def GetDiagRecord(self,diagcode,decrypt=0):
    """ returns diagnostics as a string...
        diagcodes are either 4 or 7 for the two different Records available.

	STATUS: works fine.

        decryption reported to be XOR of 165, 0xa5... not added yet.
    """
    if DEBUG & DBG_Chatty:
      print "Dumping Diagnostics..."

    # tried 32000 ... it only returned 5K, so try something small.
    buflen=4096

    modepageblock=struct.pack( ">BBBBBBBHB", 
      0xea, 0x10, 0x80, diagcode, 0x00, self.transactionID, (0x01 <<5)|0x01, buflen, 0x00 )

    todev=0

    if DEBUG & DBG_General:
        print "Page 0..."

    cmdout = self.fd.get_sub_page( buflen, modepageblock, todev, DEBUG )
    diags=cmdout
    i=0
    while len(cmdout) == buflen:
        modepageblock=struct.pack( ">BBBBBBBHB", 
            0xea, 0x10, 0x80, diagcode, 0x00, self.transactionID, 0x01, buflen, 0x00 )

        cmdout = self.fd.get_sub_page( buflen, modepageblock, todev, DEBUG )
        i=i+1
	diags=diags+cmdout

        if DEBUG & DBG_General:
            print "diags ", i, ", cmdlen=", len(cmdout), " diagslen=", len(diags)
       
    return diags


  def dumpDiagnostics(self):

    n=time.gmtime()

    dfname="/tmp/DroboDiag_%d_%02d%02d_%02d%02d%02d.log" % ( n[0:6] )
    df=open(dfname, "w")
    d=self.GetDiagRecord(4)
    df.write(d)
    d=self.GetDiagRecord(7)
    self.__transactionNext()
    df.write(d)
    df.close()
    return dfname


  #
  # constants for use with firmware operations
  #

  fwsite="ftp://updates.drobo.com/"
  localfwrepository= os.path.expanduser("~") + "/.drobo-utils"

  def PickFirmware(self,name):
    """
       read in a given firmware from disk.

       sets self.fwdata

    """
    if (DEBUG & DBG_Chatty):
       print 'Reading Firmware from = %s' % name

    if ( name[-1] == 'z' ): # data is zipped...
       inqw=self.inquire()
       hwlevel=inqw[10] 
       z=zipfile.ZipFile(name,'r')
       for f in z.namelist():
           if (DEBUG & DBG_General):
              print f , ' ? '
              print 'firmware for hw rev ', f[-5] , ' this drobo is rev ', hwlevel[0]
	   if f[-5] == hwlevel[0]:
              self.fwdata = z.read(f) 
    else: # old file...
       f = open(name,'r')
       self.fwdata = f.read()
       f.close()

    good = self.validateFirmware()
    return good

  def inquire(self):
    """ 
     issue a standard SCSI INQUIRY command, return standard response as tuple.

     STATUS: works.

     trying to understand how to send an INQUIRY:
     SCSI version 2 protocol  INQUIRY...
     protocol : T10/1236-D Revision 20

     byte:  0 - descriptor code.                0x12 -- INQUIRY
            1 - 00 peripheral dev. type code    0x0, 4, 5, 7, e .. 
            2 - reserved
            3 - reserved.
            4-27   target descriptor parameters.
                 0 - target descriptor type code: 0x04 - Identification.

            28-31  dev. type params.

    """
    mypack = '>BBBBBBBB8s16s4s20sBB8HH'
    paklen=struct.calcsize(mypack)

    modepageblock=struct.pack( "BBBBBB", 0x12 , 0, 0, 0, paklen, 0 )

    cmdout = self.fd.get_sub_page(paklen, modepageblock,0, DEBUG)
    if ( len(cmdout) == paklen ):
      return struct.unpack(mypack, cmdout)
    else:
      raise DroboException


    
  def PickLatestFirmware(self):
    """
       fetch firmware from web site. ... should be a .tdf file.
       validate firmware from header...
 
       sets self.fwdata

       go to fwsite
       download index.txt
       figure out which one to download.
       return arch and version of firmware running, and the download file name.
       SCSI INQUIRY is supposed to respond with 'VERSION' 1.0 or 2.0 to tell which to use.
       tdz support: zip file containing two .tdf's.  one for rev1, another for rev2.

     status: works 


    """
    inqw=self.inquire()
    hwlevel=inqw[10] 
    fwi=self.GetSubPageFirmware()
    fwv= str(fwi[0]) + '.' + str(fwi[1]) + '.' + str(fwi[2])

    #FIXME ugly hack to force v1 to get onto the v2 firmware stream
    #  current dri index.txt file says v1's should run 1.1.2, but win/Mac dashboards upgrade
    #  to 1.2.4 anyways...  so I guess linux should too.
    #  if a v1 is running 1.1.2, then just claim to be an early v2 firmware, all should work.
    #if fwv == "1.200.11177": 
    #   fwv="1.201.12942"     

    fwarch = fwi[6].lower()

    if (DEBUG & DBG_Chatty):
      print 'looking for firmware for:', fwarch, fwv, 'hw version:', hwlevel
    listing_file=urllib2.urlopen( Drobo.fwsite + "index.txt")
    list_of_firmware_string=listing_file.read().strip("\t\r")
    list_of_firmware=list_of_firmware_string.split("|") 
    i=1
    p = re.compile('\[(.*)\]')
    while i < len(list_of_firmware):
      key=list_of_firmware[i-1].split()[1]
      value=list_of_firmware[i].split()[1]

      k=key.split('/')
      
      # profits oblige...
      if k[2] == "licensed" : 
        k = k[0:2] + k[3:]
        #print k
   
      # these If's are now nested for ease of debugging, insert a print to taste...
      # the algorithm is wrong wrt, other platforms...
      if k[2] == "firmware" :
        #print '    match firmware'
        if k[3] == fwarch :
          #print '    match k[3] = ', fwarch
          #if we are on a line that lists the fwversion in [] fixup k[4]
          m=p.search(list_of_firmware[i-1])
          if m :
              k[4]=m.group(1);
          if k[4] == fwv:
              if len(k) > 4: 
                if (DEBUG & DBG_Chatty):
                   print 'This Drobo should be running: ', value
                return (fwarch, fwv, hwlevel, value)
      i=i+2
    if (DEBUG & DBG_Chatty):
       print 'no matching firmware found, must be the latest and greatest!'
    return ( '','','','' )

  def downloadFirmware( self, fwname, localfw ):
    """
      download given fw file from network repository.
      load self.fwdata with the data from it

      STATUS: works.
    """
    if (DEBUG & DBG_Chatty):
      print 'downloading firmware ', fwname, '...'
    self.fwdata=None
    firmware_url=urllib2.urlopen( Drobo.fwsite + fwname )
    filedata = firmware_url.read()
    f = open(localfw,'w+')
    f.write(filedata)
    f.close()
    if (DEBUG & DBG_Chatty ) :
        print 'local copy written'

    if ( fwname[-1] == 'z' ): # data is zipped...
       self.PickFirmware(localfw)
    else: 
       self.fwdata=filedata

    if (DEBUG & DBG_Chatty ) :
       print 'downloading done '
    return self.fwdata

  def validateFirmware(self):
    """
       requires self.fwdata to be initialized before calling.
       read in the header of the firmware from self.fwdata.

       check the information in the header to confirm that it is a valid firmware image.

       status:
            works for length, and body CRC.  something wrong with header CRC.

       according to dpd.h:
       (hdrlength, hdrVersion, magic, imageVersion, targetName, sequenceNum, bootFailureCount, imageFlashAddress, imageLength, imageCrc32, about, hdrCrc32 ) = struct.unpack('llll16slllll256sl', self.fwdata[0:304])

       & 0xffffffffL is a kludge to work around CRC32 returning different values on 32 vs. 64 bit platforms.
       can remove once py3k arrives.  (see: http://bugs.python.org/issue1202)
       STATUS: working.

    """
    if (DEBUG & DBG_Chatty):
      print 'validateFirmware start...'
    self.fwhdr = struct.unpack('>ll4sl16slllll256sl', self.fwdata[0:312])

    if  len(self.fwdata) != ( self.fwhdr[0] + self.fwhdr[8] ) :
	print 'header corrupt... Length does not validate.'
	return 0

    if (DEBUG & DBG_Chatty):
      print 'header+body lengths validated.  Good.'
    #print self.fwhdr

    if  self.fwhdr[2] != 'TDIH' :
        print 'bad Magic, not a valid firmware'
        return 0

    if (DEBUG & DBG_Chatty):
      print 'Magic number validated. Good.'
      print '%d + %d = %d length validated. Good.' % ( self.fwhdr[0], self.fwhdr[8], len(self.fwdata) )

    # http://bugs.python.org/issue1202
    # doesn't work on 64 bit, only on 32bit... weird...
    blank = struct.pack('i',0)
    hdrcrc = zlib.crc32( self.fwdata[0:308] + blank + self.fwdata[312:self.fwhdr[0]] ) & 0xffffffffL
    r = self.fwhdr[11] & 0xffffffffL

    if (DEBUG & DBG_Chatty):
      print 'CRC from header: %d, calculated using python zlib crc32: %d ' % ( r, hdrcrc)
    if r != hdrcrc :
        print 'file corrupt, header checksum wrong'
        return 0
    bodycrc = zlib.crc32( self.fwdata[self.fwhdr[0]:] ) & 0xffffffffL
    q = self.fwhdr[9] & 0xffffffffL
 
    if (DEBUG & DBG_Chatty):
      print 'CRC for body from header: %d, calculated: %d ' % ( q, bodycrc)
    if q != bodycrc :
        print 'file corrupt, payload checksum wrong'
        return 0
    
    if (DEBUG & DBG_Chatty):
      print '32 bit Cyclic Redundancy Check correct. Good.'
      print 'validateFirmware successful...'

    return 1 
    

  def updateFirmwareRepository(self):
    """
      put the best firmware in self.fwdata.
            return 1 if successful, 0 if not.

      determine currently running firmware and most current from web site.

      check if the most current one has already been downloaded.
      if not, then download it into a local repository.

      Compare the current running firmware against the appropriate file 
      in the local repository

      STATUS: working...

    """
    (fwarch, fwversion, hwlevel, fwpath ) = self.PickLatestFirmware()
    if fwarch == '' : # already at latest version...
        return 0

    if not os.path.exists(Drobo.localfwrepository) :
         os.mkdir(Drobo.localfwrepository)

    fwname = fwpath.split('/')
    localfw = Drobo.localfwrepository + '/' + fwarch + '_' + hwlevel + '_' + fwname[-1] 
    if (DEBUG & DBG_Chatty):
       print 'looking for: %s' % localfw
    if not os.path.exists(localfw):
       if (DEBUG & DBG_Chatty):
          print 'not present, fetching from drobo.com'
       self.fwdata = self.downloadFirmware(fwpath,localfw)
       good = self.validateFirmware()
       if not good:
          print 'downloaded firmware did not validate.' 
          return 0
    else:
       if (DEBUG & DBG_Chatty):
          print 'local copy already present:', localfw
       good = self.PickFirmware(localfw)

    if good:
      if (DEBUG & DBG_Chatty):
         print 'correct fw available'
      return 1
 
    print 'no valid firmware found'
    return 0
   

  def writeFirmware(self,function):
    """
        given good firmware data, upload it to the Drobo...

	1_README_*.txt from the resource kit is followed here.

        function -- a callback that accepts a single argument, an integer in the range 0-100.
           indicates % done.  the function is called after each write in the loop.

        STATUS: works.

    """ 

    totallength = len(self.fwdata)
    buffer = struct.pack( ">L" , totallength ) + self.fwdata[0:self.fwhdr[0]]

    modepageblock=struct.pack( ">BBBBBBBHB", 
      0xea, 0x10, 0x00, 0x70, 0x00, self.transactionID, (0x01<<5)|0x01, len(buffer), 0x00 )
    
    written = self.fd.put_sub_page( modepageblock, buffer, DEBUG )

    if DEBUG & DBG_General:
      print "Page 0..."

    buflen=32768
    written=buflen
    i=self.fwhdr[0]
    j=i+buflen 
    moretocome=0x01

    if (DEBUG & DBG_General ) :
      print 'writeFirmware: i=%d, start=%d, last=%d fw length= %d\n' % \
         ( i, self.fwhdr[0], totallength, len(buffer) )

    while (written == buflen) and ( i < len(self.fwdata)) :

        if ( i + buflen ) > totallength :  # writing the last record.
        	buflen= totallength - i
                moretocome=0

        modepageblock=struct.pack( ">BBBBBBBHB", 
            0xea, 0x10, 0x00, 0x70, 0x00, self.transactionID, moretocome, 
            buflen, 0x00 )

        j=i+buflen
        written = self.fd.put_sub_page( modepageblock, self.fwdata[i:j], DEBUG )
        i=j

        function(i*100/totallength)

        if (DEBUG & DBG_General ) :
            print 'wrote ',written, ' bytes.  Cumulative: ',  i, ' of', totallength

    if (DEBUG & DBG_General ) :
       print 'writeFirmware Done.  i=%d, len=%d' % ( i, totallength )

    self.__transactionNext()
    
    paklen=1 
    modepageblock=struct.pack( ">BBBBBBBHB",
         0xea, 0x10, 0x80, 0x71, 0, self.transactionID, 0x01 << 5 , paklen, 0 )

    cmdout = self.fd.get_sub_page(paklen, modepageblock,0, DEBUG)
    status = struct.unpack( '>B', cmdout )

    if DEBUG & DBG_General : 
      print 'Drobo thinks write status is: ', status[0]

        


  def GetCharDev(self):
     return self.char_dev_file

  def GetSubPageConfig(self):
     """ returns: ( MaxNumberOfSlots, MaxNumLUNS, MaxLunSize )
     """ 
     # SlotCount, Reserved, MaxLuns, MaxLunSz, Reserved, unused, unused 

     if DEBUG & DBG_Simulation:
	return (4, 16, 2199023250944)

     result=self.__getsubpage( 0x01, 'BBBQBHH'  )
     return ( result[0], result[2], result[3]*512 )

  def GetSubPageCapacity(self):
     """ returns: ( Free, Used, Virtual, Unprotected ) 
     """
     if DEBUG & DBG_Simulation:
        capacity = 495452160000
        used = random.randint(0,capacity)
	return (capacity-used, used, capacity, 125184245760)

     return self.__getsubpage(0x02, 'QQQQ' )

  def GetSubPageSlotInfo(self):
     """  returns list of slot info, each slot is:
       ( slotId, PhysicalCapacity, ManagedCapacity, leds, Manufacturer, Model ) ... )
       
       leds - indicates what the lights on the front panel are doing.
              returns one colour if one colour is constant, set of
              colours if there is flashing going on.
     """
     if DEBUG & DBG_Simulation:
       return ( (0, 500107862016, 0, 'green', 'ST3500830AS', 'ST3500830AS'), (1, 750156374016, 0, 'green', 'WDC WD7500AAKS-00RBA0', 'WDC WD7500AAKS-0'), (2, 0, 0, _ledstatus(random.randint(0,6)), '', ''), (3, 0, 0, 'gray', '', ''))

     slotrec='HBQQB32s16sL'
     r = self.__getsubpage( 0x03, 'B' + slotrec+slotrec+slotrec+slotrec )

     l=[]
     j=0
     while (j < r[0] ):
       i=j*8
       s = ( r[i+2], r[i+3], r[i+4], _ledstatus( r[i+5] ), r[i+6].strip(" \0"),
		r[i+7].strip(" \0") )
       l.append( s ) 
       j=j+1

     return l


  def GetSubPageLUNs(self):
     """
         returns  for each LUN  returns detailed info:
             ( LUNID, LUN total Capacity, LUN Used Capacity, PartitionScheme*, Partition Count*, Format* )

         *only returned if firmware: SUPPORTS_NEW_LUNINFO2 (essentially >=1.1.0)

      N.B. must run getSubPageFirmware before the first time you
         calling this routine, or it will fail by returning the empty set.


      STATUS: works, with ERRATA:

         report from matthew mastracci that this doesn't work for him... should be +6,
         and the value for ext3 should be 0.0x8, and not 0x80...
         haven't understood it yet...

      question: is it correct to mix 'used capacity' from luninfo, with 
      total capacity from luninfo2?

      for old luninfo, the spec and dmp.h agree... 
      spec says:   
      dmp.h says:  len ( 8* H-len, B-id, Q-cap, Q-used ) 

         returns  for each LUN  returns detailed info:
             ( LUNID, LUN total Capacity, PartitionScheme, PartitionCount, Format )

      for Luninfo2.. works, but 'PartCount' is odd.

      my guess after much experiments: PartitionCount and format are
      inverted vs. dmp.h. the count is last(6th), and the format is 5th..

      even that doesn't work right, because I get partcount=1 when there
      are none, and it stays 1 when I add one.  now there are 8 when there is
      only one... unless 8 is ext2 fs. and I guessed wrong about part types...

      See also ERRATA for _partscheme

      dmp.h says
      8 x H-length, B-LunID, Q-TotalCapacity, B-PartScheme, B-PartCount, B-Format, 5B-rsvd 
     
     """
     if DEBUG & DBG_Simulation:
       return [(0, 2199023251456, 5092651008, 'GPT', ['EXT3'])]

     lp="HBQQ"
     l = self.__getsubpage( 0x04, 'B'+lp+lp+lp+lp+lp+lp+lp+lp )

     if ( 'SUPPORTS_NEW_LUNINFO2' in self.features ):
        li2="HBQBBB5B"
        l2= self.__getsubpage( 0x07, "B"+ li2+li2+li2+li2+li2+li2+li2+li2 )

     i=0
     li=[]
     while ( i < l[0] ):
        j=i*4
        if ( 'SUPPORTS_NEW_LUNINFO2' in self.features ):
           k=i*7
           li.append( (l[j+2], l2[k+3], l[j+4], _partscheme(l2[k+4]), _partformat(l2[k+5]) ) )
        else:
           li.append( (l[j+2], l[j+3], l[j+4]) )
        i=i+1

     return li


  def GetSubPageSettings(self):
     """
        returns: ( currentUTCtime, UTCoffset, DroboName )

        STATUS: works with... 
        ERRATA:
		-- dpd.h and other sources say offset is two bytes.
                -- DMP Spec says it is only one byte.
		-- other sources say it is always set to 'California Time'... 8.
		-- California time is UTC - 8... +8 would be China.
		-- structures returned are supposed to be in network byte order (MSB)
                   when two byte value read in network byte order, result is 2048.
                   they stuff it in LSB order, so the 8 ended up in the higher order byte.
		-- so I just claim it says 8 and shut up.

     """
     if DEBUG & DBG_Simulation:
        return (1220112079, 8, 'TRUSTED DATA')

     ( utc, offset, name ) = self.__getsubpage(0x05, 'LH32s' )
     name=name.strip(" \0")
     offset=8 # offset is screwed up returned by Drobo, just set it to what they claim it should be.
     return ( utc, offset, name )

  def GetSubPageProtocol(self):
     """ 
        returns ( Major, Minor )

        STATUS: working... 
            soupcon: at firmware 1.0.3, seemed to demand an additional byte.
              might be a confused artifact of dev.
            at 1.1.1 the additional byte leads to resid > 0 in the C call, 
            so matches docs. 
     """
     if DEBUG & DBG_Simulation:
         return (0, 10)

     return self.__getsubpage( 0x06, 'BB' )

  def GetSubPageFirmware(self):
     """

        STATUS:  working with ERRATA:

        returns ( majorVer, MinorVer, Build, UpgMajorVer, UpgMinorVer, 
		BuildDate, Arch, )
        above is what the spec says...

	dpd.h says byte 128 has a feature
	    agrees on the first four, but says the date is a 32 char string, and
            is followed by Arch[16], and Extra[256],  

            Drobo has a version string after arch, guessed at 16 chars.
            I shortened Extra for that.
	    byte 0x80 is supposed to be feature flags, found it a 0x73...
     """
     if DEBUG & DBG_Simulation:
        return (1, 201, 12942, 12, 6, 'May 13 2008,15:29:32', 'ArmMarvell', '1.1.2', ['NO_AUTO_REBOOT', 'NO_FAT32_FORMAT', 'USED_CAPACITY_FROM_HOST', 'DISKPACKSTATUS', 'ENCRYPT_NOHEADER', 'CMD_STATUS_QUERIABLE', 'VARIABLE_LUN_SIZE_1_16', 'PARTITION_LUN_GPT_MBR', 'FAT32_FORMAT_VOLNAME', 'SUPPORTS_DROBOSHARE', 'SUPPORTS_NEW_LUNINFO2'])

     raw=self.__getsubpage(0x08, 'BBHBB32s16s16s240s' )
     result = struct.unpack('>112sL32sH90s', raw[8])
     self.features = _unitfeatures(result[1])
     return (raw[0], raw[1], raw[2], raw[3], raw[4], raw[5].strip(" \0"), 
         raw[6].strip(" \0"), raw[7].strip(" \0"), self.features )

  def GetSubPageStatus(self):
     """
     return _unitstatus

     STATUS: works a bit, 
        relayoutcount stuff completely untested...
      Errata: 
      spec says a single byte.
      dmp.h says two longs:  (Status, RelayOutCount)
      Drobo always returns 0 for second Long.
      when I remove a disk, I get [ 'No Redundancy', 'Relay out in progress'],
      but when I format, it stays empty...
     """
     if DEBUG & DBG_Simulation:
         return _unitstatus(random.randint(0,16535))       

     ss=self.__getsubpage(0x09, 'LL' )
     s=_unitstatus(ss[0])

     if ss[1] > 0 : # relay out in progress
        if self.relaystart == 0:
           self.relaystart=time.time()
           self.relayinitialcount=ss[1]
           s.append( 'no estimate yet ' )
        else: 
           now=time.time()
           runningtime=(now - self.relaystart)/60.0
           amtdone= self.relayinitialcount - ss[1]
           amtleft= ss[1]
           pctleft= 100.0 * amtleft / self.relayinitialcount 
           pctdone= 100 - pctleft
           
           if amtdone == 0:
              s.append( 'gathering stats, no estimate yet ' )
           else:
              rate=  pctdone / runningtime 
              timeleft = pctleft*rate  # timeleft in minutes...
              s.append( '%d blocks left ' % ss[1] )
     else:
        if self.relaystart > 0:
           self.relaystart == 0

     return ( s, ss[1] )

  def GetSubPageOptions(self): 
     """
        return( YellowAlertThresh, RedAlertThresh, AutoDelSnapshot )
  
        STATUS: untested, ERRATA too hard to reconcile...

        spec says:
           B-YelThresh, B-RedThresh, 5B-Rsvd, 1bit-AutoDel, B-Rsvd
        dmp.h says:
           B-YelThresh, B-RedThresh, B-Flags, H-DataCheckParam, B-YelLow, B-RedLow

        AutodelSnapshot is right shifted 7 bits, 
        other cases where there bit shfts are claimed have ended unhappily... 
        hmm...
     """
     if DEBUG & DBG_Simulation:
        return (1, 0, 0)

     try: # insert try/except for compatibility with firmware <= 1.1.0  
         o = self.__getsubpage(0x07, 'BB5BBB' )
         return ( o[0], o[1], o[4] >>7 )
     except:
         return ( 0,0,0 )

  def DiscoverMounts(self):
    """
        return the list of mounted file systems using the unit.
    """
    mounts=open("/etc/mtab")
    dlen=len(self.char_dev_file)
    filesystems=[]
    for l in mounts.readlines():
       fields=l.split()
       for i in self.char_devs:
          if fields[0][0:dlen] == i:
             filesystems.append(fields[1])
    mounts.close()
    return filesystems

def DiscoverLUNs(debugflags=0):
    """ find all Drobo LUNs accessible to this user on this system. 
	returns a list of list of character device files 
              samples: [ [ "/dev/sdf", "/dev/sdg" ], [ "/dev/sdh" ] ] 
    """
    global DEBUG
    DEBUG=debugflags

    if DEBUG & DBG_Simulation:
       return [ [ "/dev/sdb", "/dev/sdc" ], [ "/dev/sdd" ] ]

    devices=[]

    for potential in DroboIOctl.drobolunlist(DEBUG):
       if ( DEBUG & DBG_Detection ):
             print "trying: ", potential

       try: 
          d = Drobo( potential,debugflags=debugflags )
	  devices.append(potential)
       except:
 	      pass
              
    return devices
