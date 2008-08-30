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

#only for fw download...
import os.path
import urllib2
import zipfile,zlib

DEBUG = 0
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

#m = re.compile("lib.*")
#for l in os.listdir("build"):
#    if m.match(l) :
#        sys.path.insert(1, os.path.normpath("build/" + l ))


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
    colourstats=[ 'black', 'red', 'yellow', 'green', ['red', 'green'], 
      [ 'red', 'yellow' ], ['red', 'black'] ] 
    if DEBUG > 0:
         print 'colourstats, argument n is: ', n
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
    if ( n & 0x80 ): # on Peter's...
       f.append( 'EXT3' )
    #if ( n & 0x08 ): # on Matthew Mastracci's
    #   f.append( 'EXT3' )
    if ( n & 0xFF ) == 0:
       f.append( 'FAT32' )

    if (len(f) != 1):
      print 'hoho! multiple partition types! Brave are we not?' 

    return f


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
     self.fd=0
     
     self.fd=DroboDMP.openfd(chardev,0,DEBUG)

     self.features = []    
     self.transactionID=1
     self.relaystart=0
 
  def __del__(self):
     if DEBUG >0:
        print '__del__ '

     if (self.fd >0):
           DroboDMP.closefd()

  def format(self,pscheme='gpt',fstype='ext3'):
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

     print ' parted %s mklabel gpt ' % self.char_dev_file
     print ' parted %s mkpart ext2 0 100% ' % self.char_dev_file
     print ' parted %s print ' % self.char_dev_file

     if fstype == 'ext3': 
         print ' mke2fs -j -i 262144 -L Drobo01 -m 0 -O sparse_super,^resize_inode %s1 ' % self.char_dev_file
     elif fstype == 'ntfs':
         print 'mkntfs -f -L Drobo01  %s1' % self.char_dev_file
     elif fstype == 'FAT32':
         print 'mkdosfs -F 32 -S 4096 -n Drobo01 %s1' % self.char_dev_file
     else:
         print 'unsupported  partition type %s, sorry...' % fstype

 

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
    if DEBUG >0:
       print 'getsubpage'

    mypack = '>BBH' + pack
    paklen=struct.calcsize(mypack)

    modepageblock=struct.pack( ">BBBBBBBHB", 
         0x5a, 0, 0x3a, sub_page, 0, 0, 0, paklen, 0 )

    cmdout = DroboDMP.get_sub_page(paklen, modepageblock,0, DEBUG)

    if ( len(cmdout) == paklen ):
      result = struct.unpack(mypack, cmdout)
      if DEBUG >0:
          print 'the 4 byte header on the returned sense buffer: ', result[0:3]
          #print 'result is: ', result[3:]
      return result[3:]
    else:
      raise DroboException


  def __transactionNext(self):
    """ Increment the transaction member for some modeSelect pages.
    """
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

    if DEBUG >0:
        print 'issuecommand...'

    modepageblock=struct.pack( ">BBBBBBBHB", 
         0xea, 0x10, 0x00, command, 0x00, self.transactionID, 0x01 <<5, 0x01, 0x00 )

    try:
       cmdout = DroboDMP.get_sub_page(1, modepageblock,1,DEBUG)

    except:
       print 'IF you see, "bad address", it is because you need to be the super user...'
       print " try sudo or su ...       "
       sys.exit()

    self.__transactionNext()

    if ( len(cmdout) != 1 ):
       raise DroboException
    # only way to verify success is to look at the Drobo...

  def Sync(self):
    """  Set the Drobo's current time to the host's time.

     STATUS: works, maybe...
        DRI claims Drobos are all in California time.  afaict, it ignores TZ completely.
        I feed it UTC, and when I read the time, normal routines convert to local time.
        so it looks perfect.  but diagnostics might not agree.
    """
    now=int(time.time())
    payload="LH32s"
    payloadlen=struct.calcsize(payload)
    buffer=struct.pack( ">BBH" + payload , 0x7a, 0x05, payloadlen, now, 0 ,"Hi There" )
    sblen=len(buffer)

    # mode select CDB. 
    modepageblock=struct.pack( ">BBBBBBBHB", 0x55, 0x01, 0x7a, 0x05, 0, 0, 0, sblen, 0)
    DroboDMP.put_sub_page( modepageblock, buffer, DEBUG )


  def SetLunSize(self,tb):
    """
       SetLunSize - Sets the maximum LUN size to 'tb' terabytes

       status:  Broken!  always sets LUNSIZE to 16TB
    """
    print 'set lunsize to %d TiB' % tb
    buffer=struct.pack( ">L", tb )
    sblen=len(buffer)

    # mode select CDB. 
    modepageblock=struct.pack( ">BBBBBBBHB", 
      0xea, 0x10, 0x80, 0x0f, 0, self.transactionID, (0x01 <<5)|0x01, sblen, 0x00 )

    DroboDMP.put_sub_page( modepageblock, buffer, DEBUG )
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


  def GetDiagRecord(self,diagcode,decrypt=0):
    """ returns diagnostics as a string...
        diagcodes are either 4 or 7 for the two different Records available.

	STATUS: works fine.

        decryption reported to be XOR of 165, 0xa5... not added yet.
    """
    if DEBUG > 0:
      print "Dumping Diagnostics..."

    # tried 32000 ... it only returned 5K, so try something small.
    buflen=4096

    modepageblock=struct.pack( ">BBBBBBBHB", 
      0xea, 0x10, 0x80, diagcode, 0x00, self.transactionID, (0x01 <<5)|0x01, buflen, 0x00 )

    todev=0

    if DEBUG > 0:
        print "Page 0..."

    cmdout = DroboDMP.get_sub_page( buflen, modepageblock, todev, DEBUG )
    diags=cmdout
    i=0
    while len(cmdout) == buflen:
        modepageblock=struct.pack( ">BBBBBBBHB", 
            0xea, 0x10, 0x80, diagcode, 0x00, self.transactionID, 0x01, buflen, 0x00 )

        cmdout = DroboDMP.get_sub_page( buflen, modepageblock, todev, DEBUG )
        i=i+1
	diags=diags+cmdout

        if DEBUG > 0:
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
    print 'name = %s, %s' % ( name, name[-1] )
    if ( name[-1] == 'z' ): # data is zipped...
       inqw=self.inquire()
       hwlevel=inqw[10] 
       z=zipfile.ZipFile(name,'r')
       for f in z.namelist():
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

    cmdout = DroboDMP.get_sub_page(paklen, modepageblock,0, DEBUG)
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

     status: supports version 1 drobo tdf files.
             does not support .tdz files (yet.)

       tdz support.  zip file containing two .tdf's.  one for rev1, another for rev2.
       SCSI INQUIRY is supposed to respond with 'VERSION' 1.0 or 2.0 to tell which to use.

    """
    inqw=self.inquire()
    hwlevel=inqw[10] 
    fwi=self.GetSubPageFirmware()
    fwv= str(fwi[0]) + '.' + str(fwi[1]) + '.' + str(fwi[2])
    fwarch = fwi[6].lower()

    print 'looking for firmware for:', fwarch, fwv, 'hw version:', hwlevel
    listing_file=urllib2.urlopen( Drobo.fwsite + "index.txt")
    list_of_firmware_string=listing_file.read().strip("\t\r")
    list_of_firmware=list_of_firmware_string.split("|") 
    i=1
    while i < len(list_of_firmware):
      key=list_of_firmware[i-1].split()[1]
      value=list_of_firmware[i].split()[1]
      #print key,value

      k=key.split('/')
      if k[1][-1] == hwlevel[0] and k[2] == "firmware" and len(k) > 4: 
        if k[3] == fwarch and k[4] == fwv:
           print 'This Drobo should be running: ', value
           return (fwarch, fwv, hwlevel, value)
      i=i+2
 
    print 'no matching firmware found, must be the latest and greatest!'
    return ( '','','','' )

  def downloadFirmware( self, fwname ):
    """
      download given fw file from network repository.

      STATUS: works.
    """
    print 'downloading firmware ', fwname, '...'
    self.fwdata=None
    firmware_url=urllib2.urlopen( Drobo.fwsite + fwname )
    if ( fwname[-1] == 'z' ): # data is zipped...
       filedata= firmware_url.read()
       localfw = localfwrepository + fwname
       f = open(localfw,'w+')
       f.write(self.fwdata)
       f.close()
       self.fwdata=None
       print 'local copy written'
       self.PickFirmware(localfw)
    else: # old file...
       fwdata = firmware_url.read()
    print 'downloading done '
    return fwdata

  def validateFirmware(self):
    """
       requires self.fwdata to be initialized before calling.
       read in the header of the firmware from self.fwdata.

       check the information in the header to confirm that it is a valid firmware image.

       status:
            works for length, and body CRC.  something wrong with header CRC.

       according to dpd.h:
       (hdrlength, hdrVersion, magic, imageVersion, targetName, sequenceNum, bootFailureCount, imageFlashAddress, imageLength, imageCrc32, about, hdrCrc32 ) = struct.unpack('LLLL16sLLLLL256sL', self.fwdata[0:304])

       STATUS: working, except do not understand header CRC's yet so ignoring those for now.

    """
    print 'validateFirmware start...'
    self.fwhdr = struct.unpack('>LL4sL16sLLLLL256sL', self.fwdata[0:312])

    if  len(self.fwdata) != ( self.fwhdr[0] + self.fwhdr[8] ) :
	print 'header corrupt... Length does not validate.'
	return 0

    print 'header+body lengths validated.  Good.'
    #print self.fwhdr

    if  self.fwhdr[2] != 'TDIH' :
        print 'bad Magic, not a valid firmware'
        return 0

    print 'Magic number validated. Good.'
    print '%d + %d = %d length validated. Good.' % ( self.fwhdr[0], self.fwhdr[8], len(self.fwdata) )

    hdrcrc = zlib.crc32( self.fwdata[0:308] + self.fwdata[312:self.fwhdr[0]] )
    print 'CRC from header: %d, calculated using python zlib crc32: %d ' % ( self.fwhdr[11], hdrcrc)
    print 'yeah, the header CRCs do not match. For now they never do ... ignoring it.'
    bodycrc = zlib.crc32( self.fwdata[self.fwhdr[0]:] )
    print 'CRC for body from header: %d, calculated: %d ' % ( self.fwhdr[9], bodycrc)
    if self.fwhdr[9] != bodycrc :
        print 'file corrupt, payload checksum wrong'
        return 0
    
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
    if not os.path.exists(localfw):
       self.fwdata = self.downloadFirmware(fwpath)
       good = self.validateFirmware()
       if good:
          f = open(localfw,'w+')
          f.write(self.fwdata)
          f.close()
          print 'local copy written'
       else:
          print 'downloaded firmware did not validate, not kept...'
          return 0
    else:
       print 'local copy already present:', localfw
       good = self.PickFirmware(localfw)

    if good:
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
    
    written = DroboDMP.put_sub_page( modepageblock, buffer, DEBUG )

    if DEBUG > 0:
      print "Page 0..."

    buflen=32768
    written=buflen
    i=self.fwhdr[0]
    j=i+buflen 
    moretocome=0x01

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
        written = DroboDMP.put_sub_page( modepageblock, self.fwdata[i:j], DEBUG )
        i=j

        function(i*100/totallength)
        print 'wrote ',written, ' bytes.  Cumulative: ',  i, ' of', totallength

    print 'writeFirmware Done.  i=%d, len=%d' % ( i, totallength )

    self.__transactionNext()
    
    paklen=1 
    modepageblock=struct.pack( ">BBBBBBBHB",
         0xea, 0x10, 0x80, 0x71, 0, self.transactionID, 0x01 << 5 , paklen, 0 )

    cmdout = DroboDMP.get_sub_page(paklen, modepageblock,0, DEBUG)
    status = struct.unpack( '>B', cmdout )

    if DEBUG > 0 : 
      print 'Drobo thinks write status is: ', status[0]

        


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
           li.append( (l[j+2], l2[k+3], l[j+4], partscheme(l2[k+4]), partformat(l2[k+5]) ) )
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
     ( utc, offset, name ) = self.__getsubpage(0x05, 'LH32s' )
     name=name.strip(" \0")
     offset=8 # offset is screwed up returned by Drobo, just set it to what they claim it should be.
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

     STATUS: works a bit, 
        relayoutcount stuff completely untested...
      Errata: 
      spec says a single byte.
      dmp.h says two longs:  (Status, RelayOutCount)
      Drobo always returns 0 for second Long.
      when I remove a disk, I get [ 'No Redundancy', 'Relay out in progress'],
      but when I format, it stays empty...
     """

     ss=self.__getsubpage(0x09, 'LL' )
     s=unitstatus(ss[0])

     if ss[1] > 0 : # relay out in progress
        if self.relaystart == 0:
           self.relaystart=time.time()
           self.relayinitialcount=ss[1]
        else: 
           now=time.time()
           runningtime=now - self.relaystart
           pctdone= ((self.relayinitialcount - ss[1])*1.0)/self.relayinitialcount
           pctleft= 1 - pctdone
           rate= pctdone / runningtime # pct/second...
           timeleft = pctleft*rate*60  # timeleft in minutes...
           s.append( '%d m. left' % timeleft )
     else:
        if self.relaystart > 0:
           self.relaystart == 0

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
     try: # insert try/except for compatibility with firmware <= 1.1.0  
         o = self.__getsubpage(0x07, 'BB5BBB' )
         return ( o[0], o[1], o[4] >>7 )
     except:
         return ( 0,0,0 )



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
          try: 
              d = Drobo( dev_file )
              fw=d.GetSubPageFirmware()
              if ( len(fw) >= 8 ) and (len(fw[7]) >= 5):
	          devices.append(dev_file)
          except:
 	      pass
       else:
	  pass
    return devices
