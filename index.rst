
.. raw:: html
   :file: sponsor.js

======================
Using A Drobo on Linux
======================

A Drobo_ is a cool little storage unit.  Just add disks, and it takes care
of figuring out how to maximally protect from data loss.  One does not, as 
with other storage units, have to install matching disks.  Nor are arcane 
decisions about how the data is laid out asked.  It pretends to be just 
a pile of storage, and does the smart thing.  The product line is below:

.. image:: product_line.jpg

So you bought a Drobo_ and want to use it under linux.  Great!  Plug it in and Go!  
Really! It can be used just as a normal disk.  Plug it in like any USB thumb drive.  
For old Linux hands, just use a partitioner, such as parted, and build an ext3 
file system and set the mount point.  See the Setup_ section for details on 
manually setting things up from the command line without any special software.
For those with other tastes, there is also a GUI that can take care of it:

[ `Screen Shots`_  ][ Download_ ][`Links and Help`_][ `Index`_]

.. image:: droboview_prototype4.png

You can use Drobos without any special software.  The blue capacity lights will 
fill up as the disks fill.  When it gets too full, Drobo will ask for another 
drive with its drive lights. Just feed it drives when it asks, and that is all. 
So what is the dashboard good for?

 * If the drobo is hard to see Drobo, the software can replace the lights on 
   the front panel.
 * Verifying if new firmware available, and update installing it.
 * To see information about the hard drives in the Drobo without taking them out.
 * To change the drobo's settings from their defaults (like a 2 TiB LUN size)
 * For DroboPro, there are many settings (ip address?) one might
   need in order to configure it properly for use.
 * If you have a problem, the vendor might ask you to produce a diagnostics file.

So that is where drobo-utils, the linux dashboard, comes in.

.. _README: 

[`Links and Help`_][ `Index`_]

.. include:: README.rst

.. _`Manual Pages`:

---------
MAN PAGES
---------

Drobom
------

  * drobom_  - the interface (command line + view for a GUI)

.. _drobom: drobom.html

[`Links and Help`_][ `Index`_]

.. _DEVELOPERS: 

.. include:: DEVELOPERS.rst

[`Links and Help`_][ `Index`_]

.. include:: DroboShare.rst

[`Links and Help`_][ `Index`_]

.. _CHANGES:

Below are highlights included in each release.

.. include:: CHANGES.rst

.. _`Links and Help`:

-------------
Links & Help!
-------------

.. raw:: html
   :file: sponsor.js

If more information is needed, then there are a number of resources available:

 * Project_ -- development home page.  source code there as a download too...
 * README_ - Documentation for humans.
 * `Manual Pages`_ - traditional unix style documentation (man pages)
 * Group_ - The Google groups is the most active discussion forum 
 * Drobo_ - Who makes Drobos.
 * HomePage_ - Software home page.
 * DEVELOPERS_ Developer documentation
 * DroboSpace_ - Vendor forum
 * Email_ - The developers list, one of us will surely answer.
 * `Email Me`_ - one can email me directly.


.. _`Screen Shots`: gallery.html
.. _Group: http://groups.google.com/group/drobo-talk?hl=en">http://groups.google.com/group/drobo-talk?hl=en
.. _Drobo: http://www.drobo.com  
.. _Download: http://sourceforge.net/project/showfiles.php?group_id=222830
.. _Project: http://sourceforge.net/projects/drobo-utils/
.. _HomePage: http://drobo-utils.sourceforge.net
.. _DroboSpace: http://drobospace.com
.. _Email: drobo-utils-devel@sourceforge.net
.. _`Email me`: Peter.A.Silva@gmail.com

.. _`Index`:

.. contents::


About This Page
---------------

last revised: December 30th, 2009

copyright:

Drobo Utils Copyright (C) 2008,2009  Peter Silva (Peter.A.Silva@gmail.com)
Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.

