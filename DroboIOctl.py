"""
copyright:
Drobo Utils Copyright (C) 2008,2009  Peter Silva (Peter.A.Silva@gmail.com)
Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.
"""

from ctypes import *
from fcntl import ioctl
import Drobo
import struct


def hexdump(label, data):
    i = 0
    print(("%s %03x:" % (label, i)))
    for bb in data:
        if type(bb) is bytes:
            bb = ord(bb)
        print("%02x" % int(bb), end=' ')
        i = i + 1
        if (i % 16) == 0:
            print()
            print("%s %03x:" % (label, i), end=' ')
    print()


class sg_io_hdr(Structure):
    """

    do ioctl's using Linux generic SCSI interface.
    all of this comes from /usr/include/scsi/sg.h 

  """
    SG_DXFER_TO_DEV = -2
    SG_DXFER_FROM_DEV = -3
    SG_IO = 0x2285
    SG_GET_VERSION_NUM = 0x2282

    # see include/scsi/scsi.h for more values
    SAM_STAT_GOOD = 0x00
    SAM_STAT_CHECK_CONDITION = 0x02

    _fields_ = [
        ("interface_id", c_int),
        ("dxfer_direction", c_int),
        ("cmd_len", c_ubyte),
        ("mx_sb_len", c_ubyte),
        ("iovec_count", c_ushort),
        ("dxfer_len", c_int),
        ("dxferp", c_char_p),  # ought to be void...
        ("cmdp", c_char_p),
        ("sbp", c_char_p),
        ("timeout", c_uint),
        ("flags", c_uint),
        ("pack_id", c_int),
        ("usr_ptr", c_char_p),  # ought to be void...
        ("status", c_ubyte),
        ("masked_status", c_ubyte),
        ("msg_status", c_ubyte),
        ("sb_len_wr", c_ubyte),
        ("host_status", c_ushort),
        ("driver_status", c_ushort),
        ("resid", c_int),
        ("duration", c_uint),
        ("info", c_uint)
    ]

    def __init__(self):
        self.interface_id = ord('S')
        self.dxfer_direction = 0
        self.cmd_len = 0
        self.mx_sb_len = 0
        self.iovec_count = 0
        self.dxfer_len = 0
        self.dxferp = None
        self.cmdp = None
        self.timeout = 20000  # milliseconds
        #self.timeout=4000 # milliseconds
        self.flags = 0
        self.pack_id = 0
        self.usr_ptr = None
        self.status = 0
        self.masked_status = 0
        self.msg_status = 0
        self.sb_len_wr = 0
        self.host_status = 0
        self.driver_status = 0
        self.resid = 0
        self.duration = 0
        self.info = 0


