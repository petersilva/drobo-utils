"""
requires json module included in python 2.6


copyright:
Drobo Utils Copyright (C) 2008,2009  Peter Silva (Peter.A.Silva@gmail.com)
Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
named COPYING in the root of the source directory tree.

"""


import json

def obj_instance_variables_2JSON(obj):
      '''return all instance variables of an object (and their values) as a
         json encoded string
      '''

      # find all attribues that are not functions or builtins
      #  these should include all interesting instance variables.
      attributeList = [a for a in dir(obj) if not (a[0:2] == '__' or callable(getattr(obj, a)))]
      # turn the List into a dictionary... 
      attributeDictionary= dict(map((lambda x: (x,getattr(obj,x))), attributeList ))
      return json.dumps(attributeDictionary,indent=4)
    
import Drobo

class DroboJSON(Drobo.Drobo):
   ''' Drobo with JSON API
   '''
   def __init__(self,chardev,debugflags):
      Drobo.Drobo.__init__(self,chardev,debugflags)
      self.fillmein()

   def fillmein(self):
     ''' Add instance variables for all the info fields
     '''
     self.options=self.GetOptions()
     self.capacity=self.GetSubPageCapacity()
     self.config=self.GetSubPageConfig()
     self.luninfo=self.GetSubPageLUNs()
     self.protocol=self.GetSubPageProtocol()
     self.settings=self.GetSubPageSettings()
     self.slotinfo=self.GetSubPageSlotInfo() 
     self.status=self.GetSubPageStatus() 

   def dumps(self):
     return obj_instance_variables_2JSON(self)

if __name__ == '__main__':
   print 'hello world!'
   # start up a simulated Drobo...
   d = DroboJSON("/dev/sdc", debugflags=128)
   print d.dumps()
   
