# Drobo Utils Copyright (C) 2008  Peter Silva (Peter.A.Silva@gmail.com)
# Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
# named COPYING in the root of the source directory tree.

from distutils.core import setup

setup (name = 'Drobo-utils',
       version = '1.0',
       description = 'Drobo Management Protocol io package',
       py_modules=['Drobo','DroboGUI', 'DroboIOctl' ],
       scripts=['drobom', 'droboview'],
       data_files = [
                    ('share/pixmaps',             ['Drobo-Front-0000.gif'])
                    ]

      )

