# Drobo Utils Copyright (C) 2008  Peter Silva (Peter.A.Silva@gmail.com)
# Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
# named COPYING in the root of the source directory tree.

from distutils.core import setup, Extension

module1 = Extension('DroboDMP', sources = ['DroboDMP.c'])

setup (name = 'Drobo-utils',
       version = '1.0',
       description = 'Drobo Management Protocol io package',
       ext_modules = [module1],
       py_modules=['Drobo','DroboGUI'],
       scripts=['drobom', 'droboview'],
       data_files = [
                    ('share/pixmaps',             ['Drobo-Front-0000.gif']),
                    ('share/man/man8',             ['drobom.8']),
                    ('share/man/man8',             ['droboview.8'])
                    ]

      )

