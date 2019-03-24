QA Test checklist prior to release:

   1.0 Review Documentation
	-- Revision dates in index.html, README.txt, TODO.txt
	-- Set version to pre-release one.
        -- build packages with pre-release version id.
   1.1 drobom status... check for accuracy.


   1.2 drobom settime
   1.3 drobom status... check for accuracy.
   1.4 drobom fwload (something really old) 1.03
     1.4.1 drobom shutdown -- to run the firmware.
     1.4.2 restart (unplug and replug usb)
     1.4.3 run drobom status etc.. (make sure it is running 1.0.3)
       should say disk pack is un-readable or some such.

     1.4.4 hard reset to factory default 
        after downgrade, disk pack will no longer be recognized. need to reset to make Drobo
        look at the disks.
        (with the pin in the back and all that.)
        http://www.drobospace.com/article/10207/Resetting-the-Drobo/?highlight=reset+drobo

     1.4.3 place a file on the Drobo. make sure it works.
     1.4.4 drobom status -- have a look.
   
   1.5 drobom fwupgrade
     1.5.1 drobom shutdown - to run the firmware.
     1.5.2 drobom status -- have a look.
     1.5.3 repeat 1.5 perhaps a second time (as needed to get to current)

   1.7 drobom setlunsize 3 (should fail),1,2  

   1.8 drobom create file systems, each type.
    msdos
    ntfs
    ext3
   ....

   1.9 drobom diag # verify that dumping diagnostics still works...

   2.0 with fw >= 1.30
     drobom set name 
     drobom info...

   3.0 Re-build packages with final release id.
