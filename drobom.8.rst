==============================================================
drobom \- CLI for managing data robotics (drobo) storage units
==============================================================

--------------------------------------------------------------
drobom \- CLI for managing data robotics (drobo) storage units
--------------------------------------------------------------

:Manual section: 8
:Date: 16 October 2009
:version: 0.6.x
:Manual group: drobo-utils


SYNOPSIS
========

drobom _command_ _arguments_

DESCRIPTION
===========

Options is one of:

* *\-c, \-\-command* the command to execute.
* *_\-d, \-\-device* the device to operate on (default searches all devices and picks first one found.)
* *\-h, \-\-help* print a usage message
* *\-n, \-\-no* answer all questions no (generally does not do any damage)
* *\-s, \-\-string \<string\>* sometimes new models are not recognized by drobom. See documentation.
* *\-v, \-\-verbose* verbosity, a bit-field to trigger increased output as needed, mostly for debugging. 
   * *1* - General, 
   * *2* - Hardware Dialog, 
   * *4* - Initiation, 
   * *8* - Raw returns, 
   * *16* - Detection
   * *64* will print everything... (default: 0, as terse as possible.)
   * *128* enables simulation mode (for testing when no Drobo is available. Dangerous!)
* *\-V, \-\-version* print the version id.
* *\-y, \-\-yes* answer all questions yes (generally overwrites stuff) 


Command is one of:

* *blink* identify the drobo by making the lights blink
* *diag* dump diagnostics file into /tmp directory
* *diagprint \<diagdumpfile\>*
  print diagnostics file to standard output \<diagdumpfile\> the diagnostic dump file to read.
* *fwcheck* query 
  drobo.com for updates to firmware for the given Drobo
* *fwload  \<fwimage\>*
  load a specific firmware for the given Drobo. Arguments: <fwimage>
  the firmware file to load.
* *fwupgrade* 
  upgrade the firmware to the latest and greatest, recommended by DRI
* *help*
  print this text
* *info*  <toprint>
  print information on a Drobo. The <toprint> argument is a comma separated list of the values below (default is to print all of them): config, capacity, protocol, settings, slots, firmware, status, options, luns, scsi
* *list*
  show device files for all Drobos found.
* *set \<options\> \<value\>*
  set firmware options, such as ipaddress, etc... use 'info settings'
* *set name  <newname>*
  Set the name of the Drobo to the given value ( only firmware > 1.3.0 supports this command )
* *set lunsize*  
  Set the size of LUNS on device. Arguments: \<sz\>
  integer number of TiB to set the lunsize to

  Note: After execution, Drobo reboots, wait a few minutes before accessing again

* *set time* - sets various Drobo's clock to UTC
* *shutdown*
  shutdown drobo (DRI calls this 'standby')
* *status*
  report how is the Drobo doing
* *device*
  raw block device of a drobo (i.e. /dev/sdz) . If not given, assumes all attached drobos.
* *view*
  Start up the graphical user interface.

This manual page was written by Chris AtLee <chris@atlee.ca> for the Debian
project (but may be used by others).