class DroboIOctl:
    def __init__(self, char_dev_file, readwrite=1, debugflags=1):
        self.char_dev_file = char_dev_file
        self.sg_fd = open(char_dev_file, 'w')
        self.debug = debugflags

    def version(self):
        """
      
    
     """
        sfmt = "l"
        k = create_string_buffer(struct.calcsize(sfmt))
        if ioctl(self.sg_fd, sg_io_hdr.SG_GET_VERSION_NUM, k, True) < 0:
            print("%s is not an sg device, or old sg driver\n" % char_dev_file)
        num = struct.unpack(sfmt, k)
        return num[0]

    def closefd(self):
        if not type(self.sg_fd) is int:
            self.sg_fd.close()
        self.sg_fd = -1
        pass

    def identifyLUN(self):
        """
       issue a SCSI Identify LUN query, return the result.
 
      printf("%s: scsi%d channel=%d id=%d lun=%d", file_namep, host_no,
               (my_idlun.dev_id >> 16) & 0xff, my_idlun.dev_id & 0xff,
               (my_idlun.dev_id >> 8) & 0xff);
     """
        SCSI_IOCTL_GET_IDLUN = 0x5382
        SCSI_IOCTL_GET_BUS_NUMBER = 0x5386

        fmt = ">bbbbl"
        idlun = create_string_buffer(struct.calcsize(fmt))
        i = ioctl(self.sg_fd, SCSI_IOCTL_GET_IDLUN, idlun, True)
        if i < 0:
            print("Drobo get_mode_page SG_IO ioctl error")
            return None

        (channel, lun, id, host, host_unique_id) = struct.unpack(fmt, idlun)

        #print "%s: scsi%d channel=%d id=%d lun=%d" % ( self.char_dev_file, host, \
        #      channel, id, lun )

        #bog standard inquiry mcb
        fmt = "8s8s16s"
        hoholen = struct.calcsize(fmt)
        mcb = struct.pack("6B", 0x12, 0, 0, 0, hoholen, 0)

        # len ought to be 96
        hoho = self.get_sub_page(hoholen, mcb, 0, self.debug)
        (dunno1, vendor, product) = struct.unpack(fmt, hoho)

        return (host, channel, id, lun, vendor.decode())

    def get_sub_page(self, sz, mcb, out, DEBUG):
        """

     ioctl to retrieve a sub-page from the Drobo.
     required arguments:
            sz   : length of buffer to be returned.
                   if the ioctl indicates a residual amount
            control_block  : some scsi control block thingum...
                   pass transparently through to ioctl/SG
            out  : choose direction of xfer.  out= to device.
            debug : if 1,then print debugging output (lots of it.)

    """
        io_hdr = sg_io_hdr()

        if out:
            io_hdr.dxfer_direction = sg_io_hdr.SG_DXFER_TO_DEV
        else:
            io_hdr.dxfer_direction = sg_io_hdr.SG_DXFER_FROM_DEV

        if self.debug & Drobo.DBG_HWDialog:
            hexdump("mcb", mcb)

        io_hdr.cmd_len = len(mcb)
        io_hdr.cmdp = mcb

        sense_buffer = create_string_buffer(64)
        self.mx_sb_len = len(sense_buffer)
        io_hdr.sbp = cast(sense_buffer, c_char_p)
        io_hdr.sb_len_wr = 0  # initialize just in case...

        page_buffer = create_string_buffer(sz)
        io_hdr.dxfer_len = sz
        io_hdr.dxferp = cast(page_buffer, c_char_p)

        if self.debug & Drobo.DBG_HWDialog:
            print("4 before ioctl, sense_buffer_len=", io_hdr.mx_sb_len)

        i = ioctl(self.sg_fd, sg_io_hdr.SG_IO, io_hdr, True)

        if self.debug & Drobo.DBG_HWDialog:
            print("5 after ioctl, result=%d status: %d driver_status: %d host_status: %d sb_len_wr: %d resid: %d" % \
               ( i, io_hdr.status, io_hdr.driver_status, \
                  io_hdr.host_status, io_hdr.sb_len_wr, io_hdr.resid ))

        if i < 0:
            raise IOError("Drobo get_mode_page SG_IO ioctl error")

        if io_hdr.status != io_hdr.SAM_STAT_GOOD:
            raise IOError("io_hdr status is: %x" % io_hdr.status)

        if io_hdr.resid > 0:
            retsz = sz - io_hdr.resid
        else:
            retsz = sz

        if self.debug & Drobo.DBG_HWDialog:
            hexdump("page_buffer", page_buffer)
            print("the length is: ", retsz)
        return page_buffer[0:retsz]

    def put_sub_page(self, mcb, buffer, DEBUG):
        """

     ioctl to write using a sub-page to the Drobo.
     required arguments:
         modepageblock - 
        buffer
        DEBUG

     return the number of bytes written.
    """

        io_hdr = sg_io_hdr()

        io_hdr.dxfer_direction = sg_io_hdr.SG_DXFER_TO_DEV
        io_hdr.status = 99

        io_hdr.cmd_len = len(mcb)
        io_hdr.cmdp = mcb

        sense_buffer = create_string_buffer(32)
        io_hdr.mx_sb_len = len(sense_buffer)
        #io_hdr.sbp=addressof(sense_buffer)
        io_hdr.sbp = cast(sense_buffer, c_char_p)

        size = len(buffer)
        data2write = create_string_buffer(buffer, size)
        io_hdr.dxfer_len = size
        #io_hdr.dxferp = addressof(data2write)
        io_hdr.dxferp = cast(data2write, c_char_p)

        #these are set by ioctl... initializing just in case.
        io_hdr.sb_len_wr = 0
        io_hdr.resid = 0
        io_hdr.status = 0

        #iohp = cast(pointer(io_hdr), c_void_ptr).value

        i = ioctl(self.sg_fd, sg_io_hdr.SG_IO, io_hdr, True)

        if self.debug & Drobo.DBG_HWDialog:
            print("put_sub_page, 5 after ioctl, result=", i)
            print("status: ", io_hdr.status)
            print("driver_status: ", io_hdr.driver_status)
            print("host_status: ", io_hdr.host_status)
            print("sb_len_wr: ", io_hdr.sb_len_wr)
            print("resid: ", io_hdr.resid)

        if (i < 0):
            print(" get_mode_page SG_IO ioctl error")
            return None

        if (io_hdr.status != 0) and (io_hdr.status != 2):
            print("oh no! io_hdr status is: %x\n" % io_hdr.status)
            return None

        if io_hdr.resid > 0:
            size = size - io_hdr.resid

        return size


