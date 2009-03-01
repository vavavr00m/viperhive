#!/usr/bin/env python

# --- unsearch plugin
# refuses often search requests - more than 1 in a minute
# ---

import plugin
import yaml
import datetime
import time
import logging

# --- !! Class name SHOULD BE FileName_plugin
class unsearch_plugin(plugin.plugin):
        
	def __init__(self, hub):

                # Don't forget replace 'name_plugin' here
		super(unsearch_plugin,self).__init__(hub)
                

                # --- SETTINGS FOR PLUGIN ---
                #if 'name' not in self.hub.settings:
                #        self.hub.settings['name']={}
                if 'unsearch.db' not in self.hub.settings:
                        self.hub.settings['unsearch.db']=[]

                self.db=self.hub.settings['unsearch.db']
        
                # --- REGISTERING COMMANDS ---
                #self.commands['?']=self.?
		
                # --- REGISTERING SLOTS (On Event reaction)
		self.slots['onSearch']=self.onSearch
		self.slots['onSearchHub']=self.onSearch
                
                # --- REGISTERING USERCOMMANDS
		#self.usercommands['?']='$UserCommand 1 2 '+hub._('MENU\\ITEM')+'$<%[mynick]> '+hub.core_settings['cmdsymbol']+'COMMAND %[nick] %[line:'+hub._('message')+':]&#124;|'
		
	#def COMMAND(self,addr,params=[]):
	#	#params 'nick' 'message'
	#
	#	return RESULT_STRING
	def onSearch( self, addr, sstr):
#                logging.info('%s %s' % (addr,sstr) )
                ip=addr.split(':')[0]
                t = datetime.datetime.now()
                tm=time.mktime(t.timetuple())
#                logging.info('%s %s %s' % (t,ip,tm) )                
                for i in self.db:
			if i[0]==ip:
                                if (tm-i[1])<60:
                                        return False
                                else:
                                        i[1]=tm
                                        return True
                self.db.append( [ip, time.mktime(t.timetuple())] )
                return True
                
