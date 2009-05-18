#!/usr/bin/python

#Drobo Utils Copyright (C) 2008,2009  Peter Silva (Peter.A.Silva@gmail.com)
#Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
#named COPYING in the root of the source directory tree.
#

#-------------------------------------------------------------------
# debugging stuff: begin
#-------------------------------------------------------------------

#import pdb


#------------------------------------------------------------------
# debugging stuff: end
#-------------------------------------------------------------------
import os,sys,math
from PyQt4 import QtGui
from PyQt4 import QtCore
import socket
import Drobo
import subprocess
import commands
import string

def _toGB(num):
  g = num*1.0/(1000*1000*1000)
  return "%6.1f" % g

def _toTiB(num):
  """
  convert input number to computerish Terabytes.... (ok... TibiBytes blech...)

  STATUS: works bizarrely...
  bug in python 2.5? - a number which is 2 TB -1, + any number < 5000 ends up smaller than 2TiB.  so at first I just added 5000 to get the correct answer. did a manual binary search, and even 4096 doesn't work... but when I change OS's, even that didn't workreliably...  so now I just round it at each division...
  """
  #print num, num/1024, num/(1024*1024), num/(1024*1024*1024), 
  g = round(round(round(round(num/1024)/1024)/1024)/1024)
  return int(g)
 


def _setDiskLabel(model,capacity): 
    if (capacity == ''):
      label = model
    else:
      if ( capacity > 0):
           label = model.rstrip() + '   ' + _toGB(capacity) + 'GB '
      else:
	   label = 'empty'
    return label

partitioner=""

def _runPartitioner():
   """ invoke existing partitioning program...
   """
   print "partitioner = ", partitioner
   subprocess.Popen( partitioner, shell=True)

class DroboAbout(QtGui.QWidget):
   def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setMinimumSize(240, 240)
        al = QtGui.QVBoxLayout(self)
        self.main = QtGui.QLabel("""
  drobo-utils: software to manage a Drobo storage unit from Data Robotics International Corp.
  Winner of the Data Robotics Bounty 2008 for a linux dashboard!  
  Home page:  http://drobo-utils.sourceforge.net

  Version: """ + Drobo.VERSION + """ 
  Copyright 2008 Peter Silva ( Peter.A.Silva@gmail.com )
  license: General Public License (GPL) v3

  with contributions from: Chris Atlee (chris@atlee.ca), Brad Guillory, <withheld@spammenot.norge> 
  and inspiration from: Joe Krahn

  and thanks for DRI for putting up the Bounty!
        """ , self)
        al.addWidget(self.main)
        self.quit = QtGui.QPushButton('Quit',self)
        al.addWidget(self.quit)
        #self.quit.setCheckable(False)
        #self.quit.setMinimumWidth(200)
        #self.quit.move(-30,-100)
        self.connect(self.quit, QtCore.SIGNAL('clicked()'), 
                self.hide)
 


