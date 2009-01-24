
from ctypes import *

SG_DXFER_TO_DEV=-2
SG_DXFER_FROM_DEV=-3
SG_IO = 0x2285
SG_GET_VERSION_NUM = 0x2282

class sg_io_hdr(Structure):
  """

    do ioctl's using Linux generic SCSI interface.
    all of this comes from /usr/include/scsi/sg.h 

  """
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