import os


def drobolunlist(debugflags=0, vendor="Drobo"):
    """
      return a list of attached Drobo devices, like so

       [ [lun0, lun1, lun2], [lun0, lun1, lun2] ]

      inspired by sg_scan.c (part of sg3_utils), sample output line:
        /dev/sdh: scsi41 channel=0 id=0 lun=0 [em]
        TRUSTED   Mass Storage      1.00 [rmb=0 cmdq=0 pqual=0 pdev=0x0]

      whose logic is encapsulated in the idenfityLUN call.
    """

    devdir = "/dev"
    devices = []
    lundevs = []
    previousdev = ""
    p = os.listdir(devdir)
    p.sort()  # to ensure luns in ascending order.

    for potential in p:
        if potential.startswith("sd") and len(potential) == 3:
            dev_file = devdir + '/' + potential
            try:
                if debugflags & Drobo.DBG_Detection:
                    print("examining: ", dev_file)
                pdio = DroboIOctl(dev_file)
            except:
                if debugflags & Drobo.DBG_Detection:
                    print("rejected: failed to construct LUN pdio")
                continue

            try:
                id = pdio.identifyLUN()
            except:
                if debugflags & Drobo.DBG_Detection:
                    print("rejected: failed to identify LUN")
                pdio.closefd()
                continue

            if debugflags & Drobo.DBG_Detection:
                print("id: ", id)

            thisdev = "%02d%02d%02d" % (id[0], id[1], id[2])
            if ( id[4].lower().startswith("trusted") or \
                 id[4].lower().startswith("drobo") or \
                 id[4].lower().startswith(vendor.lower()) ):  # you have a Drobo!
                if debugflags & Drobo.DBG_Detection:
                    print("found a Drobo")
                if thisdev == previousdev:  # multi-lun drobo...
                    if debugflags & Drobo.DBG_Detection:
                        print("appending to lundevs...")
                    lundevs.append(dev_file)
                else:
                    if lundevs != []:
                        devices.append(lundevs)
                    if debugflags & Drobo.DBG_Detection:
                        print("appending new lundevs to devices:", devices)
                    lundevs = [dev_file]

            else:
                if debugflags & Drobo.DBG_Detection:
                    print("rejected: vendor is %s (not from DRI)" % id[4])

            previousdev = thisdev
            pdio.closefd()

    if lundevs != []:
        devices.append(lundevs)

    if debugflags & Drobo.DBG_Detection:
        print("returning list: ", devices)
    return devices


# unit testing...
if __name__ == "__main__":
    import struct  # only for unit testing...
    valid_device = "/dev/sdg"
    #valid mcb: 5a 00 3a 01 00 00 00 00 14 00

    valid_mcb = struct.pack(">BBBBBBBBBB", 0x5a, 0, 0x3a, 1, 0, 0, 0, 0, 0x14,
                            0)
    dmp = DroboIOctl(valid_device)
    print("version", dmp.version())
    print("identifyLUN", dmp.identifyLUN())
    print("doing a sub_page")
    hoho = dmp.get_sub_page(20, valid_mcb, 0, 4)
    # the 4 byte header on the returned sense buffer:  (122, 1, 20)
    # cfg:  (4, 16, 1099511557632)

    #hexdump("hoho", hoho)
    fmt = ">BBHBBBQBHH"
    print(struct.calcsize(fmt))
    print(struct.unpack(fmt, hoho))
    dmp.closefd()

    print('hunt...')
    print(drobolunlist())
