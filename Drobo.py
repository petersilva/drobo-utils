"""
The Drobo module is used to get configuration data 
from a Data Robotics Inc. "Drobo" storage unit.
  
The ways of querying the unit are derived mostly from:
        DROBO Management Protocol Specification Rev. A.0 03/08

referred herein as 'DMP Spec'.  Another source of data was the
droboprotocoldefs.h file (referred to as dmp.h).  The last source 
of information is what the device actually does.  Many inconsistencies 
were identified.  ERRATA is used to identify when a conflict was apparent.

tested with firmware: 1.0.3 and later...

( Drobo is a trademark of Data Robotics Inc. )

copyright:
Drobo Utils Copyright (C) 2008,2009  Peter Silva (Peter.A.Silva@gmail.com)
Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.

"""

import fcntl, struct, socket, array, subprocess, time
import os, sys, re
import types

#only for fw download...
import os.path
import urllib.request, urllib.error, urllib.parse
import zipfile, zlib

#only for simulation mode...
import random

# maximum transaction ID before wrapping...
MAX_TRANSACTION = 250

# obviously need to update this with every release.
VERSION = '9999'

# set to non-zero to increase verbosity of library functions.
DEBUG = 0
# It's a bit field,
DBG_Chatty = 0x01
DBG_HWDialog = 0x02
DBG_Instantiation = 0x04
DBG_RawReturn = 0x08
DBG_Detection = 0x10
DBG_General = 0x20

# This isn't entirely simulation mode.  It is to aid development
# when no drobo is available.  You can format random disks, including
# non-drobos.  So do not activate unless you read what the code does first.
# in simulation mode, can run non-root, best for GUI work.
DBG_Simulation = 0x80

#for generic SCSI IO details...
import DroboIOctl


class DroboException(Exception):
    """  If there is a problem accessing the Drobo, this exception is raised.
  """
    def __init__(self, msg="Unknown"):
        self.msg = msg

    def __str__(self):
        print("Problem accessing a Drobo: " + self.msg)


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
    colourstats = [
        'black', 'red', 'yellow', 'green', ['red', 'green'], ['red', 'yellow'],
        ['red', 'black']
    ]
    if DEBUG & DBG_General:
        print('colourstats, argument n is: ', n)
    if (n == 0x80):  # empty
        return 'gray'
    return colourstats[n & 0x0f]


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
    if (n & 0x0002):
        f.append('Red alert')
    if (n & 0x0004):
        f.append('Yellow alert')
    if (n & 0x0008):
        f.append('No disks')
    if (n & 0x0010):
        f.append('Bad disk')
    if (n & 0x0020):
        f.append('Too many missing disks')
    if (n & 0x0040):
        f.append('No redundancy')
    if (n & 0x0080):
        f.append('No magic hotspare')
    if (n & 0x0100):
        f.append('no space left')
    if (n & 0x0200):
        f.append('Relay out in progress')
    if (n & 0x0400):
        f.append('Format in progress')
    if (n & 0x0800):
        f.append('Mismatched disks')
    if (n & 0x1000):
        f.append('Unknown version')
    if (n & 0x2000):
        f.append('New firmware installed')
    if (n & 0x4000):
        f.append('New LUN available after reboot')
    if (n & 0x10000000
        ):  # was going to say 'Let us pray...', but no need to alarm people.
        f.append('Unknown error')

    return f


def _partformat(n):
    """ return Drobo's idea of what the partition type is

        STATUS: working 
        
        worrisome... when multiple partitions present of different types, the
       bit field is set to: NO FORMAT.

    """
    f = []

    if (n & 0x01):
        f.append('NO FORMAT')
    if (n & 0x02):
        f.append('NTFS')
    if (n & 0x04):
        f.append('HFS')
    if (n & 0x80):  # on Peter's...
        f.append('EXT3')
    if (n & 0x08):  # on Matthew Mastracci's
        f.append('EXT3')
    if (n & 0xFF) == 0:
        f.append('FAT32')

    if (len(f) != 1):
        print('hoho! multiple partition types! Brave are we not?')

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


