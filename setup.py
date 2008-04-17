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
       classifiers=[
          'Development Status :: 1 - Alpha',
          'Environment :: Console',
          'Environment :: Graphical User Environment',
          'Intended Audience :: End Users/Desktop',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: General Public License v3',
          'Operating System :: Linux',
          'Programming Language :: Python',
          ],
      )

