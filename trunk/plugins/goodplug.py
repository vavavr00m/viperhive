#!/usr/bin/env python

# --- skeleton for plugin.
#
# ---

import plugin
import yaml

# --- !! Class name SHOULD BE FileName_plugin
class goodplug_plugin(plugin.plugin):
        
	def __init__(self, hub):

                # Don't forget replace 'name_plugin' here
		super(goodplug_plugin,self).__init__(hub)
                

                # --- SETTINGS FOR PLUGIN ---
                #if 'name' not in self.hub.settings:
                #        self.hub.settings['name']={}
        
                # --- REGISTERING COMMANDS ---
                #self.commands['?']=self.?
                self.commands['AddPlugin']=self.AddPlugin
		self.commands['DelPlugin']=self.DelPlugin
		
                # --- REGISTERING SLOTS (On Event reaction)
		#self.slots['on?']=self.on?
                
                # --- REGISTERING USERCOMMANDS
		#self.usercommands['?']='$UserCommand 1 2 '+hub._('MENU\\ITEM')+'$<%[mynick]> '+hub.core_settings['cmdsymbol']+'COMMAND %[nick] %[line:'+hub._('message')+':]&#124;|'
		self.usercommands['AddPlugin']='$UserCommand 1 2 '+hub._('Plugins\\Add plugin...')+'$<%[mynick]> '+hub.core_settings['cmdsymbol']+'AddPlugin %[line:'+hub._('plugin')+':]&#124;|'
		self.usercommands['DelPlugin']='$UserCommand 1 2 '+hub._('Plugins\\Del plugin...')+'$<%[mynick]> '+hub.core_settings['cmdsymbol']+'DelPlugin %[line:'+hub._('plugin')+':]&#124;|'
                
		
	#def COMMAND(self,addr,params=[]):
	#	#params 'nick' 'message'
	#
	#	return RESULT_STRING
	def AddPlugin(self,addr,params=[]):
		ans=[]
		try:
			for i in os.listdir(self.path_to_plugins):
				if self.recp['.py'].search(i)!=None and i!="__init__.py" and i!="plugin.py":
					mod=self.recp['before.py'].search(i).group(0)
					ans.append(mod)
			if params[0] in ans:
				self.core_settings['autoload'].append(params[0])
				return self._('Success')
			else:
				return self._('No plugin')
		except:
			logging.error('error while listing plugins: %s', trace())
		
		
	def DelPlugin(self,addr,params=[]):
		if params[0] in self.core_settings['autoload']:
			t=[]
			for j in self.core_settings['autoload']:
				if params[0] != j:
					t.append(j)
			self.core_settings['autoload']=t
			return self._('Success')
		else:
			return self._('No plugin')