def _unitfeatures(norig):
    """ return a list of features supported by a unit
    
        STATUS: working.
        this comes straight from dmp.h.. what they mean isn't documented.
        stuff that looks wrong:        
                -- USED_CAPACITY... should be USE_CAPACITY ... no 'D'
                -- all the 'SUPPORTS' texts are redundant. every bit is about
                   what is supported.  It should be just LUNINFO2
         etc...                        
         feature x0800 and 0x2000 show up on my Drobo v1 running 1.3.0...
         of course, do not know what they are...
    """
    n = norig
    feature_map = [(0x0001, 'NO_AUTO_REBOOT'), (0x0002, 'NO_FAT32_FORMAT'),
                   (0x0004, 'USED_CAPACITY_FROM_HOST'),
                   (0x0008, 'DISKPACKSTATUS'), (0x0010, 'ENCRYPT_NOHEADER'),
                   (0x0020, 'CMD_STATUS_QUERIABLE'),
                   (0x0040, 'VARIABLE_LUN_SIZE_1_16'),
                   (0x0080, 'PARTITION_LUN_GPT_MBR'),
                   (0x0100, 'FAT32_FORMAT_VOLNAME'),
                   (0x0200, 'SUPPORTS_DROBOSHARE'),
                   (0x0400, 'SUPPORTS_NEW_LUNINFO2'),
                   (0x0800, 'feature x0800'), (0x1000, 'LUN_MANAGEMENT'),
                   (0x2000, 'feature x2000'), (0x4000, 'SUPPORTS_OPTIONS2'),
                   (0x8000, 'SUPPORTS_SHUTDOWN'), (0x10000, 'feature x10000'),
                   (0x20000, 'SUPPORTS_ISCSI'), (0x40000, 'feature x40000'),
                   (0x80000, 'feature x80000'),
                   (0x40000000, 'SUPPORTS_VOLUME_RENAME'),
                   (0x80000000, 'SUPPORTS_SINGLE_LUN_FORMAT')]
    f = []
    for feature in feature_map:
        #print "checking for %s %04x in %04x: " % ( feature[1], feature[0], n )
        if n & feature[0]:
            n = n & ~feature[0]
            f.append(feature[1])
    if n != 0:
        f.append("leftovers (0x%04x)" % n)

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
    def __init__(self, chardevs, debugflags=0):
        """ chardev is /dev/sdX... 
         the character device associated with the drobo unit
     """
        global DEBUG

        DEBUG = debugflags

        if DEBUG & DBG_Instantiation:
            print('__init__ ')

        self.fd = None

        if type(chardevs) is list:
            self.char_dev_file = chardevs[0]
            self.char_devs = chardevs
        else:
            self.char_dev_file = chardevs
            self.char_devs = [chardevs]

        self.features = []
        self.transactionID = random.randint(1, MAX_TRANSACTION)

        self.relaystart = 0

        if DEBUG & DBG_Simulation:
            self.GetSubPageFirmware() \
            #for the side effect, self.fw & self.features get set

        else:
            self.fd = DroboIOctl.DroboIOctl(self.char_dev_file, 0, debugflags)
            if self.fd == None:
                raise DroboException

            # more thorough checks for Drobohood...
            # for some reason under ubuntu intrepid, start getting responses of all bits set.
            # need some ways to spot a real drobo.
            cfg = self.GetSubPageConfig()
            #Side effect: Config, sets self.slot_count...

            self.inquiry = self.inquire()

            if DEBUG & DBG_Detection:
                print("cfg: ", cfg)

            if (len(cfg) != 3):  # We ask this page to return three fields...
                if DEBUG & DBG_Detection:
                    print("%s length of cfg is: %d, should be 3" %
                          (self.char_dev_file, len(cfg)))
                raise DroboException

            if (self.slot_count < 4):
                if DEBUG & DBG_Detection:
                    print(
                        "%s cfg[0] = %s, should >= 4. All Drobos have at least 4 slots"
                        % (self.char_dev_file, cfg[0]))
                raise DroboException  # Assert: All Drobo have 4 slots.

            set = self.GetSubPageSettings()
            if DEBUG & DBG_Detection:
                print("settings: ", set)

            self.GetSubPageFirmware()
            if (len(self.fw) < 8) and (len(self.fw[7]) < 5):
                if DEBUG & DBG_Detection:
                    print("%s length of fw query: is %d, should be < 8." %
                          (self.char_dev_file, len(self.fw)))
                    print("%s len(fw[7]) query: is %d, should be < 5." %
                          (self.char_dev_file, len(self.fw[7])))
                raise DroboException

            if (self.fw[6].lower() != 'armmarvell'):
                print("interesting, %s fw[6] is: %s" %
                      (self.char_dev_file, self.fw[6]))
            #if ( self.fw[6].lower() != 'armmarvell' ):
            #    if DEBUG & DBG_Detection:
            #      print "%s fw[6] is not armmarvell." % self.char_dev_file
            #    raise DroboException

    def __del__(self):

        if DEBUG & DBG_Instantiation:
            print('__del__ ')

        if self.fd != None:
            self.fd.closefd()

        self.fd = None

    def format_script(self, fstype='ext3'):
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

     algorithm:
        do discoverLUNs()
        figure out which LUNs belong to the current Drobo... How?
          -- do not want to partition LUNS on another Drobo!
             That would be bad!

        for l in LUN:
            parted /dev/sd?? mklabel gpt mkpart pri ext3 0 -1
            mke2fs -j ... /dev/sd??

     """

        format_script = '/tmp/fmtscript'
        fd = open(format_script, 'w')
        fd.write("#!/bin/sh\n")

        if fstype == 'FAT32' or fstype == 'msdos':
            ptype = 'msdos'
        else:
            ptype = 'gpt'

        for cd in self.char_devs:
            fd.write("parted -s %s mklabel %s\n" % (cd, ptype))

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
                fd.write("parted -s %s mkpart primary ext3 0 100%%\n" % cd)
                fd.write("parted -s %s print; sleep 5\n" % cd)
                fd.write(
                    'mke2fs -j -i 262144 -L Drobo01 -m 0 -O sparse_super,^resize_inode %s1\n'
                    % cd)
            elif fstype == 'ntfs':
                fd.write("parted -s %s mkpart primary ntfs 0 100%%\n" % cd)
                fd.write("parted -s %s print; sleep 5\n" % cd)
                fd.write('mkntfs -f -L Drobo01  %s1\n' % cd)
            elif fstype == 'FAT32' or fstype == 'msdos':
                fd.write("parted -s %s mkpart primary fat32 0 100%%\n" % cd)
                fd.write("parted -s %s print; sleep 5\n" % cd)
                fd.write('mkdosfs -v -v -F 32 -S 4096 -n Drobo01 %s1\n' % cd)
            else:
                print('unsupported  partition type %s, sorry...' % fstype)

        fd.close()
        os.chmod(format_script, 0o700)

        return format_script

    def __getsubpage(self, sub_page, pack):
        """Retrieve Sub page from drobo block device.
       Uses DroboIOctl class to run the raw ioctl.

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
            print('getsubpage')

        if DEBUG & DBG_Simulation:
            return ()

        mypack = '>BBH' + pack
        paklen = struct.calcsize(mypack)
        if DEBUG & DBG_RawReturn:
            print('DMIP sub_page query:0x%02x pattern: %s ' %
                  (sub_page, mypack))

        modepageblock = struct.pack(">BBBBBBBHB", 0x5a, 0, 0x3a, sub_page, 0,
                                    0, 0, paklen, 0)

        cmdout = self.fd.get_sub_page(paklen, modepageblock, 0, DEBUG)

        if len(cmdout) != paklen:
            print('expected %d, got %d bytes' % (len(cmdout), paklen))
            raise DroboException("cmdout is unexpected length")