class DroboGUI(QtGui.QMainWindow):
    """ GUI for a single Drobo, start one for each drobo.
    """

    def __Blink(self):
        self.drobo.Blink()

    def __StatusBar_space(self):
        c=self.drobo.GetSubPageCapacity()
        self.statusmsg = 'used: ' + _toGB(c[1]) + ' free: ' + _toGB(c[0]) + ' Total: ' + _toGB(c[2]) + ' GB, update# ' + str(self.updates)
	#print self.statusmsg
	
    def __updateLEDs(self):
        """ update LEDS (implement flashing.)
        """

        self.updates = self.updates + 1 
        i=0
        while ( i < self.drobo.SlotCount() ):
          c=self.s[i][3]
          if (len(c) == 2 ):  
             colour = c[ self.updates % 2] 
          else:
	     colour = c

          self.Device.slot[i][1].setStyleSheet(
                "QWidget { background-color: %s }" % colour )
	  i=i+1


    def __updatewithQueryStatus(self):
        """ query device to update information
        """
        try:
           fwv=self.drobo.GetSubPageFirmware()
        except:
           self.statusBar().showMessage( 'bad poll: %d.. need to restart' % self.updates )
           return

        settings=self.drobo.GetSubPageSettings()
        self.Device.id.setText(  self.drobo.GetCharDev() + ' firmware: ' + fwv[7] )

        self.Device.id.setToolTip(
           "Firmware build: " + str(fwv[0]) + '.' + str(fwv[1]) + '.' + str(fwv[2]) + "\n Features: " + string.join(fwv[8],"\n") )
        
        self.s=self.drobo.GetSubPageSlotInfo()

        luninfo=self.drobo.GetSubPageLUNs()

        luntooltip="luns, count: " + str(len(luninfo)) + "\n"
        for l in luninfo:
	   luntooltip = luntooltip + "lun id: " + str(l[0]) + " used: " +  \
                   _toGB(l[2]) + " total: " + _toGB(l[1]) 
           if 'SUPPORTS_NEW_LUNINFO2' in self.drobo.features :
              luntooltip = luntooltip + " scheme: " + l[3] + " type: " + str(l[4]) 
           luntooltip = luntooltip + "\n"

        i=0
        mnw=0
        while i < self.drobo.SlotCount() :
          self.Device.slot[i][0].setText(_setDiskLabel(self.s[i][5],self.s[i][1]))
          w= self.Device.slot[i][0].width()
          if w > mnw:
               mnw=w
          self.Device.slot[i][0].setToolTip(luntooltip)
	  i=i+1

        i=0
        while i < self.drobo.SlotCount() :
          self.Device.slot[i][0].setMinimumWidth(mnw)
	  i=i+1

        self.Device.fullbar.setMinimumWidth(mnw+20)
        self.Device.id.setMinimumWidth(mnw+20)
	#self.tab.setGeometry(QtCore.QRect(0,27,mnw+40,300))

        c=self.drobo.GetSubPageConfig()
        self.Format.lunsize =  _toTiB(c[2])

        c=self.drobo.GetSubPageCapacity()
        if c[2] > 0:
           self.Device.fullbar.setValue( c[1]*100/c[2] )
           self.Device.fullbar.setToolTip( 
	    "used: " + _toGB(c[1]) + ' free: ' + _toGB(c[0]) + ' Total: ' + _toGB(c[2]) + ' GB, update# ' + str(self.updates) )
	#print self.statusmsg
        #self.__StatusBar_space()
        self.statusBar().showMessage( self.statusmsg )
        ss = self.drobo.GetSubPageStatus()
        self.statusmsg = 'Status: ' + str(ss[0]) + ' update: ' + str(self.updates)

        if self.Format.inProgress and ( self.fmt_process.poll() != None) :
               # reset to normal state...
               print 'it took: %d updates to run' % (self.updates - self.Format.startupdate )
               self.Format.inProgress=0
               normal = self.Tools.Updatebutton.palette().color( QtGui.QPalette.Button )
               self.Format.Formatbutton.palette().setColor( QtGui.QPalette.Button, QtCore.Qt.blue )
               self.Format.ext3.setChecked(0)
               self.Format.ntfs.setChecked(0)
               self.Format.msdos.setChecked(0)
               self.Format.Formatbutton.setText('Format Done!')
               self.Format.connect(self.Format.Formatbutton, QtCore.SIGNAL('clicked()'),
                       self.FormatLUN)
        #pdb.set_trace()

    def __updateStatus(self):
        self.__updateLEDs() # only update display...

        # try not to poll the device too often, so only every 'n' screen updates
        if (self.updates % 5 == 0 ): # query device for new info...
	    self.__updatewithQueryStatus()


    def __initDeviceTab(self):

        self.Device = QtGui.QWidget()
        self.Device.setObjectName("Device")

        # Create Device tab...
        devtablayout=QtGui.QGridLayout(self.Device)
        devtablayout.setColumnStretch(0,9)
        devtablayout.setColumnStretch(1,1)
        self.Device.id = QtGui.QPushButton('Unknown Drobo', self.Device)
        self.Device.id.setCheckable(False)
        self.Device.id.setStyleSheet( "QWidget { background-color: white }" )
        #self.Device.id.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding )

        devtablayout.addWidget(self.Device.id,0,0,1,-1,QtCore.Qt.AlignLeft)
     
        self.Device.slot = [ [ '', '' ], [ '', '' ], [ '', '' ], [ '', '' ],
                             [ '', '' ], [ '', '' ], [ '', '' ], [ '', '' ]  ]

        i=0
        while ( i < self.drobo.SlotCount() ):
          slotlayout=QtGui.QHBoxLayout()
          self.Device.slot[i][0] = QtGui.QPushButton('uninitialized - 0000GB', self.Device)
          self.Device.slot[i][0].setCheckable(False)
          self.Device.slot[i][0].setMinimumWidth(200)
          self.Device.slot[i][0].setStyleSheet( "QWidget { background-color: white }" )
          devtablayout.addWidget(self.Device.slot[i][0],i+1,0,1,1,QtCore.Qt.AlignLeft)
          self.Device.slot[i][1] = QtGui.QWidget(self.Device)
          self.Device.slot[i][1].setMinimumWidth(10)
          self.Device.slot[i][1].setMinimumHeight(30)

          devtablayout.addWidget(self.Device.slot[i][1],i+1,1,1,1,QtCore.Qt.AlignLeft)
          devtablayout.setRowMinimumHeight(i+1,10)
          i=i+1

        self.Device.fullbar = QtGui.QProgressBar(self.Device)
        self.Device.fullbar.setMinimumWidth(230)
        devtablayout.addWidget(self.Device.fullbar,i+1,0,1,2,QtCore.Qt.AlignLeft)
        self.connect(self.Device.fullbar, QtCore.SIGNAL('focusInEvent()'), 
		self.__StatusBar_space)

        self.tab.addTab(self.Device, "Device")

    def ReallyFormatLUN(self):

       print 'Really formatting...'
       self.Format.disconnect(self.Format.Formatbutton, QtCore.SIGNAL('clicked()'),
                self.ReallyFormatLUN)
       if self.Format.fstype == 'none': # changing LUN size
            self.Format.Formatbutton.setText('Done. WAIT 5 min. restart dashboard!')
            self.drobo.SetLunSize(self.Format.lunszlcd.value())
       else:
            self.Format.Formatbutton.setText('Format in progress, WAIT!')
            format_script = self.drobo.format_script(self.Format.fstype)
            self.Format.startupdate = self.updates
            self.Format.inProgress = 1;
            #self.fmt_process = subprocess.Popen( format_script, bufsize=0, stdout=subprocess.PIPE )
            self.fmt_process = subprocess.Popen( format_script )
            p = self.Format.Formatbutton.palette()
            p.setColor( QtGui.QPalette.Button, QtCore.Qt.red )




    def FormatLUN(self):
       print 'Clicked format...'
       if self.Format.ntfs.isChecked():
            fstype='ntfs'
       elif self.Format.msdos.isChecked():
            fstype='FAT32'
       elif self.Format.ext3.isChecked():
            fstype='ext3'
       else:
            fstype='none'
            self.Format.Formatbutton.palette().setColor( QtGui.QPalette.Button, QtCore.Qt.yellow )
            self.Format.Formatbutton.setText( \
                  "Last Chance, Resize to %d TiB" % self.Format.lunszlcd.value() )

       if fstype != 'none':
          self.Format.Formatbutton.palette().setColor( QtGui.QPalette.Button, QtCore.Qt.yellow )
          self.Format.Formatbutton.setText( "Last Chance, Format %s ?" % fstype)

       self.Format.fstype=fstype
       self.Format.disconnect(self.Format.Formatbutton, QtCore.SIGNAL('clicked()'),
                self.FormatLUN)
       self.Format.connect(self.Format.Formatbutton, QtCore.SIGNAL('clicked()'),
                self.ReallyFormatLUN)

    def __adjustlunsize(self,sz):

        newsize=2**sz
        self.Format.lunszlcd.display(newsize)
        if ( self.Format.lunsize != newsize ):
            self.Format.fstype= 'none'
            self.Format.ext3.setChecked(False)
            self.Format.ext3.setCheckable(False)
            self.Format.msdos.setChecked(False)
            self.Format.msdos.setCheckable(False)
            self.Format.ntfs.setChecked(False)
            self.Format.ntfs.setCheckable(False)
            self.Format.Formatbutton.setText( "Set LUN size to %d TiB" % newsize)
        else:
            self.Format.ext3.setCheckable(True)
            self.Format.msdos.setCheckable(True)
            self.Format.ntfs.setCheckable(True)
            self.Format.Formatbutton.setText( "Format (Erases All Data!)         " )


    def __initFormatTab(self):
        """
          known issues:
           -- formats only using GPT labels... should be mbr for FAT32.
           -- should refuse to set lunsize > 2 TB for FAT32.
           -- should refuse to set lunsize > 8 TB for ext3.

        """

	self.Format = QtGui.QWidget()
        self.Format.setObjectName("Format")
        w=160

        flay = QtGui.QGridLayout(self.Format)
        flay.setColumnMinimumWidth(0,240)

        self.Format.header = QtGui.QLabel("WARNING: Format erases whole Drobo", self.Format)
        self.Format.header.setStyleSheet( "QWidget { color: red }" )
        self.Format.header.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding )
        flay.addWidget(self.Format.header,0,0,1,2,QtCore.Qt.AlignLeft)

        self.Format.lunsztitle = QtGui.QLabel("Maximum LUN size:", self.Format)
        flay.addWidget(self.Format.lunsztitle,1,0,1,1,QtCore.Qt.AlignLeft)
        self.Format.lunsztitle.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed )

        self.Format.lunszlcd = QtGui.QLCDNumber(2, self.Format)
        flay.addWidget(self.Format.lunszlcd,1,1,1,1,QtCore.Qt.AlignLeft)

        self.Format.horizontalSlider = QtGui.QSlider(self.Format)
        #self.Format.horizontalSlider.setGeometry(QtCore.QRect(x,y,w,h))
        self.Format.horizontalSlider.setMinimumWidth(w)
        flay.addWidget(self.Format.horizontalSlider,2,0,1,2,QtCore.Qt.AlignLeft)
        self.Format.horizontalSlider.setMaximum(4)
        self.Format.horizontalSlider.setMinimum(0)
        self.Format.horizontalSlider.setSingleStep(1)
        self.Format.horizontalSlider.setPageStep(2)
        self.Format.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.Format.horizontalSlider.setTickPosition(QtGui.QSlider.TicksBelow)
        self.Format.horizontalSlider.setTickInterval(1)
        self.Format.horizontalSlider.setObjectName("horizontalSlider")

        self.Format.horizontalSlider.setProperty("value",QtCore.QVariant(2))
        c=self.drobo.GetSubPageConfig()
        self.Format.lunsize =  _toTiB(c[2])
        self.Format.lunszlcd.display( self.Format.lunsize )
        self.Format.horizontalSlider.setValue( int(math.log(self.Format.lunsize,2)) )

        self.Format.connect(self.Format.horizontalSlider, QtCore.SIGNAL('valueChanged(int)'),
                self.__adjustlunsize)

        self.Format.ext3 = QtGui.QRadioButton("Ext3 (journalled ext2)", self.Format)
        mkfs = commands.getoutput("which mke2fs")
        if mkfs == "" : 
            self.Format.ext3.setCheckable(0)
            self.Format.ext3.setStyleSheet( "QWidget { color: gray }" )
            self.Format.ext3.setText('Ext3 disabled (missing mke2fs)')

        flay.addWidget(self.Format.ext3,3,0,1,-1,QtCore.Qt.AlignLeft)

        self.Format.msdos = QtGui.QRadioButton("FAT32 MS - Disk Operating System", self.Format)
        #self.Format.msdos.setStyleSheet( "QWidget { color: gray }" )
        mkfs = commands.getoutput("which mkdosfs")
        if ( mkfs == "" ): 
            self.Format.msdos.setCheckable(0)
            self.Format.msdos.setStyleSheet( "QWidget { color: gray }" )
            self.Format.msdos.setText('FAT32 disabled (missing mkdosfs)')

        flay.addWidget(self.Format.msdos,4,0,1,-1,QtCore.Qt.AlignLeft)

        self.Format.ntfs = QtGui.QRadioButton("NTFS -- Windows NT/XP/Vista", self.Format)
        flay.addWidget(self.Format.ntfs,5,0,1,-1,QtCore.Qt.AlignLeft)

        mkfs = commands.getoutput("which mkntfs")
        if ( mkfs == "" ): 
            self.Format.ntfs.setCheckable(0)
            self.Format.ntfs.setStyleSheet( "QWidget { color: gray }" )
            self.Format.ntfs.setText('NTFS disabled (missing mkntfs)')


        self.Format.Formatbutton = QtGui.QPushButton('Format (Erases All Data!)       ', self.Format)
        flay.addWidget(self.Format.Formatbutton,6,0,1,-1,QtCore.Qt.AlignLeft)

        self.tab.addTab(self.Format, "Format")

        self.Format.connect(self.Format.Formatbutton, QtCore.SIGNAL('clicked()'),
                self.FormatLUN)

        # progress flag...
        self.Format.inProgress = 0


    def upgrade(self):
        self.disconnect(self.Tools.Updatebutton, QtCore.SIGNAL('clicked()'), self.upgrade)
        self.connect(self.Tools.Updatebutton, QtCore.SIGNAL('clicked()'), self.checkup)

        if self.drobo.updateFirmwareRepository():
             self.drobo.writeFirmware( self.Tools.progress.setValue )
        self.Tools.comment.setText( "Written! Reboot Drobo to activate.")

    def checkup(self):
        self.drobo.Sync() # convenient side effect:  make the host and drobo clocks agree...
        (fwarch, fwversion, hwlevel, fwpath ) = self.drobo.PickLatestFirmware()
        print "checkup: this Drobo is a %s hw rev: %s, and needs: %s" % ( fwarch, hwlevel, fwversion )
        if fwpath != '' :
            self.Tools.Updatebutton.setText( "Upgrade" )
            self.disconnect(self.Tools.Updatebutton, QtCore.SIGNAL('clicked()'), self.checkup)
            self.connect(self.Tools.Updatebutton, QtCore.SIGNAL('clicked()'), 
                self.upgrade)
            self.Tools.comment.setText( "Press 'Upgrade' upgrade to %s" % ( fwversion ))
        else:
            self.Tools.comment.setText( "No update available!" )
     
        
    def __diags(self):
        self.drobo.Sync() # convenient side effect  make the host and drobo clocks agree...
        fname = self.drobo.dumpDiagnostics()
        self.Tools.comment.setText( fname )

    def __initToolTab(self):

	self.Tools = QtGui.QWidget()
        self.Tools.setObjectName("Tools")

        tlay = QtGui.QGridLayout(self.Tools)
        #
        # Set the tool colors to grey, to indicate non-functional...
        #
        self.Tools.Standbybutton = QtGui.QPushButton('Shutdown', self.Tools)
        self.Tools.Standbybutton.setCheckable(False)
        #self.Tools.Standbybutton.move(x,y)
        tlay.addWidget(self.Tools.Standbybutton,0,0,1,1,QtCore.Qt.AlignLeft)

        self.connect(self.Tools.Standbybutton, QtCore.SIGNAL('clicked()'), 
                self.drobo.Standby)

	w=self.Tools.Standbybutton.width()

        self.Tools.Blinkybutton = QtGui.QPushButton('Blink Lights', self.Tools)
        self.Tools.Blinkybutton.setCheckable(False)
        tlay.addWidget(self.Tools.Blinkybutton,0,1,1,1,QtCore.Qt.AlignLeft)

        self.connect(self.Tools.Blinkybutton, QtCore.SIGNAL('clicked()'), 
                self.drobo.Blink)

        self.Tools.Renamebutton = QtGui.QPushButton('Rename', self.Tools)
        self.Tools.Renamebutton.setStyleSheet( "QWidget { color: gray }" )
        self.Tools.Renamebutton.setCheckable(False)
        tlay.addWidget(self.Tools.Renamebutton,1,0,1,1,QtCore.Qt.AlignLeft)
        
        self.Tools.Updatebutton = QtGui.QPushButton('Update', self.Tools)
        tlay.addWidget(self.Tools.Updatebutton,1,1,1,1,QtCore.Qt.AlignLeft)

        self.connect(self.Tools.Updatebutton, QtCore.SIGNAL('clicked()'), self.checkup)

        Registerbutton = QtGui.QPushButton('Register', self.Tools)
        Registerbutton.setStyleSheet( "QWidget { color: gray }" )
        Registerbutton.setCheckable(False)
        tlay.addWidget(Registerbutton,2,0,1,1,QtCore.Qt.AlignLeft)

        Diagbutton = QtGui.QPushButton('Diagnostics', self.Tools)
        Diagbutton.setCheckable(False)
        tlay.addWidget(Diagbutton,2,1,1,1,QtCore.Qt.AlignLeft)

        self.connect(Diagbutton, QtCore.SIGNAL('clicked()'), 
                self.__diags)

        self.Tools.progress = QtGui.QProgressBar(self.Tools)
        #self.Tools.progress.setGeometry(x, y, 180, 25)
        self.Tools.progress.setMinimumWidth(2*w)
        tlay.addWidget(self.Tools.progress,3,0,1,1,QtCore.Qt.AlignLeft)
        self.Tools.progress.setValue( 0 )

        self.Tools.comment = QtGui.QLabel("Press 'Update' to look for updates", self.Tools)
        tlay.addWidget(self.Tools.comment,4,0,1,2,QtCore.Qt.AlignLeft)

        normal = self.Tools.Updatebutton.palette().color( QtGui.QPalette.Button )

        self.tab.addTab(self.Tools, "Tools")


    def __init__(self, d, parent=None):
        QtGui.QMainWindow.__init__(self)
        #QtGui.QWidget.__init__(self, parent)

	global partitioner

        self.drobo = d
        self.updates = 0

        self.statusmsg='Ready'
        self.color = QtGui.QColor(0, 0, 0) 
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('MacStyle'))

        #self.setGeometry(300, 100, 350, 260)
        self.setMinimumSize(320, 350)
        self.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding )
        self.setWindowTitle('DroboView')
        self.setWindowIcon(QtGui.QIcon(':Drobo-Front-0000.gif'))

        exit = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))

        #mlay = QtGui.QVBoxLayout(self)
        menubar = self.menuBar()
        #self.addWidget(menubar)
        file = menubar.addMenu('&File')
        file.addAction(exit)

        about = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'About DroboView', self)
        self.aboutdialog = DroboAbout()
        help = menubar.addMenu('&Help')
        help.addAction(about)
        self.connect(about, QtCore.SIGNAL('triggered()'), self.aboutdialog.show)

        self.tab = QtGui.QTabWidget(self)
        #self.setCentralWidget(self.tab)
        #self.addWidget(self.tab)
        self.tab.setMinimumWidth(300)
        self.tab.setMinimumHeight(300)
	self.tab.setGeometry(QtCore.QRect(0,27,300,300))
        #self.tab.setObjectName("tabs")
        
	self.__initDeviceTab()
	self.__initToolTab()
	self.__initFormatTab()

	self.__updatewithQueryStatus()
        self.updateTimer = QtCore.QTimer(self)
        self.connect(self.updateTimer, QtCore.SIGNAL("timeout()"),
		self.__updateStatus )
        self.updateTimer.setInterval(1000)
        self.updateTimer.start()

        partitioner= " gparted"

