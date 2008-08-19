#!/usr/bin/python

#Drobo Utils Copyright (C) 2008  Peter Silva (Peter.A.Silva@gmail.com)
#Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
#named COPYING in the root of the source directory tree.
#

import sys
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
        fwv=self.drobo.GetSubPageFirmware()
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

        c=self.drobo.GetSubPageCapacity()
        if c[2] > 0:
           self.Device.fullbar.setValue( c[1]*100/c[2] )
        self.Device.fullbar.setToolTip( 
	    "used: " + toGB(c[1]) + ' free: ' + toGB(c[0]) + ' Total: ' + toGB(c[2]) + ' GB, update# ' + str(self.updates) )
	#print self.statusmsg
        #self.__StatusBar_space()
        self.statusBar().showMessage( self.statusmsg )
        self.statusmsg = 'Status: ' + str(self.drobo.GetSubPageStatus()) + ' update: ' + str(self.updates)

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



    def __initFormatTab(self):

	self.Format = QtGui.QWidget()
        self.Format.setObjectName("Format")
        self.Format.setStyleSheet( "QWidget { color: gray }" )
        xo=20
        w=160
        h=16
        s=10

        x=10
        y=30
        self.Format.header = QtGui.QLabel("WARNING: Format erases whole Drobo", self.Format)
        self.Format.header.setStyleSheet( "QWidget { color: red }" )
        self.Format.header.move(x,y)

        x=xo
        y=y+h+s
        self.Format.lunsztitle = QtGui.QLabel("Maximum LUN size on Drobo", self.Format)
        self.Format.lunsztitle.move(x,y)

        y=y+h+s
        self.Format.horizontalSlider = QtGui.QSlider(self.Format)
        self.Format.horizontalSlider.setGeometry(QtCore.QRect(x,y,w,h))
        self.Format.horizontalSlider.setMaximum(16)
        self.Format.horizontalSlider.setSingleStep(2)
        self.Format.horizontalSlider.setPageStep(9)
        self.Format.horizontalSlider.setProperty("value",QtCore.QVariant(2))
        self.Format.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.Format.horizontalSlider.setTickPosition(QtGui.QSlider.TicksBelow)
        self.Format.horizontalSlider.setTickInterval(2)
        self.Format.horizontalSlider.setObjectName("horizontalSlider")

        y=y+h+s
        self.Format.ext3 = QtGui.QRadioButton("Ext3 ", self.Format)
        self.Format.ext3.move(x,y)

        y=y+h+s
        self.Format.msdos = QtGui.QRadioButton("FAT32 (MS-DOS)", self.Format)
        self.Format.msdos.move(x,y)

        y=y+h+s
        self.Format.ntfs = QtGui.QRadioButton("NTFS", self.Format)
        self.Format.ntfs.move(x,y)

        y=y+h+s

        x=x+20
        Formatbutton = QtGui.QPushButton('Format', self.Format)
        Formatbutton.setCheckable(False)
        Formatbutton.move(x,y)

        self.tab.addTab(self.Format, "Format")
  
    def upgrade(self):
        if self.drobo.updateFirmwareRepository():
             self.drobo.writeFirmware( self.Tools.progress.setValue )
        self.Tools.comment.setText( "Written! Reboot Drobo to activate.")

    def checkup(self):
        self.drobo.Sync() # convenient side effect:  make the host and drobo clocks agree...
        (fwarch, fwversion, hwlevel, fwpath ) = self.drobo.PickLatestFirmware()
        print "checkup: this Drobo is a %s hw rev: %s, and needs: %s" % ( fwarch, hwlevel, fwversion )
        if fwpath != '' :
            self.Tools.Updatebutton.setText( "Upgrade" )
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
        Standbybutton = QtGui.QPushButton('Standby', self.Tools)
        Standbybutton.setCheckable(False)
        Standbybutton.move(x,y)

        self.connect(Standbybutton, QtCore.SIGNAL('clicked()'), 
                self.drobo.Standby)

	w=Standbybutton.width()
        x=x+w+s

        Blinkybutton = QtGui.QPushButton('Blink Lights', self.Tools)
        Blinkybutton.setCheckable(False)
        Blinkybutton.move(x,y)

        self.connect(Blinkybutton, QtCore.SIGNAL('clicked()'), 
                self.drobo.Blink)

        h=Standbybutton.height()
        x=xo
        y=y+h+s
        Renamebutton = QtGui.QPushButton('Rename', self.Tools)
        Renamebutton.setStyleSheet( "QWidget { color: gray }" )
        Renamebutton.setCheckable(False)
        Renamebutton.move(x,y)
        
        x=x+w+s
        self.Tools.Updatebutton = QtGui.QPushButton('Update', self.Tools)
        self.Tools.Updatebutton.move(x,y)

        self.connect(self.Tools.Updatebutton, QtCore.SIGNAL('clicked()'), 
                self.checkup)


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

        parted = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Manage Space', self)
        parted.setShortcut('Ctrl+S')
        parted.setStatusTip('Start up gparted Space Manager')
        self.connect(parted, QtCore.SIGNAL('triggered()'), runPartitioner)
        tools = menubar.addMenu('&Tools')
        tools.addAction(parted)

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


        # figure out which ever graphical sudo is available...
        gsudo = commands.getoutput("which gtksudo")
        if ( gsudo == "" ):
           gsudo = commands.getoutput("which kdesudo")
        partitioner= gsudo + " gparted"

