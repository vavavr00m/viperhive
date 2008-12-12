#!/usr/bin/env python

# --- chatroom plugin.
#
# ---

import plugin
import pydcppbot
import threading
import viperhive
import re
import logging

class chatroom( pydcppbot.dcppbot ):

	recp=re.compile('\$<([^ ]*)> (.*)')

	def __init__( self, hub, name='#ChatRoom' ):
		
		logging.debug( 'CREATING CHATROOM' )

		self.hub=hub
		self.roomlock=threading.RLock()
		self.nicks=[]
		
		passwd=unicode(viperhive.genpass(10))

		hub.reglist[name]={'level':'chatroom','passwd': passwd}

		super( chatroom, self ).__init__( 'localhost', hub.core_settings['port'], name, passwd )

	def parser ( self, msg ):
		logging.debug( 'CHATROOM: parsing message' )
		
		try:
			amsg=recp.search(msg)
			if amsg==None:
				return
			nick=amsg.group(1)

			if nick not in self.nicks:
				return

			msg='<%s> %s|' % (nick, amsg.gorup(2))
			for i in nicks:
				if i==nick:
					continue
				self.hub.send_pm_to_nick( self.NICK, i, msg )
		except:
			logging.error('CHATROOM ERROR %s' % self.hub.trace() )

		logging.debug( 'CHATROOM: message parsed' )
		return




# --- !! Class name SHOULD BE FileName_plugin
class chatroom_plugin(plugin.plugin):
        
	def __init__(self, hub):

                # Don't forget replace 'name_plugin' here
		super( chatroom_plugin, self ).__init__( hub )
                
		self.roomthreads = {}
		self.rooms = {}
		
		#testroom=chatroom( hub )
		#test=threading.Thread( None, testroom.run, 'test', () )
		#test.start()

                # --- SETTINGS FOR PLUGIN ---
                if 'chatroom' not in self.hub.settings:
			self.hub.settings['chatroom'] = {'#OpChat': { 'allow': ['owner','op'], 'autojoin': ['owner', 'op']} }
		self.settings=self.hub.settings['chatroom']


        
                # --- REGISTERING COMMANDS ---
                self.commands['join'] = self.join
		self.commands['left'] = self.left

		self.loadrooms()
		#self.commands['listroom'] = self.listroom
		
                # --- REGISTERING SLOTS (On Event reaction)
		#self.slots['onUserLeft']=self.onUserLeft
		#self.slots['onConnected']=self.onConnected
                
                # --- REGISTERING USERCOMMANDS
		#self.usercommands['?']='$UserCommand 1 2 '+hub._('MENU\\ITEM')+'$<%[mynick]> '+hub.core_settings['cmdsymbol']+'COMMAND %[nick] %[line:'+hub._('message')+':]&#124;|'
	
	def unload( self ):
		logging.debug('DESTROYING CHATROOMS')
		for room in self.rooms.itervalues():
			room.work=False
		
	def loadrooms( self ):
		for i, r in self.settings.items():
			room=chatroom( self.hub, i )
			self.rooms[i]=room 
			self.hub.userlock.acquire()
			try:
				for nick, user in self.hub.nicks.iteritems():
					if user.level in r['autojoin']:
						room.nicks.append(nick)
			finally:
				self.hub.userlock.release()
			
			roomthread=threading.Thread( None, room.run, 'chatroom', () )
			self.roomthreads[i]=roomthread
			roomthread.start()

	def join( self, addr, params=[]):
		pass
	def left( self, addr, params=[]):
		pass
	#def listroom( self, addr, params=[]):
	#	pass
	




	#def COMMAND(self,addr,params=[]):
	#	#params 'nick' 'message'
	#
	#	return RESULT_STRING
