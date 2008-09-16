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

#
# FIXME: if installed with "python setup.py install" then this 
# insert is not needed.  This is to be able to test it before 
# installation. best to remove this once installed.
#  this might be considered a security issue as it is...
#
# on kubuntu hardy:
#sys.path.insert(1, os.path.normpath('build/lib.linux-i686-2.5') )
#on Debian Lenny, it's the same except 2.4... 
#on a Droboshare... who knows?
m = re.compile("lib.*")

for l in os.listdir("build"):
    if m.match(l) :
        sys.path.insert(1, os.path.normpath("build/" + l ))


import DroboDMP

class DroboException(exceptions.Exception):
  """  If there is a problem accessing the Drobo, this exception is raised.
  """
  def __init__(self):
     return

  def __str__(self):
     print " problem accessing a Drobo"


def hexstr(hexstring): 
    """ convert an array into a string representing hex...  """

    i=0
    for c in hexstring:
       if ( i % 8 ) == 0:
          print "\n%02x -" % i,
       print "%02x" % ord(c),
       i=i+1
    print

def ledstatus(n):
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
    #print 'colourstats, argument n is: ', n
    colourstats=[ 'black', 'red', 'yellow', 'green', ['red', 'green'], 
      [ 'red', 'yellow' ], ['red', 'black'] ] 
    if ( n == 0x80 ):  # empty
       return 'gray'
    return colourstats[n & 0x0f ]


def unitstatus(n):
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

def partformat(n):
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
    if ( n & 0x80 ):
       f.append( 'EXT3' )
    if ( n & 0xFF ) == 0:
       f.append( 'FAT32' )

    if (len(f) != 1):
      raise DroboException

    return f[0]


def partscheme(n):
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
   
