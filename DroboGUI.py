#!/usr/bin/python

#Drobo Utils Copyright (C) 2008  Peter Silva (Peter.A.Silva@gmail.com)
#Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
#named COPYING in the root of the source directory tree.
#

import os,sys,math
from PyQt4 import QtGui
from PyQt4 import QtCore
import socket
import Drobo
import subprocess
import commands
import string

def toGB(num):
  g = num*1.0/(1000*1000*1000)
  return "%6.1f" % g

def toTiB(num):
  """
  convert input number to computerish Terabytes.... (ok... TibiBytes blech...)

  STATUS: works bizarrely...
  bug in python 2.5? - a number which is 2 TB -1, + any number < 5000 ends up smaller than 2TiB.  so I just add 5000 to get the correct answer. did a manual binary search, and even 4096 doesn't work...
  """
  num=num+5000
  #print num, num/1024, num/(1024*1024), num/(1024*1024*1024)
  g = (num)/(1024*1024*1024*1024)
  return int(g)
 


def setDiskLabel(model,capacity): 
    if (capacity == ''):
      label = model
    else:
      if ( capacity > 0):
           label = model.rstrip() + '   ' + toGB(capacity) + 'GB '
      else:
	   label = 'empty'
    return label

partitioner=""

def runPartitioner():
   """ invoke existing partitioning program...
   """
   print "partitioner = ", partitioner
   subprocess.Popen( partitioner, shell=True)

class DroboAbout(QtGui.QWidget):
   def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.main = QtGui.QLabel("""
  drobo-utils: software to manage a Drobo 
  storage unit from Data Robotics 
  International Corp.

  http://drobo-utils.sourceforge.net

  Copyright 2008 Peter Silva
  ( Peter.A.Silva@gmail.com )

  license: General Public License (GPL) v3

  with Contributions from: 
     Chris Atlee (chris@atlee.ca)
     Brad Guillory, <withheld@spammenot.norge>
        """ , self)
        self.setMinimumSize(240, 240)
        self.quit = QtGui.QPushButton('Quit',self)
        self.quit.setCheckable(False)
        self.quit.setMinimumWidth(200)
        self.quit.move(30,200)
        self.connect(self.quit, QtCore.SIGNAL('clicked()'), 
                self.hide)
 


