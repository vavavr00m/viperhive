#!/usr/bin/env python

# --- motd plugin.
# Message Of The Day
#
# Send MOTD to user on login or by 'motd'command 
#
# ---

import plugin

class motd_plugin(plugin.plugin):
        
	def __init__(self, hub):
		super(motd_plugin,self).__init__(hub)
                self.commands['motd']=self.motd
                self.slots['onConnected']=self.onConnected

                if 'motd' not in hub.settings:
                        hub.settings['motd']={'message':'PLEASE SET MOTD MESSAGE (!Set motd message <new message>)'}

        def onConnected(self,user):
                self.motd(user.addr)
                return True
		
	def motd(self,addr):
                if 'motd' in self.hub.settings:
                        self.hub.send_to_addr(addr,self.hub.settings['motd']['message'])
                return ""