def unitfeatures(n):
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


  def __init__(self,chardev):
     """ chardev is /dev/sdX... 
         the character device associated with the drobo unit
     """   
     self.char_dev_file = chardev  
     self.features = []    
     self.transactionID=1


  def format(self,pscheme,fstype,maxlunsz,devsz):
     """ return a shell script giving the code to commands required to 
     
     pscheme is one of: mbr, apt, gpt,  
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
     print "Not Implemented Yet"
     raise DroboException

     

  def __getsubpage(self,sub_page,pack): 
    """ Retrieve Sub page from drobo char device.
        uses a DroboDMP extension in C to run the raw ioctl.

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
    mypack = '>BBH' + pack
    paklen=struct.calcsize(mypack)

    modepageblock=struct.pack( ">BBBBBBBHB", 
         0x5a, 0, 0x3a, sub_page, 0, 0, 0, paklen, 0 )

    cmdout = DroboDMP.get_sub_page(str(self.char_dev_file), paklen, 
       modepageblock,0)

    if ( len(cmdout) == paklen ):
      result = struct.unpack(mypack, cmdout)
      #print 'result is: ', result[3:]
      return result[3:]
    else:
      raise DroboException

  def __transactionNext(self):
    if (self.transactionID > 200):
       self.transactionID=0
    self.transactionID=self.transactionID+1


  def __issueCommand(self,command):
    """ issue a command to a Drobo...
     0x06 - blink.
     0x0d - Standby

     returns nothing, look at the drobo to see if it worked.
     note: command is asynchronous, returns before operation is complete.
    """

    modepageblock=struct.pack( ">BBBBBBBHB", 
         0xea, 0x10, 0x00, command, 0x00, self.transactionID, 0x01 <<5, 0x01, 0x00 )

    try:
       cmdout = DroboDMP.get_sub_page(str(self.char_dev_file), 1, modepageblock,1)

    except:
       print 'IF you see, "bad address", it is because you need to be the super user...'
       print " try sudo or su ...       "
       sys.exit()

    self.__transactionNext()

    if ( len(cmdout) != 1 ):
       raise DroboException
    # only way to verify success is to look at the Drobo...

  def Sync(self):
    """  Set the time to the host's time

     ( utc, offset, name ) = self.__getsubpage(0x05, 'LB32s' )

     STATUS: not tested yet.
    """
    pass
    dateblock=struct.pack(">LH32s", 0,0,"Hi There!" )
    buflen(dateblock)
    modepageblock=struct.pack( ">BBBBBBBHB", 
      0xea, 0x10, 0x80, 0x05, 0x00, self.transactionID, 
      (0x01 <<5)|0x01, buflen, 0x00 )

    todev=0
    cmdout = DroboDMP.get_sub_page( str(self.char_dev_file), 
                buflen, modepageblock, todev )
    diags=cmdout
    i=0

  def Blink(self):
    """ asks the Drobo nicely to blink it's lights. aka. Identification 
        If you happen to have five in a row (drool), you can know which is which.

        STATUS: works no issues.
    """
    self.__issueCommand(6)


  def Standby(self):
    """ asks the Drobo nicely to shutdown, flushing all manner of caches.

        STATUS: command itself works, no issues.... only light tests so far.
                still testing umount code.
    """
    mounts=open("/etc/mtab")
    dlen=len(self.char_dev_file)
    toumount=[]
    for l in mounts.readlines():
       fields=l.split()
       if fields[0][0:dlen] == self.char_dev_file:
          toumount.append(fields[1])

    if len(toumount) > 0:
       for i in toumount:
           umresult=os.system("umount " + i )
           if umresult != 0:
                return

    self.__issueCommand(0x0d)


  def __GetDiagRecord(self,diagcode):
    """ returns diagnostics as a string...
	STATUS: totally borked!  loops forever!  
         don't know how to read the count of bytes actually provided by Drobo.
    """
    print "Dumping Diagnostics..."
    # tried 32000 ... it only returned 5K, so try something small.
    buflen=4096

    modepageblock=struct.pack( ">BBBBBBBHB", 
      0xea, 0x10, 0x80, diagcode, 0x00, self.transactionID, 
      (0x01 <<5)|0x01, buflen, 0x00 )

    todev=0
    print "Page 0..."
    cmdout = DroboDMP.get_sub_page( str(self.char_dev_file), 
                buflen, modepageblock, todev )
    diags=cmdout
    i=0
    while len(cmdout) == buflen:
        modepageblock=struct.pack( ">BBBBBBBHB", 
            0xea, 0x10, 0x80, diagcode, 0x00, self.transactionID, 0x01, 
            buflen, 0x00 )

        cmdout = DroboDMP.get_sub_page( str(self.char_dev_file), 
                   buflen, modepageblock, todev )
        i=i+1
	diags=diags+cmdout
        print "diags ", i, ", cmdlen=", len(cmdout), " diagslen=", len(diags)
       
    
    return diags

  def dumpDiagnostics(self):

    n=time.gmtime()

    df=open("/tmp/DroboDiag_%d_%02d%02d_%02d%02d%02d.log" % ( n[0:6] ), "w")
    d=self.__GetDiagRecord(4)
    df.write(d)
    d=self.__GetDiagRecord(7)
    self.__transactionNext()
    df.write(d)
    df.close()


  def GetCharDev(self):
     return self.char_dev_file

  def GetSubPageConfig(self):
     """ returns: ( MaxNumberOfSlots, MaxNumLUNS, MaxLunSize )
     """ 
     # SlotCount, Reserved, MaxLuns, MaxLunSz, Reserved, unused, unused 
     result=self.__getsubpage( 0x01, 'BBBQBHH'  )
     return ( result[0], result[2], result[3]*512 )

  def GetSubPageCapacity(self):
     """ returns: ( Free, Used, Virtual, Unprotected ) 
     """
     return self.__getsubpage(0x02, 'QQQQ' )

  def GetSubPageSlotInfo(self):
     """  returns list of slot info, each slot is:
       ( slotId, PhysicalCapacity, ManagedCapacity, leds, Manufacturer, Model ) ... )
       
       leds - indicates what the lights on the front panel are doing.
              returns one colour if one colour is constant, set of
              colours if there is flashing going on.
     """
     slotrec='HBQQB32s16sL'
     r = self.__getsubpage( 0x03, 'B' + slotrec+slotrec+slotrec+slotrec )

     l=[]
     j=0
     while (j < r[0] ):
       i=j*8
       s = ( r[i+2], r[i+3], r[i+4], ledstatus( r[i+5] ), r[i+6].strip(" \0"),
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

      See also ERRATA for partscheme

      dmp.h says
      8 x H-length, B-LunID, Q-TotalCapacity, B-PartScheme, B-PartCount, B-Format, 5B-rsvd 
     
     """
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
           li.append( (l[j+2], l2[k+3], l[j+4], 
                  partscheme(l2[k+4]), partformat(l2[k+5]), l2[k+6] ) )
        else:
           li.append( (l[j+2], l[j+3], l[j+4]) )
        i=i+1

     return li


  def GetSubPageSettings(self):
     """
        returns: ( currentUTCtime, UTCoffset, DroboName )

        STATUS: works, no issues.
     """
     ( utc, offset, name ) = self.__getsubpage(0x05, 'LB32s' )
     name=name.strip(" \0")
     return ( utc, offset, name )

  def GetSubPageProtocol(self):
     """ 
        returns ( Major, Minor )

        STATUS: working... 
            soupcon: at firmware 1.0.3, seemed to demand and additional byte.
              might be a confused artifact of dev.
            at 1.1.1 the additional byte leads to resid > 0 in the C call, 
            so matches docs. 
     """
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
     raw=self.__getsubpage(0x08, 'BBHBB32s16s16s240s' )
     result = struct.unpack('>112sL32sH90s', raw[8])
     self.features = unitfeatures(result[1])
     return (raw[0], raw[1], raw[2], raw[3], raw[4], raw[5].strip(" \0"), 
         raw[6].strip(" \0"), raw[7].strip(" \0"), self.features )

  def GetSubPageStatus(self):
     """
     return unitstatus

     STATUS: works a bit, Errata
      spec says a single byte.
      dmp.h says two longs:  (Status, RelayOutCount)
      Drobo always returns 0 for second Long.
      when I remove a disk, I get [ 'No Redundancy', 'Relay out in progress'],
      but when I format, it stays empty...
     """

     ss=self.__getsubpage(0x09, 'LL' )
     s=unitstatus(ss[0])
     return s

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
     o = self.__getsubpage(0x07, 'BB5BBB' )
     return ( o[0], o[1], o[4] >>7 )



def DiscoverLUNs():
    """ find all Drobo LUNs accessible to this user on this system. 
	returns a list of character device files 
              samples: ( "/dev/sdc", "/dev/sdd" )
    """

    devdir="/dev"
    devices=[]
    for potential in os.listdir(devdir):
       if ( potential[0:2] == "sd" and len(potential) == 3 ):
	  dev_file= devdir + '/' + potential
          d = Drobo( dev_file )
          try: 
              fw=d.GetSubPageFirmware()
              if ( len(fw) >= 8 ) and (len(fw[7]) >= 5):
	          devices.append(dev_file)
          except:
 	      pass
       else:
	  pass
    return devices