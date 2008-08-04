#!/usr/bin/env python

# --- SAY plugin.
# used to say something from different nickname
# usage: say 'nick' 'message'
# ---

import plugin

class say_plugin(plugin.plugin):
        
	def __init__(self, hub):
		super(say_plugin,self).__init__(hub)
                self.commands['say']=self.say
		
	def say(self,addr,params):
		#params 'nick' 'message'
		if len(params)>1:
			self.hub.send_to_all('<%s> %s|' % (params[0], " ".join(params[1:])))
			return ''
		else:
			return self.hub._('params error')

