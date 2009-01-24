
from ctypes import *
from fcntl import ioctl
import Drobo

def hexdump(label,data):
      i=0
      print "%s %03x:" % (label, i),
      for bb in data:
         print "%02x" % ord(bb), 
         i=i+1
         if (i % 16) == 0:
             print
             print "%s %03x:" % (label,i),
      print


from ctypes import *


class sgio(Structure):
  """

    do ioctl's using Linux generic SCSI interface.
    all of this comes from /usr/include/scsi/sg.h 

  """
  SG_DXFER_TO_DEV=-2
  SG_DXFER_FROM_DEV=-3
  SG_IO = 0x2285
  SG_GET_VERSION_NUM = 0x2282

  _fields_ = [ ("interface_id", c_int ),
    ("dxfer_direction", c_int),
    ("cmd_len", c_ubyte),
    ("mx_sb_len", c_ubyte),
    ("iovec_count", c_ushort),
    ("dxfer_len", c_int),
    ("dxferp", c_char_p), # ought to be void...
    ("cmdp", c_char_p),
    ("sbp", c_char_p),
    ("timeout", c_uint),
    ("flags", c_uint),
    ("pack_id", c_int),
    ("usr_ptr", c_char_p), # ought to be void...
    ("status", c_ubyte),
    ("masked_status", c_ubyte),
    ("msg_status", c_ubyte),
    ("sb_len_wr", c_ubyte),
    ("host_status", c_ushort),
    ("driver_status", c_ushort),
    ("resid", c_int),
    ("duration", c_uint),
    ("info", c_uint) ]


  def __init__(self):
     self.interface_id=ord('S')
     self.dxfer_direction=0
     self.cmd_len=0
     self.mx_sb_len=0
     self.iovec_count=0
     self.dxfer_len=0
     self.dxferp=None
     self.cmdp=None
     self.timeout=20000 # milliseconds
     #self.timeout=4000 # milliseconds
     self.flags=0
     self.pack_id=0
     self.usr_ptr=None
     self.status=0
     self.masked_status=0
     self.msg_status=0
     self.sb_len_wr=0
     self.host_status=0
     self.driver_status=0
     self.resid=0
     self.duration=0
     self.info=0


class DroboIOctl():

  def __init__(self,char_dev_file,readwrite,debugflags):
     self.char_dev_file=char_dev_file
     self.sg_fd=open(char_dev_file,'w')
     self.debug=debugflags
  
  def version(self):
     """
    
     """
     k=create_string_buffer(8) 
     if ioctl(self.sg_fd, sgio.SG_GET_VERSION_NUM, k) < 0 :
        print "%s is not an sg device, or old sg driver\n" % char_dev_file
     num=struct.unpack("l",k) 
     return num

  def closefd(self):
     self.sg_fd.close()
     pass

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
    io_hdr=sgio()

    if out:
      io_hdr.dxfer_direction=sgio.SG_DXFER_TO_DEV
    else:
      io_hdr.dxfer_direction=sgio.SG_DXFER_FROM_DEV

    if self.debug & Drobo.DBG_HWDialog:
        hexdump("mcb", mcb)

    io_hdr.cmd_len = len(mcb)
    io_hdr.cmdp = mcb

    sense_buffer = create_string_buffer(64)
    self.mx_sb_len = len(sense_buffer)
    io_hdr.sbp=addressof(sense_buffer)
    io_hdr.sb_len_wr = 0 # initialize just in case...

    
    page_buffer=create_string_buffer(sz)
    io_hdr.dxfer_len = sz
    io_hdr.dxferp = addressof(page_buffer)

    if self.debug & Drobo.DBG_HWDialog:
      print "4 before ioctl, sense_buffer_len=", io_hdr.mx_sb_len

    i=ioctl(self.sg_fd, sgio.SG_IO, io_hdr)

    if i < 0:
        print "Drobo get_mode_page SG_IO ioctl error"
        return None
 
    if self.debug & Drobo.DBG_HWDialog:
      print "5 after ioctl, result=", i
      print "status: ", io_hdr.status
      print "driver_status: ", io_hdr.driver_status
      print "host_status: ", io_hdr.host_status
      print "sb_len_wr: ", io_hdr.sb_len_wr
      print "resid: ",  io_hdr.resid

    if (io_hdr.status != 0 ) and (io_hdr != 2) :
        print "oh no! io_hdr status is: %x\n" %  io_hdr.status
        return None

    if io_hdr.resid > 0:
       retsz = sz - io_hdr.resid
    else:
       retsz = sz

    if self.debug & Drobo.DBG_HWDialog:
       hexdump("page_buffer", page_buffer)
       print "the length is: ", retsz
    return page_buffer[0:retsz]


  def put_sub_page(self, modepageblock, data2write, DEBUG ):
    """

     ioctl to write using a sub-page to the Drobo.
     required arguments:
	modepageblock - 
        data2write
        DEBUG

     return the number of bytes written.
    """
    return None

    io_hdr=sgio()
    io_hdr.dxfer_direction=sgio.SG_DXFER_TO_DEV
    mcb=create_string_buffer(modepageblock)
    sense_buffer = create_string_buffer(32)
    io_hdr.sbp=addressof(sense_buffer)
    io_hdr.status=99;

    page_buffer=create_string_buffer(sz)

    io_hdr.cmd_len = len(mcb)
    io_hdr.mx_sb_len = sizeof(sense_buffer)
    io_hdr.dxfer_len = sizeof(data2write)
    io_hdr.dxferp = addressof(data2write)
    io_hdr.cmdp = mcb.raw

    #these are set by ioctl... initializing just in case.
    io_hdr.sb_len_wr=0;
    io_hdr.resid=0;
    io_hdr.status=0;

    #PUT PUT PUT PUT PUT
    iohp = cast(pointer(io_hdr), c_void_ptr).value
    #PUT PUT PUT PUT PUT
    i=ioctl(self.sg_fd, sgio.SG_IO, iohp)
    #PUT PUT PUT PUT PUT
 
    if (i< 0) :
       print " get_mode_page SG_IO ioctl error"
       return None
 
    return i

# unit testing...
if __name__ == "__main__":
  import struct # only for unit testing...
  valid_device="/dev/sdf"
  #valid mcb: 5a 00 3a 01 00 00 00 00 14 00

  valid_mcb=struct.pack(">BBBBBBBBBB", 0x5a, 0, 0x3a, 1, 0, 0, 0, 0, 0x14, 0 )
  dmp = DroboIOctl(valid_device,1,1)
  print dmp.version()
  hoho=dmp.get_sub_page(20,valid_mcb,0,4)
  print "hoho is ", len(hoho), " bytes long"
  # the 4 byte header on the returned sense buffer:  (122, 1, 20)
  # cfg:  (4, 16, 1099511557632)                                 

  #hexdump("hoho", hoho)
  fmt=">BBHBBBQBHH"
  print struct.calcsize(fmt)
  print struct.unpack(fmt,hoho)
  dmp.closefd()

