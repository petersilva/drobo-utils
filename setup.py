# Drobo Utils Copyright (C) 2008,2009  Peter Silva (Peter.A.Silva@gmail.com)
# Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
# named COPYING in the root of the source directory tree.

from distutils.core import setup

setup(name='Drobo-utils',
      version='9999',
      description='Drobo Management Protocol io package',
      py_modules=['Drobo', 'DroboGUI', 'DroboIOctl'],
      scripts=['drobom', 'droboview'],
      data_files=[('share/pixmaps', ['Drobo-Front-0000.gif']),
                  ('share/drobo-utils-doc', ['README.html']),
                  ('share/drobo-utils-doc', ['DEVELOPERS.html']),
                  ('share/drobo-utils-doc', ['drobom.html']),
                  ('share/drobo-utils-doc', ['droboview.html']),
                  ('share/drobo-utils-doc', ['CHANGES.html'])])