class DroboGUI(QtGui.QMainWindow):
    """ GUI for a single Drobo, start one for each drobo.
    """

    def __doButton(self,x,y,parent):
	""" create a disk display "button" ...
        """
        button = QtGui.QPushButton('uninitialized - 0000GB', parent)
        button.setCheckable(False)
        button.setMinimumWidth(200)
        button.setStyleSheet( "QWidget { background-color: white }" )
        button.move(x,y)
        #self.connect(button, QtCore.SIGNAL('focusInEvent()'), 
	#	self.__StatusBar_space)
        return button

    def __Blink(self):
        self.drobo.Blink()

    def __StatusBar_space(self):
        c=self.drobo.GetSubPageCapacity()
        self.statusmsg = 'used: ' + toGB(c[1]) + ' free: ' + toGB(c[0]) + ' Total: ' + toGB(c[2]) + ' GB, update# ' + str(self.updates)
	#print self.statusmsg
	
    def __updateLEDs(self):
        """ update LEDS (implement flashing.)
        """
        #if (self.Format.inProgress and self.Format.fstype == 'ext3'):
        #   if  self.fmt_process.poll() == None:
        #      line=self.fmt_process.stdout.readline()
        #      print 'format progress:',line

        self.updates = self.updates + 1 
        i=0
        while ( i < 4 ):
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
                   toGB(l[2]) + " total: " + toGB(l[1]) 
           if ( 'SUPPORTS_NEW_LUNINFO2' in self.drobo.features ):
                   lintooltip = luntooltip + " scheme: " + l[3] + " type: " + str(l[4]) + "\n"

        i=0
        while ( i < 4 ):
          self.Device.slot[i][0].setText(setDiskLabel(self.s[i][5],self.s[i][1]))
          self.Device.slot[i][0].setToolTip(luntooltip)
	  i=i+1

        c=self.drobo.GetSubPageConfig()
        self.Format.lunsize =  toTiB(c[2])

        c=self.drobo.GetSubPageCapacity()
        if c[2] > 0:
           self.Device.fullbar.setValue( c[1]*100/c[2] )
           self.Device.fullbar.setToolTip( 
	    "used: " + toGB(c[1]) + ' free: ' + toGB(c[0]) + ' Total: ' + toGB(c[2]) + ' GB, update# ' + str(self.updates) )
	#print self.statusmsg
        #self.__StatusBar_space()
        self.statusBar().showMessage( self.statusmsg )
        self.statusmsg = 'Status: ' + str(self.drobo.GetSubPageStatus()) + ' update: ' + str(self.updates)

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

    def __updateStatus(self):
        self.__updateLEDs() # only update display...

        # try not to poll the device too often, so only every 'n' screen updates
        if (self.updates % 5 == 0 ): # query device for new info...
	    self.__updatewithQueryStatus()


    def __initDeviceTab(self):

        self.Device = QtGui.QWidget()
        self.Device.setObjectName("Device")

        # Create Device tab...
        x=10
        y=30 
        yby=35

        self.Device.id =self.__doButton(x,y,self.Device)
        self.Device.id.setMinimumWidth(220)
 
        self.Device.slot = [ [ '', '' ], [ '', '' ], [ '', '' ], [ '', '' ] ]
        y=y+yby

        i=0
        while ( i < 4 ):
          self.Device.slot[i][0] =self.__doButton(x,y,self.Device)
          y=y+yby
          i=i+1

        x=x+210
        y=30+yby
        i=0
        while ( i < 4 ):
          self.Device.slot[i][1] = QtGui.QWidget(self.Device)
          self.Device.slot[i][1].setGeometry(x, y, 10, 30)
          y=y+yby
          i=i+1

        x=10
        self.Device.fullbar = QtGui.QProgressBar(self.Device)
        self.Device.fullbar.setGeometry(x, y, 230, 25)
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
        xo=20
        w=160
        h=16
        s=10

        x=10
        y=20
        self.Format.header = QtGui.QLabel("WARNING: Format erases whole Drobo", self.Format)
        self.Format.header.setStyleSheet( "QWidget { color: red }" )
        self.Format.header.move(x,y)

        x=xo
        y=y+h+s
        self.Format.lunsztitle = QtGui.QLabel("Maximum LUN size:", self.Format)
        self.Format.lunsztitle.move(x,y)

        self.Format.lunszlcd = QtGui.QLCDNumber(2, self.Format)

        x=x+120
        self.Format.lunszlcd.move(x,y)

 
        x=xo
        y=y+h+s

        self.Format.horizontalSlider = QtGui.QSlider(self.Format)
        self.Format.horizontalSlider.setGeometry(QtCore.QRect(x,y,w,h))
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
        self.Format.lunsize =  toTiB(c[2])
        self.Format.lunszlcd.display( self.Format.lunsize )
        self.Format.horizontalSlider.setValue( int(math.log(self.Format.lunsize,2)) )

        self.Format.connect(self.Format.horizontalSlider, QtCore.SIGNAL('valueChanged(int)'),
                self.__adjustlunsize)
        #self.Format.connect(self.Format.horizontalSlider, QtCore.SIGNAL('valueChanged(int)'),
        #        self.Format.lunszlcd.display)

        y=y+h+s
        self.Format.ext3 = QtGui.QRadioButton("Ext3 (journalled ext2)", self.Format)
        mkfs = commands.getoutput("which mke2fs")
        if ( mkfs == "" ): 
            self.Format.ext3.setCheckable(0)
            self.Format.ext3.setStyleSheet( "QWidget { color: gray }" )
            self.Format.ext3.setText('Ext3 disabled (missing mke2fs)')

        self.Format.ext3.move(x,y)

        y=y+h+s
        self.Format.msdos = QtGui.QRadioButton("FAT32 MS - Disk Operating System", self.Format)
        #self.Format.msdos.setStyleSheet( "QWidget { color: gray }" )
        mkfs = commands.getoutput("which mkdosfs")
        if ( mkfs == "" ): 
            self.Format.msdos.setCheckable(0)
            self.Format.msdos.setStyleSheet( "QWidget { color: gray }" )
            self.Format.msdos.setText('FAT32 disabled (missing mkdosfs)')

        self.Format.msdos.move(x,y)

        y=y+h+s
        self.Format.ntfs = QtGui.QRadioButton("NTFS -- Windows NT/XP/Vista", self.Format)
        #self.Format.ntfs.setStyleSheet( "QWidget { color: gray }" )
        self.Format.ntfs.move(x,y)

        mkfs = commands.getoutput("which mkntfs")
        if ( mkfs == "" ): 
            self.Format.ntfs.setCheckable(0)
            self.Format.ntfs.setStyleSheet( "QWidget { color: gray }" )
            self.Format.ntfs.setText('NTFS disabled (missing mkntfs)')

        y=y+h+s

        self.Format.Formatbutton = QtGui.QPushButton('Format (Erases All Data!)       ', self.Format)
        #self.Format.Formatbutton.setStyleSheet( "QWidget { color: gray }" )
        self.Format.Formatbutton.move(x,y)

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
        xo=20
        x=xo
        y=30
        w=160
        h=16
        s=10

        #
        # Set the tool colors to grey, to indicate non-functional...
        #
        self.Tools.Standbybutton = QtGui.QPushButton('Shutdown', self.Tools)
        self.Tools.Standbybutton.setCheckable(False)
        self.Tools.Standbybutton.move(x,y)

        self.connect(self.Tools.Standbybutton, QtCore.SIGNAL('clicked()'), 
                self.drobo.Standby)

	w=self.Tools.Standbybutton.width()
        x=x+w+s

        self.Tools.Blinkybutton = QtGui.QPushButton('Blink Lights', self.Tools)
        self.Tools.Blinkybutton.setCheckable(False)
        self.Tools.Blinkybutton.move(x,y)

        self.connect(self.Tools.Blinkybutton, QtCore.SIGNAL('clicked()'), 
                self.drobo.Blink)

        h=self.Tools.Standbybutton.height()
        x=xo
        y=y+h+s
        self.Tools.Renamebutton = QtGui.QPushButton('Rename', self.Tools)
        self.Tools.Renamebutton.setStyleSheet( "QWidget { color: gray }" )
        self.Tools.Renamebutton.setCheckable(False)
        self.Tools.Renamebutton.move(x,y)
        
        x=x+w+s
        self.Tools.Updatebutton = QtGui.QPushButton('Update', self.Tools)
        self.Tools.Updatebutton.move(x,y)

        self.connect(self.Tools.Updatebutton, QtCore.SIGNAL('clicked()'), self.checkup)


        x=xo
        y=y+h+s
        Registerbutton = QtGui.QPushButton('Register', self.Tools)
        Registerbutton.setStyleSheet( "QWidget { color: gray }" )
        Registerbutton.setCheckable(False)
        Registerbutton.move(x,y)

        x=x+w+s
        Diagbutton = QtGui.QPushButton('Diagnostics', self.Tools)
        Diagbutton.setCheckable(False)
        Diagbutton.move(x,y)

        self.connect(Diagbutton, QtCore.SIGNAL('clicked()'), 
                self.__diags)

        # next button...
        x=xo
        y=y+h+s

        self.Tools.progress = QtGui.QProgressBar(self.Tools)
        self.Tools.progress.setGeometry(x, y, 180, 25)
        self.Tools.progress.setValue( 0 )

        x=xo
        y=y+h+s

        self.Tools.comment = QtGui.QLabel("Press 'Update' to look for updates", self.Tools)
        self.Tools.comment.move(x,y)

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
        #QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('cleanlooks'))
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('MacStyle'))
        #self.setStyleSheet( "QWidget { border-color: white }" )
        #self.setStyleSheet( "QWidget { background-color: black }" )
        #self.setStyleSheet( "QWidget { color: white }" )

        #self.setGeometry(300, 100, 350, 260)
        self.setMinimumSize(240, 310)
        self.setWindowTitle('DroboView')
        self.setWindowIcon(QtGui.QIcon(':Drobo-Front-0000.gif'))

        exit = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))

        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(exit)

        #parted = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Manage Space', self)
        #parted.setShortcut('Ctrl+S')
        #parted.setStatusTip('Start up gparted Space Manager')
        #self.connect(parted, QtCore.SIGNAL('triggered()'), runPartitioner)
        #tools = menubar.addMenu('&Tools')
        #tools.addAction(parted)

        about = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'About DroboView', self)
        self.aboutdialog = DroboAbout()
        help = menubar.addMenu('&Help')
        help.addAction(about)
        self.connect(about, QtCore.SIGNAL('triggered()'), self.aboutdialog.show)

        self.tab = QtGui.QTabWidget(self)
	self.tab.setGeometry(QtCore.QRect(0,27,240,260))
        self.tab.setObjectName("tabs")
        
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

