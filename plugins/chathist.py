#!/usr/bin/env python

# --- Chathist plugin.
#
#    Showing last N messages
#
# ---

import plugin
import yaml
import time

class chathist_plugin(plugin.plugin):
        
    def __init__(self,hub):
          super(chathist_plugin,self).__init__(hub)
          self.N = 20
          if 'chathist' not in self.hub.settings:
            self.hub.settings['chathist']=[]
          self.chlog=self.hub.settings['chathist']=[]
          self.slots['onConnected']=self.onConnected
          self.slots['onMainChatMsg']=self.onMainChatMsg
		
    def onConnected(self,user):
          self.hub.send_to_addr(user.addr,'>>>>>>>>>>>ChatHistory<<<<<<<<<<<<<<')
          f = open('./chhist.log','r')
          i = 0
          lines = ""
          for line in reversed(f.readlines()):
            i+=1
            lines= "%s%s" % ( line, lines)
            if i==self.N-1:
              break
          lines= "\n%s" % lines
          self.hub.send_to_addr(user.addr,unicode(lines,'utf-8'))
          f.close()
          self.hub.send_to_addr(user.addr,unicode('>>>>>>>>>>>ChatHistory<<<<<<<<<<<<<<','utf-8'))
          return True
          
    def onMainChatMsg(self, from_nick, message): 
        open('./chhist.log','a').write(('['+time.strftime('%x %X')+'] <'+from_nick+'> '+message+'\n').encode('utf-8'))
        for count, line in enumerate(open('./chhist.log')):
          pass
        if count > self.N-1:
          f = open('./chhist.log')
          lines = f.readlines()
          f.close();
          del lines[0]
          f = open('./chhist.log',"w")
          f.writelines(lines)
          f.close();
        return True    