#    print 'Pack: ' + mypack

        result = struct.unpack(mypack, cmdout)
        if DEBUG & DBG_HWDialog:
            print('4 byte returned sense buffer header: 0x%x, 0x%x, 0x%x' %
                  result[:3])
        if DEBUG & DBG_RawReturn:
            print('DMIP response sub_page:0x%02x returned: %s ' %
                  (sub_page, str(result[3:])))
        return result[3:]

    def __transactionNext(self):
        """ Increment the transaction member for some modeSelect pages.
    """
        if (self.transactionID > MAX_TRANSACTION):
            self.transactionID = 0
        self.transactionID = self.transactionID + 1

    def __issueCommand(self, command):
        """ issue a command to a Drobo...
     0x06 - blink.
     0x0d - Standby

     returns nothing, look at the drobo to see if it worked.
     note: command is asynchronous, returns before operation is complete.
    """

        if DEBUG & DBG_HWDialog:
            print('issuecommand...')

        if DEBUG & DBG_Simulation:
            self.__transactionNext()
            return

        modepageblock = struct.pack(">BBBBBBBHB", 0xea, 0x10, 0x00, command,
                                    0x00, self.transactionID, 0x01 << 5, 0x01,
                                    0x00)

        try:
            cmdout = self.fd.get_sub_page(1, modepageblock, 1, DEBUG)

        except:
            print(
                'IF you see, "bad address", it is because you need to be the super user...'
            )
            print(" try sudo or su ...       ")
            sys.exit()

        self.__transactionNext()

        if (len(cmdout) != 1):
            raise DroboException
        # only way to verify success is to look at the Drobo...

    def Sync(self, NewName=None):
        """  Set the Drobo's current time to the host's time,
         and the name to selected value.

     STATUS: works, maybe...
        DRI claims Drobos are all in California time.  afaict, it ignores TZ completely.
        I feed it UTC, and when I read the time, normal routines convert to local time.
        so it looks perfect.  but diagnostics might not agree.
    """
        if DEBUG & DBG_Simulation:
            return

        now = int(time.time())
        payload = "LH32s"
        payloadlen = struct.calcsize(payload)
        if NewName == None:
            NewName = self.GetSubPageSettings()[2]

        buffer = struct.pack(">BBH" + payload, 0x7a, 0x05, payloadlen, now, 0,
                             NewName)
        sblen = len(buffer)

        # mode select CDB.
        modepageblock = struct.pack(">BBBBBBBHB", 0x55, 0x01, 0x7a, 0x05, 0, 0,
                                    0, sblen, 0)
        self.fd.put_sub_page(modepageblock, buffer, DEBUG)

    def SetOptions(self, options):
        """ Set Options.
        accepts a set of options as returned by GetOptions

    STATUS: working. 
         basic thresholds work on Drobo v1.
         OPTIONS2 tested by folks on the internet.  Seem OK.

    """
        # v1 Options first...
        fmt = 'BBBLBB'
        payloadlen = struct.calcsize(fmt)
        buffer = struct.pack(">BBH" + fmt, 0x7a, 0x30, payloadlen,
                             options["YellowThreshold"],
                             options["RedThreshold"], 0, 0, 0, 0)
        sblen = len(buffer)
        modepageblock = struct.pack(">BBBBBBBHB", 0x55, 0x01, 0x7a, 0x30, 0, 0,
                                    0, sblen, 0)
        self.fd.put_sub_page(modepageblock, buffer, DEBUG)

        if ('SUPPORTS_OPTIONS2' in self.features):
            ip = struct.unpack('I', socket.inet_aton(options['IPAddress']))[0]
            nm = struct.unpack('I', socket.inet_aton(options['NetMask']))[0]
            rawip = socket.htonl(ip)
            rawnm = socket.htonl(nm)
            flags = 0
            if (options["DualDiskRedundancy"]):
                flags |= 0x0001
            if (options["SpinDownDelayMinutes"] > 0):
                flags |= 0x0002
            if (options["UseManualVolumeManagement"]):
                flags |= 0x0004
            if (options["UseStaticIPAddress"]):
                flags |= 0x0008

            fmt = 'QHLLB'
            payloadlen = struct.calcsize(fmt)
            # the ffff mask is there to suppress python 2.5 warning:
            #  DeprecationWarning: struct integer overflow masking is deprecated
            # which is quite strange because not a problem in 2.6.
            buffer = struct.pack(">BBH" + fmt, 0x7a, 0x31, payloadlen, \
              flags, options["SpinDownDelayMinutes"], \
               0xffffffff&rawip, 0xffffffff&rawnm, 0 )
            sblen = len(buffer)
            modepageblock=struct.pack( ">BBBBBBBHB", 0x55, 0x01, 0x7a, \
              0x31, 0, 0, 0, sblen, 0)
            self.fd.put_sub_page(modepageblock, buffer, DEBUG)

        return

    def SetLunSize(self, tb):
        """
       SetLunSize - Sets the maximum LUN size to 'tb' terabytes

       status:  works with no issues!
    """
        if (DEBUG & DBG_Chatty):
            print('set lunsize to %d TiB' % tb)

        if not self.umount():
            if (DEBUG & DBG_Chatty):
                print('cannot free up Drobo to set lunsize')
            return

        buffer = struct.pack(">l", tb)
        sblen = len(buffer)

        # mode select CDB.
        modepageblock = struct.pack(">BBBBBBBHB", 0xea, 0x10, 0x0, 0x0f, 0,
                                    self.transactionID, (0x01 << 5) | 0x01,
                                    sblen, 0x00)

        self.fd.put_sub_page(modepageblock, buffer, DEBUG)
        self.__transactionNext()

    def SlotCount(self):
        self.GetSubPageConfig()
        return self.slot_count

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
        if self.umount():
            self.__issueCommand(0x0d)

    def GetDiagRecord(self, diagcode, decrypt=0):
        """ returns diagnostics as a string...
        diagcodes are either 4 or 7 for the two different Records available.

        STATUS: works fine.

        decryption done in drobom (look at diagprint)
    """
        if DEBUG & DBG_Chatty:
            print("Dumping Diagnostics...")

        # tried 32000 ... it only returned 5K, so try something small.
        buflen = 4096

        modepageblock = struct.pack(">BBBBBBBHB", 0xea, 0x10, 0x80, diagcode,
                                    0x00, self.transactionID,
                                    (0x01 << 5) | 0x01, buflen, 0x00)

        todev = 0

        if DEBUG & DBG_General:
            print("Page 0...")

        cmdout = self.fd.get_sub_page(buflen, modepageblock, todev, DEBUG)
        diags = cmdout
        i = 0
        while len(cmdout) == buflen:
            modepageblock = struct.pack(">BBBBBBBHB", 0xea, 0x10, 0x80,
                                        diagcode, 0x00, self.transactionID,
                                        0x01, buflen, 0x00)

            cmdout = self.fd.get_sub_page(buflen, modepageblock, todev, DEBUG)
            i = i + 1
            diags = diags + cmdout

            if DEBUG & DBG_General:
                print("diags ", i, ", cmdlen=", len(cmdout), " diagslen=",
                      len(diags))

        return diags

    def dumpDiagnostics(self):

        n = time.gmtime()

        dfname = "/tmp/DroboDiag_%d_%02d%02d_%02d%02d%02d.log" % (n[0:6])
        df = open(dfname, "w")
        d = self.GetDiagRecord(4)
        df.write(d)
        d = self.GetDiagRecord(7)
        self.__transactionNext()
        df.write(d)
        df.close()
        return dfname

    def decodeDiagnostics(self, diagfilename):
        try:
            f = open(diagfilename)
            data = f.read()
            f.close()
        except:
            return ''

        key = ord(data[0]) ^ 0x2d
        datam = ''.join([chr(ord(x) ^ key) for x in data])
        return datam

    #
    # constants for use with firmware operations
    #

    fwsite = "ftp://updates.drobo.com/"
    localfwrepository = os.path.expanduser("~") + "/.drobo-utils"

    def localFirmwareRepository(self):
        return Drobo.localfwrepository

    def PickFirmware(self, name):
        """
       read in a given firmware from disk.

       sets self.fwdata

    """
        if (DEBUG & DBG_Chatty):
            print('Reading Firmware from = %s' % name)

        if (name[-1] == 'z'):  # data is zipped...
            inqw = self.inquiry
            hwlevel = inqw[10]
            z = zipfile.ZipFile(name, 'r')
            for f in z.namelist():
                if (DEBUG & DBG_General):
                    print(f, ' ? ')
                    print('firmware for hw rev ', f[-5], ' this drobo is rev ',
                          hwlevel[0])
                if f[-5] == hwlevel[0]:
                    self.fwdata = z.read(f)
        else:  # old file...
            f = open(name, 'r')
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
        dpropack = '>BBBBBBBB8s16s4s'
        mypack = dpropack + '20sBB8HH'
        paklen = struct.calcsize(mypack)

        modepageblock = struct.pack("BBBBBB", 0x12, 0, 0, 0, paklen, 0)

        cmdout = self.fd.get_sub_page(paklen, modepageblock, 0, DEBUG)
        if (len(cmdout) == paklen):
            ret = struct.unpack(mypack, cmdout)
        else:
            if (len(cmdout) == 36):  # we have a PRO...
                ret = struct.unpack(dpropack, cmdout)
            else:
                print(
                    'warning: scsi inquire returned %d, bytes instead of %d expected.'
                    % (len(cmdout), paklen))
                raise DroboException
        if DEBUG & DBG_RawReturn:
            print("inquiry response: ", str(ret))
        return ret

    def PickLatestFirmware(self):
        """
       fetch firmware from web site. ... should be a .tdf or .tdz file.
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
        if DEBUG & DBG_Simulation:
            return ('fwarch', 'fwv', 'hwlevel', 'value')

        inqw = self.inquiry
        hwlevel = inqw[10]
        fwv = str(self.fw[0]) + '.' + str(self.fw[1]) + '.' + str(self.fw[2])

        #FIXME ugly hack to force v1 to get onto the v2 firmware stream
        #  current dri index.txt file says v1's should run 1.1.2, but win/Mac dashboards upgrade
        #  to 1.2.4 anyways...  so I guess linux should too.
        #  if a v1 is running 1.1.2, then just claim to be an early v2 firmware, all should work.
        #if fwv == "1.200.11177":
        #   fwv="1.201.12942"

        fwarch = self.fw[6].lower()

        if (DEBUG & DBG_Chatty):
            print('looking for firmware for:', fwarch, fwv, 'hw version:',
                  hwlevel)
        listing_file = urllib.request.urlopen(Drobo.fwsite + "index.txt")
        list_of_firmware_string = listing_file.read().decode().strip("\t\r")
        list_of_firmware = list_of_firmware_string.split("|")
        i = 1
        p = re.compile('\[(.*)\]')
        while i < len(list_of_firmware):
            key = list_of_firmware[i - 1].split()[1]
            value = list_of_firmware[i].split()[1]

            k = key.split('/')

            # profits oblige...
            if k[2] == "licensed":
                k = k[0:2] + k[3:]
                #print k

            # these If's are now nested for ease of debugging, insert a print to taste...
            # the algorithm is wrong wrt, other platforms...
            if k[2] == "firmware":
                #print '    match firmware'
                if k[3] == fwarch:
                    #print '    match k[3] = ', fwarch
                    #if we are on a line that lists the fwversion in [] fixup k[4]
                    m = p.search(list_of_firmware[i - 1])
                    if m:
                        k[4] = m.group(1)
                    if k[4] == fwv:
                        if len(k) > 4:
                            if (DEBUG & DBG_Chatty):
                                print('This Drobo should be running: ', value)
                            return (fwarch, fwv, hwlevel, value)
            i = i + 2
        if (DEBUG & DBG_Chatty):
            print(
                'no matching firmware found, must be the latest and greatest!')
        return ('', '', '', '')

    def downloadFirmware(self, fwname, localfw):
        """
      download given fw file from network repository.
      load self.fwdata with the data from it

      STATUS: works.
    """
        if (DEBUG & DBG_Chatty):
            print('downloading firmware ', fwname, '...')
        self.fwdata = None
        firmware_url = urllib.request.urlopen(Drobo.fwsite + fwname)
        filedata = firmware_url.read()
        f = open(localfw, 'w+')
        f.write(filedata)
        f.close()
        if (DEBUG & DBG_Chatty):
            print('local copy written')

        if (fwname[-1] == 'z'):  # data is zipped...
            self.PickFirmware(localfw)
        else:
            self.fwdata = filedata

        if (DEBUG & DBG_Chatty):
            print('downloading done ')
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
            print('validateFirmware start...')
        self.fwhdr = struct.unpack('>ll4sl16slllll256sl', self.fwdata[0:312])

        if len(self.fwdata) != (self.fwhdr[0] + self.fwhdr[8]):
            print('header corrupt... Length does not validate.')
            return 0

        if (DEBUG & DBG_Chatty):
            print('header+body lengths validated.  Good.')
        #print self.fwhdr

        if self.fwhdr[2] != 'TDIH':
            print('bad Magic, not a valid firmware')
            return 0

        if (DEBUG & DBG_Chatty):
            print('Magic number validated. Good.')
            print('%d + %d = %d length validated. Good.' %
                  (self.fwhdr[0], self.fwhdr[8], len(self.fwdata)))

        # http://bugs.python.org/issue1202
        # doesn't work on 64 bit, only on 32bit... weird...
        blank = struct.pack('i', 0)
        hdrcrc = zlib.crc32(self.fwdata[0:308] + blank +
                            self.fwdata[312:self.fwhdr[0]]) & 0xffffffff
        r = self.fwhdr[11] & 0xffffffff

        if (DEBUG & DBG_Chatty):
            print(
                'CRC from header: %d, calculated using python zlib crc32: %d '
                % (r, hdrcrc))
        if r != hdrcrc:
            print('file corrupt, header checksum wrong')
            return 0
        bodycrc = zlib.crc32(self.fwdata[self.fwhdr[0]:]) & 0xffffffff
        q = self.fwhdr[9] & 0xffffffff

        if (DEBUG & DBG_Chatty):
            print('CRC for body from header: %d, calculated: %d ' %
                  (q, bodycrc))
        if q != bodycrc:
            print('file corrupt, payload checksum wrong')
            return 0

        if (DEBUG & DBG_Chatty):
            print('32 bit Cyclic Redundancy Check correct. Good.')
            print('validateFirmware successful...')

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

      STATUS: working.

    """
        (fwarch, fwversion, hwlevel, fwpath) = self.PickLatestFirmware()
        if fwarch == '':  # already at latest version...
            return 0

        if not os.path.exists(Drobo.localfwrepository):
            os.mkdir(Drobo.localfwrepository)

        fwname = fwpath.split('/')
        hwlevel = hwlevel.decode()
        localfw = Drobo.localfwrepository + '/' + fwarch + '_' + hwlevel + '_' + fwname[
            -1]
        if (DEBUG & DBG_Chatty):
            print('looking for: %s' % localfw)
        if not os.path.exists(localfw):
            if (DEBUG & DBG_Chatty):
                print('not present, fetching from drobo.com')
            self.fwdata = self.downloadFirmware(fwpath, localfw)
            good = self.validateFirmware()
            if not good:
                print('downloaded firmware did not validate.')
                return 0
        else:
            if (DEBUG & DBG_Chatty):
                print('local copy already present:', localfw)
            good = self.PickFirmware(localfw)

        if good:
            if (DEBUG & DBG_Chatty):
                print('correct fw available')
            return 1

        print('no valid firmware found')
        return 0

    def writeFirmware(self, function):
        """
        given good firmware data, upload it to the Drobo...

        1_README_*.txt from the resource kit is followed here.

        function -- a callback that accepts a single argument, an integer in the range 0-100.
           indicates % done.  the function is called after each write in the loop.

        STATUS: works.

    """

        totallength = len(self.fwdata)
        buffer = struct.pack(">L", totallength) + self.fwdata[0:self.fwhdr[0]]

        modepageblock = struct.pack(">BBBBBBBHB", 0xea, 0x10, 0x00, 0x70, 0x00,
                                    self.transactionID, (0x01 << 5) | 0x01,
                                    len(buffer), 0x00)

        written = self.fd.put_sub_page(modepageblock, buffer, DEBUG)

        if DEBUG & DBG_General:
            print("Page 0...")

        buflen = 32768
        written = buflen
        i = self.fwhdr[0]
        j = i + buflen
        moretocome = 0x01

        if (DEBUG & DBG_General):
            print('writeFirmware: i=%d, start=%d, last=%d fw length= %d\n' % \
               ( i, self.fwhdr[0], totallength, len(buffer) ))

        while (written == buflen) and (i < len(self.fwdata)):

            if (i + buflen) > totallength:  # writing the last record.
                buflen = totallength - i
                moretocome = 0

            modepageblock = struct.pack(">BBBBBBBHB", 0xea, 0x10, 0x00, 0x70,
                                        0x00, self.transactionID, moretocome,
                                        buflen, 0x00)

            j = i + buflen
            written = self.fd.put_sub_page(modepageblock, self.fwdata[i:j],
                                           DEBUG)
            i = j

            function(i * 100 / totallength)

            if (DEBUG & DBG_General):
                print('wrote ', written, ' bytes.  Cumulative: ', i, ' of',
                      totallength)

        if (DEBUG & DBG_General):
            print('writeFirmware Done.  i=%d, len=%d' % (i, totallength))

        self.__transactionNext()

        paklen = 1
        modepageblock = struct.pack(">BBBBBBBHB", 0xea, 0x10, 0x80, 0x71, 0,
                                    self.transactionID, 0x01 << 5, paklen, 0)

        cmdout = self.fd.get_sub_page(paklen, modepageblock, 0, DEBUG)
        status = struct.unpack('>B', cmdout)

        if DEBUG & DBG_General:
            print('Drobo thinks write status is: ', status[0])

    def GetCharDev(self):
        return self.char_dev_file

    def GetSubPageConfig(self):
        """ returns: ( MaxNumberOfSlots, MaxNumLUNS, MaxLunSize )
     """
        # SlotCount, Reserved, MaxLuns, MaxLunSz, Reserved, unused, unused

        if DEBUG & DBG_Simulation:
            self.slot_count = 8
            return (8, 16, 2199023250944)

        result = self.__getsubpage(0x01, 'BBBQ')
        self.slot_count = result[0]
        return (result[0], result[2], result[3] * 512)

    def GetSubPageCapacity(self):
        """ returns: ( Free, Used, Virtual, Unprotected ) 
     """
        if DEBUG & DBG_Simulation:
            capacity = 495452160000
            used = random.randint(0, capacity)
            return (capacity - used, used, capacity, 125184245760)

        return self.__getsubpage(0x02, 'QQQQ')

    def GetSubPageSlotInfo(self):
        """  returns list of slot info, each slot is:
       ( slotId, PhysicalCapacity, ManagedCapacity, leds, Manufacturer, Model ) ... )
       
       leds - indicates what the lights on the front panel are doing.
              returns one colour if one colour is constant, set of
              colours if there is flashing going on.
     """
        if DEBUG & DBG_Simulation:
            return ((0, 500107862016, 0, 'green', 'ST3500830AS',
                     'ST3500830AS'), (1, 750156374016, 0, 'green',
                                      'WDC WD7500AAKS-00RBA0',
                                      'WDC WD7500AAKS-0'),
                    (2, 0, 0, _ledstatus(random.randint(0, 6)), '', ''),
                    (3, 0, 0, 'gray', '', ''), (0, 500107862016, 0, 'green',
                                                'ST3500830AS', 'ST3500830AS'),
                    (1, 750156374016, 0, 'green', 'WDC WD7500AAKS-00RBA0',
                     'WDC WD7500AAKS-0'), (2, 0, 0,
                                           _ledstatus(random.randint(0, 6)),
                                           '', ''), (3, 0, 0, 'gray', '', ''))

        slotrec = 'HBQQB32s16sL'

        i = 0
        pattern = 'B' + slotrec * self.slot_count

        r = self.__getsubpage(0x03, pattern)

        l = []
        j = 0

        # The normal thing to do, which was here, is to use r[0] which is supposed
        # to indicate the number of records returned.  Unfortunately, a bug in
        # Drobo S, has it return 8 for r[0], instead of 5.  So use a surrogate found elsewhere.
        #
        # this is safe because slot_count is initialized in init.
        #
        while (j < self.slot_count):
            i = j * 8
            s = (r[i + 2], r[i + 3], r[i + 4], _ledstatus(r[i + 5]),
                 r[i + 6].decode().strip(" \0"),
                 r[i + 7].decode().strip(" \0"))
            l.append(s)
            j = j + 1

        return l

    def GetSubPageLUNs(self):
        """
         For each LUN, returns detailed information tuple:
            [ ( LUNID, LUN total Capacity, LUN Used Capacity, PartitionScheme*, Format* ),
                ... ]

         *only returned if firmware: SUPPORTS_NEW_LUNINFO2 (essentially >=1.1.0)

      STATUS: works, with worries and omissions:

      question: is it correct to mix 'used capacity' from luninfo, with 
      total capacity from luninfo2?

      parameter luninfo2[k+4] is supposed to be partcount...
      but 'PartCount' is odd. Seems to always be 128 (0x80)
         once partitions are set on my v1.  perhaps indicates maximum?

      if you mix partition types within a single Drobo, Drobo tends to give up
      and claim "no partitions" rather than reporting the union of the types.
     """
        if DEBUG & DBG_Simulation:
            return [(0, 2199023251456, 5092651008, 'GPT', 1, ['EXT3'])]

        lp = "HBQQ"
        l = self.__getsubpage(0x04, 'B' + lp * 8)

        if ('SUPPORTS_NEW_LUNINFO2' in self.features):
            # must ensure li2 fields have correct count.
            li2fieldcount = 10
            li2 = "HBQBBBH3B"
            l2 = self.__getsubpage(0x07, "B" + li2 * 8)

        i = 0
        li = []
        while (i < l[0]):
            j = i * 4
            if ('SUPPORTS_NEW_LUNINFO2' in self.features):
                k = 1 + i * li2fieldcount

                # sanity check, in case I ever get out of sync again...
                if l2[k] != 17:
                    print(
                        'Warning: probably have not grokked the LUNINFO2 record correctly'
                    )

                li.append((l2[k + 1], l2[k + 2], l[j + 4],
                           _partscheme(l2[k + 3]), _partformat(l2[k + 5])))
            else:
                li.append((l[j + 2], l[j + 3], l[j + 4]))
            i = i + 1

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

        (utc, offset, name) = self.__getsubpage(0x05, 'LH32s')
        name = name.decode().strip(" \0")
        offset = 8  # offset is screwed up returned by Drobo, just set it to what they claim it should be.
        return (utc, offset, name)

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

        return self.__getsubpage(0x06, 'BB')

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
            self.features=['NO_AUTO_REBOOT', 'NO_FAT32_FORMAT', \
                   'USED_CAPACITY_FROM_HOST', 'DISKPACKSTATUS', \
                   'ENCRYPT_NOHEADER', 'CMD_STATUS_QUERIABLE', \
                   'VARIABLE_LUN_SIZE_1_16', 'PARTITION_LUN_GPT_MBR', \
                   'FAT32_FORMAT_VOLNAME', 'SUPPORTS_OPTIONS2', \
                   'SUPPORTS_DROBOSHARE', 'SUPPORTS_NEW_LUNINFO2']
            self.fw=(1, 201, 12942, 12, 6, 'May 13 2008,15:29:32', \
                     'ArmMarvell', '1.1.2', self.features )
            return self.fw

        raw = self.__getsubpage(0x08, 'BBHBB32s16s16s240s')
        result = struct.unpack('>112sL32sH90s', raw[8])
        self.features = _unitfeatures(result[1])
        self.fw = (raw[0], raw[1], raw[2], raw[3], raw[4],
                   raw[5].decode().strip(" \0"), raw[6].decode().strip(" \0"),
                   raw[7].decode().strip(" \0"), self.features)
        return self.fw

    def GetSubPageStatus(self):
        """
     return _unitstatus

     STATUS: works a bit, 
        relayoutcount stuff completely untested...
      Errata: 
      spec says a single byte.
      dmp.h says two longs:  (Status, RelayOutCount)
      when I remove a disk, I get [ 'No Redundancy', 'Relay out in progress'],
      but when I format, it stays empty...
     """
        if DEBUG & DBG_Simulation:
            return _unitstatus(random.randint(0, 16535))

        ss = self.__getsubpage(0x09, 'LL')
        s = _unitstatus(ss[0])

        if ss[1] > 0:  # relay out in progress
            if self.relaystart == 0:
                self.relaystart = time.time()
                self.relayinitialcount = ss[1]
                s.append('no estimate yet ')
            else:
                now = time.time()
                runningtime = (now - self.relaystart) / 60.0
                amtdone = self.relayinitialcount - ss[1]
                amtleft = ss[1]
                pctleft = 100.0 * amtleft / self.relayinitialcount
                pctdone = 100 - pctleft

                if amtdone == 0:
                    s.append('gathering stats, no estimate yet ')
                else:
                    rate = pctdone / runningtime
                    timeleft = pctleft * rate  # timeleft in minutes...
                    s.append('%d blocks left ' % ss[1])
        else:
            if self.relaystart > 0:
                self.relaystart == 0

        return (s, ss[1])

    def GetOptions(self):
        """
        different fw/hw combinations will return different results.
        return one of:
           None 
               - this drobo does not support Options ( fw < 1.11 )
           ( YellowThresh, RedThresh, AutoDelSnapshot, LowYel, LowRed )
               - drobo supports first version of options ( fw >= 1.11)
             ( above + FeatureOnOffStates, SpinDownDelay, IPAddress, Subnetmask ) 
               - DroboPro only ? my v1's don't support it.
        
        STATUS: untested, seems to agree with dmp.h for Options
            Options2 (only on Drobo Pro) completely un-tested.


        DMIP spec says:
           B-YelThresh, B-RedThresh, 5B-Rsvd, 1bit-AutoDel, B-Rsvd

        dmp.h (published 2007 and summer 2009) says:
           B-YelThresh, B-RedThresh, B-Flags, L-DataCheckParam, B-LowYelThresh, B-LowRedThresh.
        
        later firmware version and dmp published in 2009 adds OPTIONS2 with
        hmm...
     """
        if DEBUG & DBG_Simulation:
            return {"YellowThreshold":85, "RedThreshold":95, \
                    "SpinDownDelayMinutes":5, "SpinDownDelay": True, \
                    "UseStaticIPAddress":True, "IPAddress":'192.168.10.4', \
                    "NetMask":'255.255.255.0', "DualDiskRedundancy":True, \
                    "UseManualVolumeManagement":False }
        if 'SUPPORTS_OPTIONS2' in self.features or self.fw[7] >= '1.1.0':
            # insert try/except for compatibility with firmware <= 1.1.0
            o = self.__getsubpage(0x30, 'BBBIBB')
            d = {"YellowThreshold": o[0], "RedThreshold": o[1]}
            if ('SUPPORTS_OPTIONS2' in self.features):
                ( flags, d['SpinDownDelayMinutes'], \
                  rawipb, rawnmb, rawgwb, mtub, \
                  rawipa, rawnma, rawgwa, mtua ) = \
                  self.__getsubpage(0x31, 'QHLLLHLLLH' )
                d['Flags'] = flags
                d['DualDiskRedundancy'] = (flags & 0x0001) > 0
                d['SpinDownDelay'] = (flags & 0x0002) > 0
                d['UseManualVolumeManagement'] = (flags & 0x0004) > 0
                if ('SUPPORTS_ISCSI' in self.features):
                    d['UseStaticIPAddress'] = (flags & 0x0008) > 0
                    ipb = socket.ntohl(rawipb)
                    maskb = socket.ntohl(rawnmb)
                    gwb = socket.ntohl(rawgwb)
                    if (mtua > 0):
                        ipa = socket.ntohl(rawipa)
                        maska = socket.ntohl(rawnma)
                        gwa = socket.ntohl(rawgwa)
                        d['IPAddress'] = socket.inet_ntoa(struct.pack(
                            'I', ipa))
                        d['NetMask'] = socket.inet_ntoa(struct.pack(
                            'I', maska))
                        d['Gateway'] = socket.inet_ntoa(struct.pack('I', gwa))
                        d['MTU'] = mtua
                        d['IPAddress2'] = socket.inet_ntoa(
                            struct.pack('I', ipb))
                        d['NetMask2'] = socket.inet_ntoa(
                            struct.pack('I', maskb))
                        d['Gateway2'] = socket.inet_ntoa(struct.pack('I', gwb))
                        d['MTU2'] = mtub
                    else:
                        d['IPAddress'] = socket.inet_ntoa(struct.pack(
                            'I', ipb))
                        d['NetMask'] = socket.inet_ntoa(struct.pack(
                            'I', maskb))
                        d['Gateway'] = socket.inet_ntoa(struct.pack('I', gwb))
            return d
        else:
            return None

    def umount(self):
        """
       umount all file systems using the given Drobo.
       return true on success, false on failure.
    """

        if DEBUG & DBG_Simulation:
            return True

        toumount = self.DiscoverMounts()
        if len(toumount) > 0:
            for i in toumount:
                if DEBUG & DBG_Chatty:
                    print("unmounting: ", i)
                umresult = os.system("umount " + i)
                if umresult != 0:
                    return False
        return True

    def DiscoverMounts(self):
        """
        return the list of mounted file systems using the unit.
    """

        if DEBUG & DBG_Simulation:
            return ["/drmnt0", "/drmnt2"]

        mounts = open("/etc/mtab")
        dlen = len(self.char_dev_file)
        filesystems = []
        for l in mounts.readlines():
            fields = l.split()
            for i in self.char_devs:
                if fields[0][0:dlen] == i:
                    filesystems.append(fields[1])
        mounts.close()
        return filesystems


def DiscoverLUNs(debugflags=0, vendorstring="Drobo"):
    """ find all Drobo LUNs accessible to this user on this system. 
        returns a list of list of character device files 
              samples: [ [ "/dev/sdf", "/dev/sdg" ], [ "/dev/sdh" ] ] 
        vendorstring adds a string to be compared to for SCSI ID LUN call.
        This value changes as new products are introduced.
    """
    global DEBUG
    DEBUG = debugflags

    if DEBUG & DBG_Simulation:
        return [["/dev/sdx", "/dev/sdy"], ["/dev/sdz"]]

    devices = []

    for potential in DroboIOctl.drobolunlist(DEBUG, vendorstring):
        if (DEBUG & DBG_Detection):
            print("trying: ", potential)

        try:
            d = Drobo(potential, DEBUG)
            devices.append(potential)
        except:
            pass

    return devices
