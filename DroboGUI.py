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
  Winner of the Data Robotics Incorporated (DRI) Bounty 2008 for a linux dashboard!  
  Thanks tor RI for putting up the Bounty!

  Copyright 2008 Peter Silva ( Peter.A.Silva@gmail.com )
  license: General Public License (GPL) v3
  Version: """ + Drobo.VERSION + """ 

  See README for other contributors.
        """ , self)
        al.addWidget(self.main)
        self.quit = QtGui.QPushButton('Dismiss',self)
        al.addWidget(self.quit)
        self.connect(self.quit, QtCore.SIGNAL('clicked()'), self.hide)
 
class ShowText(QtGui.QWidget):


   def __init__(self, manual, isfile=True, parent=None):

      QtGui.QWidget.__init__(self, parent)
      self.setMinimumSize(500, 440)
      al = QtGui.QVBoxLayout(self)

      # search support... buggy.
      #self.lastsearch=''
      #self.lscursor=QtGui.QTextCursor(self)
      #self.lscursor.setPosition(0)

      if isfile:
        dirs=[ "/usr/local/share/drobo-utils-doc", "/usr/share/drobo-utils/share/drobo-utils-doc", "." ]
        readme=""
        i=0
        while (i < 3 ) and (readme == "") :
          try: 
            readmefile = open( dirs[i] + "/" + manual )
            readme = readmefile.read()
            readmefile.close()
          except:
            pass

          i=i+1

        if i >= 3:
          readme = "Documentation %s not found" % manual

        self.main = QtGui.QTextEdit(readme, self )
      else:
        self.main = QtGui.QTextEdit('', self )
        self.main.setPlainText(manual)

        
      al.addWidget(self.main)
      self.quit = QtGui.QPushButton('Dismiss',self)
      al.addWidget(self.quit)
      self.connect(self.quit, QtCore.SIGNAL('clicked()'), self.hide)

      #self.findbt = QtGui.QPushButton('Find',self)
      #al.addWidget(self.findbt)
      #self.connect(self.findbt, QtCore.SIGNAL('clicked()'), self.__search)


   def __search(self):
        """
         search is for finding a string in a text document being displayed.
         STATUS: totally borked.
        """
        text, ok = QtGui.QInputDialog.getText(self, self.tr("Search Text"),
                                              self.tr("Look for:"), QtGui.QLineEdit.Normal,
                                              self.lastsearch)
        if ok and not text.isEmpty():
            self.lastsearch = QtCore.QString(text)
	    self.lscursor = self.find(self.lastsearch,0)
            self.lscursor.setPosition(0)

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
        self.Device.id.setText(  self.drobo.GetCharDev() + ' ' + settings[2] + ' firmware: ' + fwv[7] )

        self.Device.id.setToolTip(
           "Firmware build: " + str(fwv[0]) + '.' + str(fwv[1]) + '.' + str(fwv[2]) + "\n Features: " + string.join(fwv[8],"\n") )
        
        self.s=self.drobo.GetSubPageSlotInfo()

        luninfo=self.drobo.GetSubPageLUNs()

        luntooltip="luns, count: " + str(len(luninfo)) + "\n"
        for l in luninfo:
	   luntooltip = luntooltip + "lun id: " + str(l[0]) + " used: " +  \
                   _toGB(l[2]) + " total: " + _toGB(l[1]) 
           if 'SUPPORTS_NEW_LUNINFO2' in self.drobo.features :
              luntooltip = luntooltip + " scheme: " + str(l[3]) + " type: " + str(l[4]) 
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

        c=self.drobo.GetSubPageConfig()
        self.Format.lunsize =  _toTiB(c[2])

        c=self.drobo.GetSubPageCapacity()
        if c[2] > 0:
           self.Device.fullbar.setValue( c[1]*100/c[2] )
           self.Device.fullbar.setToolTip(  string.join(self.drobo.DiscoverMounts(),',') +
	    "\nused: " + _toGB(c[1]) + ' free: ' + _toGB(c[0]) + ' Total: ' + _toGB(c[2]) + ' GB, update# ' + str(self.updates) )
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
               self.Format.connect(self.Format.Formatbutton, \
                     QtCore.SIGNAL('clicked()'), self.FormatLUN)
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
        devtablayout.setColumnStretch(0,19)
        devtablayout.setColumnStretch(1,1)
        devtablayout.setVerticalSpacing(4)

        self.Device.id = QtGui.QPushButton('Unknown Drobo', self.Device)
        self.Device.id.setCheckable(False)
        self.Device.id.setStyleSheet( "QWidget { background-color: white }" )
        #self.Device.id.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding )

        devtablayout.addWidget(self.Device.id,0,0,1,-1)
     
        self.Device.slot = [ [ '', '' ], [ '', '' ], [ '', '' ], [ '', '' ],
                             [ '', '' ], [ '', '' ], [ '', '' ], [ '', '' ]  ]

        i=0
        while ( i < self.drobo.SlotCount() ):
          slotlayout=QtGui.QHBoxLayout()
          self.Device.slot[i][0] = QtGui.QPushButton('uninitialized - 0000GB', self.Device)
          self.Device.slot[i][0].setCheckable(False)
          self.Device.slot[i][0].setStyleSheet( "QWidget { background-color: white }" )
          self.Device.slot[i][0].setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding )
          devtablayout.addWidget(self.Device.slot[i][0],i+1,0,1,1)
          self.Device.slot[i][1] = QtGui.QWidget(self.Device)
          self.Device.slot[i][1].setMinimumWidth(10)

          devtablayout.addWidget(self.Device.slot[i][1],i+1,1,1,1)
          i=i+1

        self.Device.fullbar = QtGui.QProgressBar(self.Device)
        devtablayout.addWidget(self.Device.fullbar,i+1,0,1,-1)
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
            if ( self.Format.lunszlcd.value() == self.Format.lunsize ):
                 return

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

        # This crap is here only because of firmware broken for large LUNS
        #   please remove the whole if mess once the firmware gets fixed.
        if ( sz > 1 ):
           # force down to 2 TiB
           newsize=2
           self.Format.lunsize = newsize 
           self.Format.lunszlcd.display( newsize )
           self.Format.horizontalSlider.setValue( 1 )
           self.__adjustlunsize(1)
           self.Format.Formatbutton.setText( "Sorry, only upto %d TiB on Linux" % newsize )
           return

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

        flay = QtGui.QGridLayout(self.Format)

        self.Format.header = QtGui.QLabel("WARNING: Format erases whole Drobo", self.Format)
        self.Format.header.setStyleSheet( "QWidget { color: red }" )
        flay.addWidget(self.Format.header,0,0,1,2)

        self.Format.lunsztitle = QtGui.QLabel("Maximum LUN size:", self.Format)
        flay.addWidget(self.Format.lunsztitle,1,0,1,1)
        self.Format.lunsztitle.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed )

        self.Format.lunszlcd = QtGui.QLCDNumber(2, self.Format)
        flay.addWidget(self.Format.lunszlcd,1,1,1,1)

        self.Format.horizontalSlider = QtGui.QSlider(self.Format)
        flay.addWidget(self.Format.horizontalSlider,2,0,1,2)
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
        if self.Format.lunsize > 1:
           self.Format.horizontalSlider.setValue( int(math.log(self.Format.lunsize,2)) )
        else:
           self.Format.horizontalSlider.setValue(0) 

        self.Format.connect(self.Format.horizontalSlider, QtCore.SIGNAL('valueChanged(int)'),
                self.__adjustlunsize)

        self.Format.ext3 = QtGui.QRadioButton("Ext3 (journalled ext2)", self.Format)
        mkfs = commands.getoutput("which mke2fs")
        if mkfs == "" : 
            self.Format.ext3.setCheckable(0)
            self.Format.ext3.setStyleSheet( "QWidget { color: gray }" )
            self.Format.ext3.setText('Ext3 disabled (missing mke2fs)')

        flay.addWidget(self.Format.ext3,3,0,1,-1)

        self.Format.msdos = QtGui.QRadioButton("FAT32 MS - Disk Operating System", self.Format)
        mkfs = commands.getoutput("which mkdosfs")
        if ( mkfs == "" ): 
            self.Format.msdos.setCheckable(0)
            self.Format.msdos.setStyleSheet( "QWidget { color: gray }" )
            self.Format.msdos.setText('FAT32 disabled (missing mkdosfs)')

        flay.addWidget(self.Format.msdos,4,0,1,-1)

        self.Format.ntfs = QtGui.QRadioButton("NTFS -- Windows NT/XP/Vista", self.Format)
        flay.addWidget(self.Format.ntfs,5,0,1,-1)

        mkfs = commands.getoutput("which mkntfs")
        if ( mkfs == "" ): 
            self.Format.ntfs.setCheckable(0)
            self.Format.ntfs.setStyleSheet( "QWidget { color: gray }" )
            self.Format.ntfs.setText('NTFS disabled (missing mkntfs)')


        self.Format.Formatbutton = QtGui.QPushButton('Format (Erases All Data!)       ', self.Format)
        self.Format.Formatbutton.setToolTip("Configure a Drobo for use")
        flay.addWidget(self.Format.Formatbutton,6,0,1,-1)

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
        self.last_diagfile = fname
        self.Tools.comment.setText( fname )

 
    def __printDiagFile(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self,
                                         self.tr("QFileDialog.getOpenFileName()"),
                                         self.last_diagfile,
                                         self.tr("All Files (*);;Text Files (*.txt)"))
        if not fileName.isEmpty():
            datam =self.drobo.decodeDiagnostics(str(fileName))
            self.diagdialog = ShowText(datam,False)
            self.diagdialog.show()

    def __loadFirmware(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self,
                                         self.tr("QFileDialog.getOpenFileName()"),
                                         self.drobo.localFirmwareRepository(),
                                         self.tr("All Files (*);;Text Files (*.txt)"))
        if not fileName.isEmpty():
          if self.drobo.PickFirmware(str(fileName)):
             self.drobo.writeFirmware( self.Tools.progress.setValue )
	  

    def __renameDialog(self):

        settings=self.drobo.GetSubPageSettings()
        text, ok = QtGui.QInputDialog.getText(self, self.tr("QInputDialog.getText()"),
                                              self.tr("New name:"), QtGui.QLineEdit.Normal,
                                              settings[2])
        if ok and not text.isEmpty():
            self.drobo.Sync(str(text)) # convenient side effect:  make the host and drobo clocks agree...


    def __initToolTab(self):

	self.Tools = QtGui.QWidget()
        self.Tools.setObjectName("Tools")

        tlay = QtGui.QGridLayout(self.Tools)
        #
        # Set the tool colors to grey, to indicate non-functional...
        #
        self.Tools.Standbybutton = QtGui.QPushButton('Shutdown', self.Tools)
        self.Tools.Standbybutton.setToolTip( 'Unmount file systems, and turn Drobo off (DRI calls this standby)' )
        self.Tools.Standbybutton.setCheckable(False)
        tlay.addWidget(self.Tools.Standbybutton,0,0,1,1)

        self.connect(self.Tools.Standbybutton, QtCore.SIGNAL('clicked()'), 
                self.drobo.Standby)

	w=self.Tools.Standbybutton.width()

        self.Tools.Blinkybutton = QtGui.QPushButton('Blink Lights', self.Tools)
        self.Tools.Blinkybutton.setToolTip( 'Make a light show (totally harmless)' )
        self.Tools.Blinkybutton.setCheckable(False)
        tlay.addWidget(self.Tools.Blinkybutton,0,1,1,1)

        self.connect(self.Tools.Blinkybutton, QtCore.SIGNAL('clicked()'), 
                self.drobo.Blink)

        self.Tools.Renamebutton = QtGui.QPushButton('Rename', self.Tools)
        self.Tools.Renamebutton.setToolTip( "Change the Drobo's name (does not affect mount points.)" )
        self.Tools.Renamebutton.setCheckable(False)
        tlay.addWidget(self.Tools.Renamebutton,1,0,1,1)
        self.connect(self.Tools.Renamebutton, QtCore.SIGNAL('clicked()'), self.__renameDialog)
        
        self.Tools.Updatebutton = QtGui.QPushButton('Update', self.Tools)
        self.Tools.Updatebutton.setToolTip( "See if new firmware is available." )
        tlay.addWidget(self.Tools.Updatebutton,1,1,1,1)

        self.connect(self.Tools.Updatebutton, QtCore.SIGNAL('clicked()'), self.checkup)

        Registerbutton = QtGui.QPushButton('Register', self.Tools)
        Registerbutton.setToolTip( "Report for warranty service." )
        Registerbutton.setStyleSheet( "QWidget { color: gray }" )
        Registerbutton.setCheckable(False)
        tlay.addWidget(Registerbutton,2,0,1,1)

        Diagbutton = QtGui.QPushButton('Diagnostics', self.Tools)
        Diagbutton.setToolTip( "Have Drobo write a diagnostics file to /tmp" )
        Diagbutton.setCheckable(False)
        tlay.addWidget(Diagbutton,2,1,1,1)
        self.connect(Diagbutton, QtCore.SIGNAL('clicked()'), self.__diags)

        DiagShowbutton = QtGui.QPushButton('Show Diag', self.Tools)
        DiagShowbutton.setToolTip( "Show a decoded diagnostics file" )
        DiagShowbutton.setCheckable(False)
        tlay.addWidget(DiagShowbutton,3,0,1,1)
        self.connect(DiagShowbutton, QtCore.SIGNAL('clicked()'), self.__printDiagFile)

        FwLdbutton = QtGui.QPushButton('Load Firmware', self.Tools)
        FwLdbutton.setToolTip( "Pick your own firmware (use Update normally)" )
        FwLdbutton.setCheckable(False)
        tlay.addWidget(FwLdbutton,3,1,1,1)
        self.connect(FwLdbutton, QtCore.SIGNAL('clicked()'), self.__loadFirmware)

        self.Tools.progress = QtGui.QProgressBar(self.Tools)
        #self.Tools.progress.setMinimumWidth(2*w)
        tlay.addWidget(self.Tools.progress,4,0,1,2)
        #self.Tools.progress.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed )
        self.Tools.progress.setValue( 0 )

        self.Tools.comment = QtGui.QLabel("Press 'Update' to look for updates", self.Tools)
        tlay.addWidget(self.Tools.comment,5,0,1,2)

        normal = self.Tools.Updatebutton.palette().color( QtGui.QPalette.Button )

        self.tab.addTab(self.Tools, "Tools")

    def __SetOptions(self):

       self.options['YellowThreshold'] = self.Options.yelthresh.value()
       self.options['RedThreshold'] = self.Options.redthresh.value()

       if ( 'SUPPORTS_OPTIONS2' in self.drobo.features ):
          self.options['DualDiskRedundancy'] = self.Options.DDRCheckBox.value()
          self.options['SpinDownDelay'] = self.Options.SDDCheckBox.value()
          self.options['SpinDownDelayMinutes'] = self.Options.SDDMinutes.value()
          self.options['UseManualVolumeManagement'] = self.Options.MVMCheckBox.value()
          self.options['UseStaticIPAddress'] = self.Options.SIPCheckBox.value()

       self.drobo.SetOptions(self.options)
       return

    def __initOptionsTab(self):

	self.Options = QtGui.QWidget()
        self.Options.setObjectName("Options")
        olay = QtGui.QGridLayout(self.Options)
        self.options = self.drobo.GetOptions()

        i=0 
        j=0
        self.Options.DDRCheckBox = QtGui.QCheckBox('Dual Disk Redundancy')
        olay.addWidget(self.Options.DDRCheckBox,i,j,1,2)

        i+=1
        j=0
        self.Options.SDDCheckBox = QtGui.QCheckBox('Spin Down Delay Minutes:')
        olay.addWidget(self.Options.SDDCheckBox,i,j,1,2)

        j+=2
        self.Options.SDDMinutes = QtGui.QSpinBox()
        self.Options.SDDMinutes.setRange(0, 100)
        self.Options.SDDMinutes.setSingleStep(1)
        olay.addWidget(self.Options.SDDMinutes,i,j,1,1)

        i+=1
        j=0
        self.Options.MVMCheckBox = QtGui.QCheckBox('Manual Volume Management')
        olay.addWidget(self.Options.MVMCheckBox,i,j,1,2)

        i+=1
        j=0
        self.Options.SIPCheckBox = QtGui.QCheckBox('Use Static IP Address')
        olay.addWidget(self.Options.SIPCheckBox,i,j,1,2)

        i+=1
        self.Options.AddrLabel = QtGui.QLabel("Address:")
        olay.addWidget(self.Options.AddrLabel,i,j,1,2)

        j+=1
        self.Options.AddrEdit = QtGui.QLineEdit()
        olay.addWidget(self.Options.AddrEdit,i,j,1,2)

        j=0
        i+=1
        self.Options.NetMaskLabel = QtGui.QLabel("NetMask:")
        olay.addWidget(self.Options.NetMaskLabel,i,j,1,2)

        j+=1
        self.Options.NetMaskEdit = QtGui.QLineEdit()
        olay.addWidget(self.Options.NetMaskEdit,i,j,1,2)

        if ( 'SUPPORTS_OPTIONS2' in self.drobo.features ):
          self.Options.DDRCheckBox.setChecked( self.options['DualDiskRedundancy'] )
          self.Options.SDDCheckBox.setChecked( self.options['SpinDownDelay'] )
          self.Options.SDDMinutes.setValue( self.options['SpinDownDelayMinutes'] )
          self.Options.MVMCheckBox.setChecked( \
              self.options['UseManualVolumeManagement'] )
          if 'SUPPORTS_ISCSI' in self.drobo.features :
              self.Options.SIPCheckBox.setChecked( self.options['UseStaticIPAddress'] )
              self.Options.AddrEdit.setText( self.options['IPAddress'] ) 
              self.Options.NetMaskEdit.setText( self.options['NetMask'] ) 
        else:
          self.Options.DDRCheckBox.setCheckable(False)
          self.Options.DDRCheckBox.setStyleSheet( "QWidget { color: gray }" )
          self.Options.SDDCheckBox.setCheckable(False)
          self.Options.SDDCheckBox.setStyleSheet( "QWidget { color: gray }" )
          self.Options.MVMCheckBox.setCheckable(False)
          self.Options.MVMCheckBox.setStyleSheet( "QWidget { color: gray }" )
          self.Options.SIPCheckBox.setCheckable(False)
          self.Options.SIPCheckBox.setStyleSheet( "QWidget { color: gray }" )
          self.Options.AddrLabel.setStyleSheet( "QWidget { color: gray }" )
          self.Options.NetMaskLabel.setStyleSheet( "QWidget { color: gray }" )

        self.Options.AlertTitle = QtGui.QLabel( "Alerting Thresholds:", \
           self.Options)
        i+=1
        j=0
        olay.addWidget(self.Options.AlertTitle,i,j,1,1)
        self.Options.AlertTitle.setSizePolicy( QtGui.QSizePolicy.Expanding, \
           QtGui.QSizePolicy.Fixed )

        j+=1
        self.Options.yelthresh = QtGui.QSpinBox()
        self.Options.yelthresh.setRange(0, 100)
        self.Options.yelthresh.setSingleStep(1)
        olay.addWidget(self.Options.yelthresh,i,j,1,1)
        self.Options.yelthresh.setStyleSheet( \
		"QWidget { background-color: yellow }" )
        self.Options.yelthresh.setValue( self.options['YellowThreshold'] )

        j+=1
        self.Options.redthresh = QtGui.QSpinBox()
        self.Options.redthresh.setRange(0, 100)
        self.Options.redthresh.setSingleStep(1)
        olay.addWidget(self.Options.redthresh,i,j,1,1)
        self.Options.redthresh.setStyleSheet( \
		"QWidget { background-color: red }" )
        self.Options.redthresh.setValue( self.options['RedThreshold'] )

        i+=1
        j=0
        self.Options.Setbutton = QtGui.QPushButton('Set', self.Options)
        self.Options.Setbutton.setToolTip("Set the options on the Drobo")
        olay.addWidget(self.Options.Setbutton,i,j,1,-1)
        self.Options.connect(self.Options.Setbutton, \
           QtCore.SIGNAL('clicked()'), self.__SetOptions)

        self.tab.addTab(self.Options, "Options")


    def __init__(self, d, parent=None):
        QtGui.QMainWindow.__init__(self)
        #QtGui.QWidget.__init__(self, parent)

	global partitioner

        self.drobo = d
        self.updates = 0
        self.last_diagfile='/tmp'

        self.statusmsg='Ready'
        self.color = QtGui.QColor(0, 0, 0) 
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('MacStyle'))

        self.setMinimumSize(300, 350)
        self.setSizePolicy( QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding )
        self.setWindowTitle('DroboView')
        self.setWindowIcon(QtGui.QIcon(':Drobo-Front-0000.gif'))

        exit = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))

        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(exit)

        help = menubar.addMenu('&Help')

        manual = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Read Me', self)
        self.manualdialog = ShowText("README.html")
        help.addAction(manual)
        self.connect(manual, QtCore.SIGNAL('triggered()'), self.manualdialog.show)

        devmanual = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'For Developers', self)
        self.devmanualdialog = ShowText("DEVELOPERS.html")
        help.addAction(devmanual)
        self.connect(devmanual, QtCore.SIGNAL('triggered()'), self.devmanualdialog.show)

        dmmanpage = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Drobom man-page', self)
        self.dmmanpagedialog = ShowText("drobom.html")
        help.addAction(dmmanpage)
        self.connect(dmmanpage, QtCore.SIGNAL('triggered()'), self.dmmanpagedialog.show)

        chgmanual = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Change log', self)
        self.chgmanualdialog = ShowText("CHANGES.html")
        help.addAction(chgmanual)
        self.connect(chgmanual, QtCore.SIGNAL('triggered()'), self.chgmanualdialog.show)

        about = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'About Drobom view', self)
        self.aboutdialog = DroboAbout()
        help.addAction(about)
        self.connect(about, QtCore.SIGNAL('triggered()'), self.aboutdialog.show)

        self.tab = QtGui.QTabWidget(self)
        self.setCentralWidget(self.tab)
        self.tab.setMinimumWidth(300)
        self.tab.setMinimumHeight(300)
        
	self.__initDeviceTab()
	self.__initToolTab()
	self.__initFormatTab()
	self.__initOptionsTab()

	self.__updatewithQueryStatus()
        self.updateTimer = QtCore.QTimer(self)
        self.connect(self.updateTimer, QtCore.SIGNAL("timeout()"),
		self.__updateStatus )
        self.updateTimer.setInterval(1000)
        self.updateTimer.start()

        partitioner= " gparted"

