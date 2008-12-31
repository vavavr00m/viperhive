#!/usr/bin/env python
# vim:fileencoding=utf-8

import yaml

import socket
import select
import re
import threading
import thread
import logging
import sys
import signal
import os
import traceback
import codecs
import time
import string
import random

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
#logging.getLogger().addHandler()

trace=None
if 'format_exc' in dir(traceback):
        from traceback import format_exc as trace
else:
        from traceback import print_exc as trace


reload(sys)

def lock2key (lock):
		key = {}
		for i in xrange(1, len(lock)):
				key[i] = ord(lock[i]) ^ ord(lock[i-1])
		key[0] = ord(lock[0]) ^ ord(lock[len(lock)-1]) ^ ord(lock[len(lock)-2]) ^ 5
		for i in xrange(0, len(lock)):
				key[i] = ((key[i]<<4) & 240) | ((key[i]>>4) & 15)
		out = ''
		for i in xrange(0, len(lock)):
				out += unichr(key[i])
		out = out.replace(u'\0', u'/%DCN000%/').replace(u'\5', u'/%DCN005%/').replace(u'\44', u'/%DCN036%/')
		out = out.replace(u'\140', u'/%DCN096%/').replace(u'\174', u'/%DCN124%/').replace(u'\176', u'/%DCN126%/')
		return out

def genpass( size=10 ):
	s=[]
	for i in range( size ):
		s.append( random.choice( string.letters + string.digits ) )
        return ''.join(s)




def number_to_human_size(size, precision=1):
	"""
	Returns a formatted-for-humans file size.

	``precision``
	The level of precision, defaults to 1

	Examples::

	>>> number_to_human_size(123)
	'123 Bytes'
	>>> number_to_human_size(1234)
	'1.2 KB'
	>>> number_to_human_size(12345)
	'12.1 KB'
	>>> number_to_human_size(1234567)
	'1.2 MB'
	>>> number_to_human_size(1234567890)
	'1.1 GB'
	>>> number_to_human_size(1234567890123)
	'1.1 TB'
	>>> number_to_human_size(1234567, 2)
	'1.18 MB'
	"""
	if size == 1:
		return "1 Byte"
	elif size < 1024:
		return "%d Bytes" % size
	elif size < (1024**2):
		return ("%%.%if KB" % precision) % (size / 1024.00)
	elif size < (1024**3):
		return ("%%.%if MB" % precision) % (size / 1024.00**2)
	elif size < (1024**4):
		 return ("%%.%if GB" % precision) % (size / 1024.00**3)
	elif size < (1024**5):
		return ("%%.%if TB" % precision) % (size / 1024.00**4)


	return ""
	





class DCUser:

	recp={}
	recp['tag']=re.compile('[<](.*)[>]$')
	recp['slots']=re.compile('S:(\d*)')
	recp['hubs']=re.compile('H:([0-9/]*)')
	


	def __init__(self,myinfo="",descr=None,addr=None):
		
		self.nick = ''
		self.connection = ''
		self.flag = ''
		self.mail = ''
		self.share = 0
		self.descr = None
		self.MyINFO = None
		self.level = 0
		self.tag = ''
		self.slots = 0
		self.hubs = 0
		self.sum_hubs = 0	
		if len( myinfo )>0:
			self.upInfo( myinfo )
		self.descr = descr
		self.addr = addr



				

	def upInfo(self,myinfo):
		self.MyINFO = myinfo
		ar = myinfo.split("$")
		ar2 = ar[2].split(" ",2)
		self.nick = ar2[1]
		self.description = ar2[2]
		self.connection = ar[4][0:-1]
		self.flag = ar[4][-1]
		self.mail = ar[5]
		self.share = int( ar[6] )

		# Parsing TAG
		tag = self.recp['tag'].search( self.description )
		if self.tag != None:
			self.tag=tag.group( 1 )
			slots = self.recp['slots'].search( self.tag )
			if slots != None:
				self.slots = int( slots.group( 1 ) )

			hubs = self.recp['hubs'].search( self.tag )
			if hubs != None:
				self.hubs = hubs.group( 1 )
				try:
					self.sum_hubs=self.get_sum_hubs()
				except:
					logging.warning( 'WRONG TAG: %s' % tag )



	def get_ip( self ):
		return self.addr.split(':')[0]

	def get_sum_hubs( self ):
		s=0
		for i in self.hubs.split('/'):
			s=s+int( i )
		return s


class DCHub:
	# CONSTANTS
	LOCK='EXTENDEDPROTOCOL_viperhive Pk=version0.4-svn'
	SUPPORTS='NoHello NoGetINFO UserIP UserIP2'
	WORKER_MAX=300
	 
	 
	def _(self,string):  # Translate function
		return self.lang.get(string,string)
	
	def tUCR( self, req ):
		'''translate and make usercmmand request %[line:req:] '''
		return '%%[line:%s:]' % self._( req )


	def UC( self, menu, params ):
		'''make UserCommands'''
		return '$UserCommand 1 2 %s %s %s%s&#124;|' % ( menu, '$<%[mynick]>', self.core_settings['cmdsymbol'], ' '.join( params ) )


	def Gen_UC( self ):
		self.usercommands={}
		# -- CORE USERCOMMANDS --

		self.usercommands['Quit'] = self.UC( self._('Core\\Quit'), ['Quit'] )
		self.usercommands['Save'] = self.UC( self._('Settings\\Save settings'), ['Save'] )
		self.usercommands['SetTopic'] = self.UC( self._('Settings\\Set hub topic'), ['SetTopic', self.tUCR('New Topic')] )
		self.usercommands['Help'] = self.UC( self._('Help'), ['Help'] )
		self.usercommands['RegenMenu'] = self.UC( self._( 'Core\\Regenerate menu' ), ['RegenMenu'] )
		self.usercommands['ReloadSettings'] = self.UC( self._( 'Core\\Reload settings (DANGEROUS)' ), ['ReloadSettings'] )

		# -- settings get/set
		self.usercommands['Get'] = self.UC( self._('Settings\\List settings files'), ['Get'] )

		self.usercommands['Set'] = self.UC( self._('Settings\\Set variable'), ['Set', self.tUCR( 'File' ), self.tUCR( 'Variable' ), self.tUCR( 'New Value' )] )
		 

		# -- Limits control

		self.usercommands['Set'] += self.UC( self._('Settings\\Limits\\Set max users'), ['Set core max_users', self.tUCR( 'New max users' )] )
		self.usercommands['Set'] += self.UC( self._('Settings\\Limits\\Set min share'), ['Set core min_share', self.tUCR( 'New min share (in bytes)' )] )
		self.usercommands['Set'] += self.UC( self._('Settings\\Limits\\Set max hubs'), ['Set core max_hubs', self.tUCR( 'New max hubs' )] )
		self.usercommands['Set'] += self.UC( self._('Settings\\Limits\\Set min slots'), ['Set core min_slots', self.tUCR( 'New min slots' )] )




		# -- User control
		self.usercommands['AddReg'] = ''
		self.usercommands['SetLevel'] = ''


		for i in self.settings['privlist'].keys():
			self.usercommands['AddReg'] += self.UC( self._( 'Users\\Selected\\Register selected nick as\\%s' ) % i, ['AddReg %[nick]', i, self.tUCR( 'Password' )] )


		self.usercommands['AddReg'] += self.UC( self._( 'Users\\Register nick...' ), ['AddReg', self.tUCR( 'nick' ), self.tUCR( 'level' ), self.tUCR( 'Password' )] )

		self.usercommands['ListReg'] = self.UC( self._( 'Users\\List registred nicks' ), ['ListReg'] )

		self.usercommands['DelReg'] = self.UC( self._( 'Users\\Selected\\Unreg selected nick' ), ['DelReg %[nick]'] )
		self.usercommands['DelReg'] += self.UC( self._( 'Users\\Unreg nick...' ), ['DelReg', self.tUCR('Nick')] )

		for i in self.settings['privlist'].keys():
			self.usercommands['SetLevel'] += self.UC( self._( 'Users\\Selected\\Set level for selected nick\\%s' ) % i, ['SetLevel %[nick]', i] )


		self.usercommands['PasswdTo'] = self.UC( self._( 'Users\\Selected\\Set password for selected nick...' ), ['PasswdTo %[nick]', self.tUCR('new password')] )

		self.usercommands['Kick'] = self.UC( self._( 'Kick selected nick' ), ['Kick %[nick]'] )

		self.usercommands['UI'] = self.UC( self._( 'Users\\Selected\\User Info' ), ['UI %[nick]'] )




		# -- Plugin control
		
		#self.usercommands['ListPlugins'] = self.UC( self._( 'Plugins\\List aviable plugins' ), ['ListPlugins'] )
		#self.usercommands['ActivePlugins'] = self.UC( self._( 'Plugins\\List active plugins' ), ['ListPlugins'] )

		menu = self._( 'Plugins\\Load/Reload Plugin\\' )
		menuU = self._( 'Plugins\\Unload Plugin\\' )
		loaded = self._( '(loaded)' )

		aplugs = self.get_aviable_plugins()

		self.usercommands['ReloadPlugin'] = ''
		self.usercommands['LoadPlugin'] = ''
		self.usercommands['UnloadPlugin'] = ''
		
		for i in aplugs:
			if i in self.plugs:
				self.usercommands['ReloadPlugin'] += self.UC( menu + i + '  ' + loaded, ['ReloadPlugin', i] )
			else:
				self.usercommands['LoadPlugin'] += self.UC( menu + i, ['LoadPlugin', i] )

		for i in self.plugs.keys():
			self.usercommands['UnloadPlugin'] += self.UC( menuU + i, ['Unload', i] )




		#self.usercommands['ListPlugins']='$UserCommand 1 2 '+self._('Plugins\\List aviable plugins')+'$<%[mynick]> '+self.core_settings['cmdsymbol']+'ListPlugins&#124;|'
		#self.usercommands['ActivePlugins']='$UserCommand 1 2 '+self._('Plugins\\List active plugins')+'$<%[mynick]> '+self.core_settings['cmdsymbol']+'ActivePlugins&#124;|'
		#self.usercommands['LoadPlugin']='$UserCommand 1 2 '+self._('Plugins\\Load plugin..')+'$<%[mynick]> '+self.core_settings['cmdsymbol']+'LoadPlugin %[line:'+self._('plugin')+':]&#124;|'
		#self.usercommands['UnloadPlugin']='$UserCommand 1 2 '+self._('Plugins\\Unload plugin...')+'$<%[mynick]> '+self.core_settings['cmdsymbol']+'UnloadPlugin %[line:'+self._('plugin')+':]&#124;|'
		#self.usercommands['ReloadPlugin']='$UserCommand 1 2 '+self._('Plugins\\Reload plugin...')+'$<%[mynick]> '+self.core_settings['cmdsymbol']+'ReloadPlugin %[line:'+self._('plugin')+':]&#124;|'
	   
		# -- Self control
		self.usercommands['Passwd'] = self.UC( self._('Me\\Set MY password...'), [ 'Passwd', self.tUCR( 'new password' ) ] )

		for i in self.plugs.values():
			i.update_menu()
			self.usercommands.update( i.usercommands )




		#logging.debug ('UC: %s' % repr(self.usercommands) )
		
		return




	def __init__( self ):

		# COMMANDS
		self.commands={}
		# SIGNAL-SLOT EVENT SUBSYSTEM
		self.slots={}
	   

		# COMPILE REGEXPS
		self.recp={}
		self.recp['Key']=re.compile('(?<=\$Key )[^|]*(?=[|])')
		self.recp['ValidateNick']=re.compile('(?<=\$ValidateNick )[^|]*(?=[|])')
		self.recp['Supports']=re.compile('(?<=\$Supports )[^|]*(?=[|])')
		self.recp['MyPass']=re.compile('(?<=\$MyPass )[^|]*(?=[|])')
		self.recp['MyINFO']=re.compile('\$MyINFO [^|]*(?=[|])')

		self.recp['NoGetINFO']=re.compile('NoGetINFO')
		self.recp['NoHello']=re.compile('NoHello')

		self.recp['.yaml']=re.compile('\.yaml$')
		self.recp['before.yaml']=re.compile('.*(?=\.yaml)')
		self.recp['.py']=re.compile('\.py$')
		self.recp['before.py']=re.compile('.*(?=\.py)')
		self.recp['tag']=re.compile('[<](.*)[>]$')
	   

		# SET PATHS
		self.path_to_settings="./settings/"
		self.path_to_plugins="./plugins/"


		# ----- SETTINGS -----
		self.settings={}

		# LOADING SETTINGS
		self.load_settings()


		# SHORTCUTS
		self.core_settings=self.settings.get('core',{})
		self.reglist=self.settings.get('reglist',{})
		self.privlist=self.settings.get('privlist',{})

		# DEFAULTS
		defcore_settings={}
		defcore_settings['port']=[411]
		defcore_settings['hubname']='Viperhive powered hub'
		defcore_settings['topic']='Viperhive powered hub'
		defcore_settings['cmdsymbol']='!'
		defcore_settings['OpLevels']=['owner']
		defcore_settings['Protected']=['owner', 'op']
		defcore_settings['Lang']='ru.cp1251'
		defcore_settings['autoload']=['ban', 'mute', 'forbid', 'say', 'motd', 'regme']
		defcore_settings['loglevel']=10
		defcore_settings['autosave']=120
		defcore_settings['userip']=['owner', 'op']

		# ---- LIMITS ----

		defcore_settings['max_users'] = 10000
		defcore_settings['min_share'] = 0
		defcore_settings['max_hubs'] = 1000
		defcore_settings['min_slots'] = 0
		defcore_settings['pass_limits'] = ['owner', 'op', 'chatroom']



		defcore_settings['hubinfo']={'address':'example.com','description':'Viperhive powered hub','type':'ViperHive Hub', 'hubowner':'owner'}

		defreglist={'admin':{'level':'owner', 'passwd':'megapass'}}


		defprivlist={'owner':['*']}

		
	


		# If loaded core_settings miss some stuff - load defaults
		if len(self.core_settings)==0:
				self.settings['core']=self.core_settings={}

		for i in defcore_settings.keys():
			if not i in self.core_settings:
				self.core_settings[i]=defcore_settings[i]


		#------UPDATE SETTINGS FROM OLD VERSION:-------

		# UPDATE PORT SETTINGS FOR VERSIONS <= svn r168
		if not isinstance( self.core_settings['port'], list ):
			self.core_settings['port'] = [ self.core_settings['port'] ]

		if len(self.reglist)==0:
				self.settings['reglist']=self.reglist=defreglist
	   
		if len(self.privlist)==0:
				self.settings['privlist']=self.privlist=defprivlist

		# MORE SHORTCUTS
		self.oplevels=self.core_settings['OpLevels']
		self.protected=self.core_settings['Protected']
		self.KEY=lock2key(self.LOCK)

		# ---- SOCKETS ----
		self.srvsock = []
		for i in self.core_settings['port']:
			try:
				sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM ) 
				sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
				sock.bind( ("", i) )
				sock.listen( 5 )
				self.srvsock.append( sock )
			except:
				logging.error('---- A PROBLEM WHILE BINDING TO PORT: %s \n %s----' % (i, trace(),) )
		#self.descriptors = [[self.srvsock]]
		self.descriptors=[]

		# User hashes
		self.nicks={}
		self.addrs={}

		# Support for very, VERY old clients
		self.hello=[]
		self.getinfo=[]
	   
		self.clthreads=[]

	   
		# Reinitialize Logging
		logging.debug('Set logging level to %s' % str(self.settings['core']['loglevel']))
		reload(sys.modules['logging'])
		logging.getLogger().setLevel(self.settings['core']['loglevel'])
	   

		# REGISTERING CORE COMMANDS
		self.commands['Quit']=self.Quit #Usercommands +
		self.commands['AddReg']=self.AddReg #Usercommands +
		self.commands['DelReg']=self.DelReg  #Usercommands +
		self.commands['ListReg']=self.ListReg #Usercommands +
		self.commands['Get']=self.Get #Usercommands +
		self.commands['Set']=self.Set #Usercommands +
		self.commands['SetLevel']=self.SetLevel #Usercommands +
		self.commands['Help']=self.Help #Usercommands +
		self.commands['ListPlugins']=self.ListPlugins #Usercommands +
		self.commands['LoadPlugin']=self.LoadPlugin #Usercommands +
		self.commands['UnloadPlugin']=self.UnloadPlugin #Usercommands +
		self.commands['ActivePlugins']=self.ActivePlugins #Usercommands +
		self.commands['Save']=self.Save #Usercommands +
		self.commands['ReloadPlugin']=self.ReloadPlugin
		self.commands['RP']=self.ReloadPlugin #Usercommands +
		self.commands['Passwd']=self.Passwd
		self.commands['PasswdTo']=self.PasswdTo #Usercommands +
		self.commands['Kick']=self.Kick #Usercommands +
		self.commands['UI']=self.UI #Usercoommands +
		self.commands['SetTopic']=self.SetTopic #Usercommands +
		self.commands['RegenMenu'] = self.RegenMenu #Usercommands +
		self.commands['ReloadSettings'] = self.ReloadSettings #Usercommands +


		# TRANSLATION SYSTEM
		self.lang={}              # Current language array
		self.help={}              # Help for current language

		# -- LOADING LANGUAGE

		lang=self.core_settings['Lang'].split('.')[0]
		self.charset=cpage=self.core_settings['Lang'].split('.')[1]


		try:
			lpath='./languages/'+lang+'/'
			lfiles=os.listdir(lpath)
			for i in lfiles:
				# LOAD MESSAGES FOR CURRENT LANGUAGE
				if self.recp['.yaml'].search(i)!=None:
					try:
						arr=yaml.load(codecs.open(lpath+i,'r','utf-8').read())
					   
						#for key,value in arr.iteritems():
						#       arr[key]=value.encode(cpage)

						self.lang.update(arr)
					except:
						logging.error('file %s in wrong format: %s' % ((lpath+i), trace()))
			if 'help' in lfiles:                                
			   # LOAD HELP FOR CURRENT LANGUAGE
			   hpath=lpath+'help/'
			   hfiles=os.listdir(hpath)
			   for i in hfiles:
					if self.recp['.yaml'].search(i)!=None:
						try:
							arr=yaml.load(codecs.open(hpath+i,'r','utf-8').read())
						   
							#for key,value in arr.iteritems():
							#        arr[key]=value.encode(cpage)

							self.help.update(arr)
						except:
							logging.error('file %s in wrong format: %s' % ((lpath+i), trace()))
		except:
			logging.error('language directory not found %s' % (trace()))

	   
		logging.info('Language loaded: %s strings' % str(len(self.lang)))
		logging.info('Help loaded: %s strings' % str(len(self.help)))


		# PLUGINS
		self.plugs={}

		self.Gen_UC()

		# AUTOLOAD PLUGINS
		for i in self.core_settings['autoload']:
			self.LoadPlugin(None,[i])

		logging.info ('Hub ready to start on port %s...' % self.core_settings['port'])

		self.skipme=[]



		
	def emit(self,signal,*args):
		#logging.debug('emitting %s' % signal)
		#logging.debug('emit map %s' % repr(self.slots))
		for slot in self.slots.get(signal,[]):
			logging.debug( 'Emitting: %s, for  %s slot' % ( signal, repr( slot )) )
			try:
				if not slot(*args):
					logging.debug( 'Emit %s: FALSE' % signal )
					return False
			except:
				logging.error('PLUGIN ERROR: %s' % trace())
		logging.debug( 'Emit %s: True' % signal )
		return True

	def pinger( self, atime ):


		while self.work:
			time.sleep(atime)
			logging.debug('pinging')
			try:
				self.send_to_all('|')
			except:
				pass
		return True
							   
	def settings_autosaver( self, atime ):
		while self.work:
			time.sleep(atime)
			logging.debug('settings autosave')
			self.save_settings()
		return True

	def receive_and_parse( self, sock ):
		try:
			# Received something on a client socket
			logging.debug( 'reciving from %s' % repr( sock ) )
			try:
				str = unicode(sock.recv(4096), self.charset)
			except:
				logging.debug('recive from client error %s %s' % (trace(), repr(sock)))
				self.skipme.remove( sock )
				return
			# Check to see if the peer socket closed
			if str == '':
				host,port = sock.getpeername()
				addr = '%s:%s' % (host, port)
				logging.debug ('disconnecting: %s..' % addr)
				self.emit('onDisconnected',addr)
				self.drop_user_by_addr(addr)
			else:
				# -- Recive up to 10 x 4096 from socket. If it still not empty - ignore it.
				i=10
				while str[-1]!="|" and i>0:
					try:
						str=str+unicode(sock.recv(4096),self.charset)
					except:
						logging.debug('recive from client error %s' % trace())
						self.skipme.remove( sock )
						return
					i-=1
				# --
				logging.debug( 'parsing' )
				host,port = sock.getpeername()
				addr = '%s:%s' % (host, port)
				logging.debug ('recived: %s from %s' % (str, addr))
				if str[-1]=="|":
					if self.emit('onRecivedSomething',addr):
						logging.debug('Recived: %s' % str)
						if len(str)>0:
							msgarr=str.split('|')
							for i in msgarr:
								if i=="":
									pass
								elif i[0]=="$":
									self.parse_protocol_cmd(i,addr)
								else:
									self.parse_chat_msg(i,addr)


				else:
					logging.warning ( 'Too big or wrong message recived from %s: %s' % (addr,s) )

				self.skipme.remove( sock )

		except:
			self.drop_user_by_sock(sock)
			logging.debug('User Lost: %s' % trace()) 
	



	def clientserv(self, part):
		''' listen for client sockets in descriptors[part]'''
		logging.debug('clientserv %s started!' % part)
		
		while self.work:
			try:
				if len(self.descriptors[part])>0:
					(sread, swrite, sexc) = select.select( self.descriptors[part], [], [], 1 )
				else:
					time.sleep(1)
					sread=[]
				for sock in sread:
					if sock == None:
						continue

					#logging.debug( 'activity in socket %s' % repr( sock ) )
					if sock not in self.skipme:
					#	logging.debug( 'accepting activity' )
						self.skipme.append( sock ) #Temporary remove socket, it will be served in separate thread
						parser=threading.Thread(None, self.receive_and_parse, 'Recive/Parse', (sock,))
						parser.start()
			except:
				logging.debug( 'clientserv error %s' % trace() )
			
		print('clientserv %s stopped!' % part)
		return
	def run( self ):
		logging.info ('Hub started!')
		try:
			try:
				self.work=True
				self.pingthread=threading.Thread(None,self.pinger,'pinger',(120,))
				self.autosaver=threading.Thread(None,self.settings_autosaver,'saver',(self.settings['core']['autosave'],))
				self.pingthread.setDaemon(True)
				self.autosaver.setDaemon(True)

				self.pingthread.start()
				self.autosaver.start()

				while self.work:
					(sread, swrite, sexc) = select.select( self.srvsock, [], [], 1 )

					for sock in sread:
						# Start new thread to avoid hub lock when user connecting
						newsock, (host, port) = sock.accept()
						connhandler=threading.Thread(None,self.accept_new_connection,'newConnection: %s %s' %(str(host), str(port)),(newsock, host, port))
						connhandler.setDaemon(True)
						connhandler.start()
						#self.accept_new_connection()
			except:
				logging.error(trace())
				self.on_exit()
		finally:
			# Save settings before exiting
			self.on_exit()

								

	def parse_protocol_cmd(self,cmd,addr):
		acmd=cmd.split(' ')
		if acmd[0]=='$GetINFO':
			if len(acmd)==3:
				if self.addrs[addr].nick==acmd[2] and self.nicks.has_key(acmd[1]):
					if self.emit('onGetINFO',acmd[1],acmd[2]):
						logging.debug('send myinfo %s' % self.nicks[acmd[1]].MyINFO)
						self.send_to_nick(acmd[2],self.nicks[acmd[1]].MyINFO+"|")
		elif acmd[0]=='$MyINFO':
			if len(acmd)>=3:
				if self.addrs[addr].nick==acmd[2]:
					try:
						self.nicks[acmd[2]].upInfo(cmd)
						if self.emit('onMyINFO',cmd):
							self.send_to_all(cmd+"|")
					except:
						logging.warning( 'Wrong MyINFO by: %s with addr %s: %s' ( acmd[2], addr, trace() ) )
						self.drop_user_by_addr(addr)
		elif acmd[0]=='$To:':
			if len(acmd)>5:
				if acmd[3]==self.addrs[addr].nick==acmd[4][2:-1]:
					if acmd[1] in self.nicks:
						tocmd=cmd.split(' ',5)
						if self.emit('onPrivMsg',acmd[3],acmd[1],tocmd[5]):
							self.send_to_nick(acmd[1],cmd+"|")
		elif acmd[0]=='$ConnectToMe':
			if len(acmd)==3:
				if acmd[2].split(':')[0]==addr.split(':')[0]:
					if self.emit('onConnectToMe',addr,acmd[1]):
						self.send_to_nick(acmd[1],cmd+"|")
		elif acmd[0]=='$RevConnectToMe':
			if len(acmd)==3:
				if acmd[1] in self.nicks:
					if self.addrs[addr].nick==acmd[1]:
						if self.emit('onRevConnectToMe',acmd[1],acmd[2]):
							self.send_to_nick(acmd[2],cmd+"|")
		elif acmd[0]=='$Search':
			if len(acmd)>=3:
				srcport=acmd[1].split(':')
				if len(srcport)==2:
					if srcport[0]=='Hub':
						#Passive Search
						if srcport[1]==self.addrs[addr].nick:
							bcmd=cmd.split(' ',2)
							if self.emit('onSearchHub',bcmd[1],bcmd[2]):
								self.send_to_all(cmd+"|",self.addrs[addr].descr)

					else:
						#Active Search
						if srcport[0]==self.addrs[addr].addr.split(':')[0]:
							bcmd=cmd.split(' ',2)
							if self.emit('onSearch',bcmd[1],bcmd[2]):
								self.send_to_all(cmd+"|",self.addrs[addr].descr)
		elif acmd[0]=='$SR':
			fcmd=cmd.split(chr(5))
			if len(fcmd)==4:
				if len(acmd)>=3:
					sender=acmd[1]
					reciver=fcmd[3]
					if self.addrs[addr].nick==sender:
						if self.emit('onSearchResult',sender,reciver,cmd):
							self.send_to_nick(reciver,cmd+"|")


		elif acmd[0] == '$GetNickList':
			self.send_to_addr( addr, self.get_nick_list() )

		elif acmd[0]=='$HubINFO' or acmd[0]=='$BotINFO':
			hubinfo='$HubINFO '
			info=self.core_settings['hubinfo']
			hubinfo+='%s$' % self.core_settings['hubname']
			hubinfo+='%s:%s$' % ( info.get('address',''), self.core_settings['port'][0] )
			hubinfo+='%s$' % info.get('description','')
			hubinfo+='%s$' % self.core_settings.get('max_users','10000')
			hubinfo+='%s$' % self.core_settings.get('min_share','0') 
			hubinfo+='%s$' % self.core_settings.get('min_slots','0')
			hubinfo+='%s$' % self.core_settings.get('max_hubs','1000')
			hubinfo+='%s$' % info.get('type','')
			hubinfo+='%s$' % info.get('owner','')
			hubinfo+='|'
			self.send_to_addr( addr,hubinfo )

		else:
			logging.debug('Unknown protocol command: %s from: %s' % (cmd,addr))

		return


	def parse_cmd(self,cmd,addr):
		logging.debug('command recived %s' % cmd)
				#cmd=self.decode(cmd)
		acmd=cmd.split(' ')
		ncmd=acmd[0]
		for j in self.commands:
			if acmd[0].lower() == j.lower():
				ncmd=j
		if self.check_rights(self.addrs[addr],acmd[0]):
			if ncmd in self.commands:
				try:
					if (len(acmd[1:]))>0:
						result=self.commands[ncmd](addr,acmd[1:])
					else:
						result=self.commands[ncmd](addr)
					if result!='':
						self.send_to_addr(addr,self._('<HUB> %s|') % result)
						
				except SystemExit:
					raise SystemExit

				except:
					self.send_to_addr(addr,self._('<HUB> Error while proccessing command %s|') % trace())
			else:
				self.send_to_addr(addr,self._('<HUB> No such command'))
		else:
			self.send_to_addr(addr,self._('<HUB> Premission denied'))
		return



	def parse_chat_msg(self,msg,addr):
		acmd=msg.split(' ',1)
		if len(acmd)==2:
			if acmd[0][1:-1]==self.addrs[addr].nick:
				if acmd[1][0]==self.core_settings['cmdsymbol']:
					tmp=threading.Thread(None,self.parse_cmd,'cmd_parser',(acmd[1][1:],addr,))
					tmp.setDaemon(True)
					tmp.start()
					#self.parse_cmd(acmd[1][1:],addr)
				else:
					if self.emit('onMainChatMsg',acmd[0][1:-1],acmd[1]):
						self.send_to_all(msg+"|")
			else:
				logging.warning('user tried to use wrong nick in MC. Real nick: %s. Message: %s' % (self.addrs[addr].nick, msg))
				self.drop_user_by_addr(addr)
		return


	def accept_new_connection( self, newsock, host, port ):
		if len( self.nicks ) >= self.core_settings['max_users']:
			newsock.close()
			logging.warning( 'MAX USERS REACHED!!!' )
			return
		try:
			addr='%s:%s' % (host, port)
			logging.debug ('connecting: %s' % addr)
			if self.emit('onConnecting', addr):
				newsock.send('$Lock %s|$HubName %s|<HUB> Hub is powered by ViperHive [ http://dc.hovel.ru http://code.google.com/p/viperhive/ ]|' % ( self.LOCK , self.core_settings['hubname'].encode(self.charset) ) )
				(sock, sw, sx)=select.select([newsock],[],[],15)
				
				logging.debug(repr(sock))

				if sock!=[]:
					newsock.settimeout(5.0)
					s=unicode(newsock.recv(4096),self.charset)
					supports=self.recp['Supports'].search(s)
					if supports!=None:
						supports=supports.group(0)
					else:
						supports=''
					#clisup=[]	
					validated=True
					logging.debug('Supports: %s' % supports)
					#if supports!=None:
					#	#Normal clients should support this
					#	supports=supports.group(0)
					#	logging.debug('client supports: %s' % supports)
					#	if self.recp['NoGetINFO'].search(supports)!=None:
					#		clisup.append('NoGetINFO')
					#	if self.recp['NoHello'].search(supports)!=None:
					#		clisup.append('NoHello')

					nick=self.recp['ValidateNick'].search(s)
					#checking nick
					# if nick == None => something like microdc2
					if nick==None:
						logging.debug('Old client: %s' %s)
						newsock.send('$Supports %s|' % self.SUPPORTS)
						(sock, sw, sx)=select.select([newsock],[],[],15)
						if sock!=[]:
							s+=unicode(newsock.recv(4096),self.charset)
							nick=self.recp['ValidateNick'].search(s)
						logging.debug('Old client full: %s' %s)
					
					#checking nick
					if nick!=None:
						nick=nick.group(0)
						logging.debug('validating: %s' % nick)

						if nick in self.reglist:
							# if user registred, and passwd is correct 
							# we should connect it even if it's already connected (drop & connect)
							
							newsock.send('$GetPass|')
							(sock, sw, sx)=select.select([newsock],[],[],15)
							if sock!=[]:
								s+=unicode(newsock.recv(4096),self.charset)
								passw=self.recp['MyPass'].search(s)
								if passw!=None:
									passw=passw.group(0)
									logging.debug('MyPass %s' % passw)
								
									if passw!=self.reglist[nick]['passwd']:
										logging.info('wrong pass')
										newsock.send(('<HUB> %s|' % (self._('Password incorrect. Provided: %s') % str(passw),)).encode(self.charset))
										newsock.send('$BadPass|')
										validated=False
									else:
										if nick in self.nicks:
											logging.debug('reconnecting identified user')
											try:
												self.nicks[nick].descr.send('<HUB> youre connecting from different machine. bye.|')
											except:
												pass
											self.drop_user_by_nick(nick)
								else:
									validated=False
							else:
								validated=False

						else:
						# if nick in self.reglist
						#nick is not registred
							if nick in self.nicks:
								newsock.send('ValidateDenie')
								validated=False
							else:
								validated=True
					else:
						validated=False

					if validated:
						logging.debug ('validated %s' % nick)
						newsock.send('$Hello %s|' %  nick.encode(self.charset))
						newsock.send('$Supports %s|' % self.SUPPORTS)
						#for i in self.hello:
						#	i.send('$Hello %s|' %  nick)
						k=3
						while (not 'MyINFO' in s) and (k>0):
							(sock, sw, sx)=select.select([newsock],[],[],15)
							if sock!=[]:
								s+=unicode(newsock.recv(4096),self.charset)
							k=k-1

						info=self.recp['MyINFO'].search(s)
						if info!=None:
							tr=True
							info=info.group(0)
							try:
								user=DCUser(info,newsock,addr)
							except:
								logging.warning( 'wrong myinfo from: %s addr: %s info: %s %s' % ( nick, addr, info, trace() ) )
								tr=False
							if tr:
								if nick in self.reglist:
									user.level=self.reglist[nick]['level']
								else:
									user.level='unreg'
								self.nicks[nick]=user
								self.addrs[addr]=user
								try:
									# --- APPLY LIMITS ---

									if user.share < self.core_settings['min_share'] and user.level not in self.core_settings['pass_limits']:
										newsock.send( (self._( '<HUB> Too low share. Min share is %s.|' ) % number_to_human_size( self.core_settings['min_share'] ) ).encode( self.charset ) )
										logging.debug('not validated. dropping')
										self.drop_user(addr, nick, newsock)
										return

									if user.sum_hubs > self.core_settings['max_hubs'] and user.level not in self.core_settings['pass_limits']:
										newsock.send( (self._( '<HUB> Too many hubs open. Max hubs is %s.|' ) % self.core_settings['max_hubs']).encode( self.charset ) )
										logging.debug('not validated. dropping')
										self.drop_user(addr, nick, newsock)
										return

									if user.slots < self.core_settings['min_slots'] and user.level not in self.core_settings['pass_limits']:
										newsock.send( (self._( '<HUB> Too few slots open. Min slots is %s.|' ) % self.core_settings['min_slots']).encode( self.charset ) )
										logging.debug('not validated. dropping')
										self.drop_user(addr, nick, newsock)
										return

									logging.debug('slots: %s, hubs: %s' % (user.slots, user.hubs) )


										

									if self.emit('onConnected',user):
										logging.debug('Validated. Appending.')
										
										free=None # No free workers
										for i, val in enumerate(self.descriptors): # Search for  free worker
											if len(val)<self.WORKER_MAX:
												val.append(newsock)
												free=i
												break
										if free==None:
											#adding worker
											logging.info('Many users. Appending worker')
											self.descriptors.append([newsock])
											try:
												newthread=(threading.Thread(None,self.clientserv,'worker',(len(self.descriptors)-1,)))
												logging.debug(newthread.getName())
												newthread.setDaemon(True)
												newthread.start()
											except:
												logging.error(trace())
											self.clthreads.append(newthread)
												
										
										if user.level in self.oplevels:
											self.send_to_all(self.get_op_list())

										if not 'NoHello' in supports:
											self.hello.append(newsock)
										
										if not 'NoGetINFO' in supports:
											newsock.send(self.get_nick_list().encode( self.charset ))
											#newsock.send(self.get_op_list().encode( self.charset ))
										else:
											for i in self.nicks.values():
												newsock.send(i.MyINFO.encode(self.charset)+"|")
												newsock.send(self.get_op_list().encode(self.charset))
										self.send_to_all(info+"|")
										
										uips=self.get_userip_acc_list()

										if ('UserIP' in supports) or ('UserIP2' in supports):
											self.send_to_nick(nick, '$UserIP %s %s$$|' %(nick, user.get_ip()))
											if user.level in self.core_settings['userip']:
												self.send_to_nick(nick, self.get_userip_list())
										
										for unick in uips:
											self.send_to_nick(unick, '$UserIP %s %s$$|' %(nick, user.get_ip()))


										self.send_usercommands_to_nick(nick)
										self.send_to_nick(nick, '$HubTopic %s|' % self.core_settings['topic'])
										

										#logging.debug (repr(self.nicks))
										#logging.debug (repr(self.addrs))
									else:
										logging.debug('not validated. dropping')
										self.drop_user(addr, nick, newsock)
								except:
									logging.debug('error while connect: %s' % trace())
									self.drop_user(addr, nick, newsock)
						else:
							logging.debug('no MyINFO recived\n recived: %s' % s)
							newsock.close()
					else:
						logging.debug('not validated nick. dropping.')
						newsock.close()
				else:
					logging.debug('timeout: %s' % addr)
					newsock.send('login timeout')
					newsock.close()
			else:
				logging.debug('Connectin not allowed by plugins')
			logging.debug('handheld complite with %s' % nick)
		except:
			logging.debug('Unexpected error: %s' % trace())
		return



	def drop_user_by_addr(self,addr):
		if addr in self.addrs:
			sock=self.addrs[addr].descr
			nick=self.addrs[addr].nick
			self.drop_user(addr,nick,sock)

	def drop_user(self,addr,nick,sock):
		logging.debug('dropping %s %s %s' % (addr, nick, sock))
		try:
			for i in self.descriptors:
				if sock in i: i.remove(sock)
			self.addrs.pop(addr,'')
			self.nicks.pop(nick,'')
			if sock in self.hello: self.hello.remove(sock)
			sock.close()
		except:
				logging.debug('something wrong while dropping client %s' % trace())
		logging.debug ('Quit %s' % nick)
		self.send_to_all('$Quit %s|' % nick)
		self.emit('onUserLeft',addr,nick)

	def drop_user_by_nick(self,nick):
		if nick in self.nicks:
			sock=self.nicks[nick].descr
			addr=self.nicks[nick].addr
			self.drop_user(addr,nick,sock)

	def drop_user_by_sock(self, sock):
		A=None
		N=None

		for nick, user in self.nicks.items():
			if user.descr==sock:
				N=nick

		for addr, user in self.addrs.items():
			if user.descr==addr:
				A=addr

		self.drop_user(A,N,sock)


	def send_to_all(self, msg, omitSock=None):
		logging.debug('sending to all %s' % msg)
		if not (len(msg)>0 and msg[-1]=="|"):
			msg=msg+"|"
		for part in self.descriptors:
			for sock in part:
				if sock!=self.srvsock and sock!=omitSock:
					try:
						sock.send(msg.encode(self.charset))
					except:
						logging.debug('socket error %s' % trace())
						self.drop_user_by_sock( sock )

	def send_pm_to_nick(self,fnick,nick,msg):
		self.send_to_nick(nick,'$To: %s From: %s $<%s> %s|' % (nick, fnick, fnick, msg))

	def send_to_nick(self,nick,msg):
		if nick in self.nicks:
			if not (len(msg)>0 and msg[-1]=="|"):
					msg=msg+"|"
			try:
				logging.debug('senging %s to %s' % (msg, nick))
				self.nicks[nick].descr.send(msg.encode(self.charset))
			except:
				logging.debug('Error while sending %s to %s. Dropping. %s' % (msg,nick,trace()))
				self.drop_user_by_nick(nick)
				logging.debug('socket error %s. user lost!' % trace() )
		else:
			logging.warning('send to unknown nick: %s' % nick)

	def send_to_addr(self,addr,msg):
		if addr in self.addrs:
			if not (len(msg)>0 and msg[-1]=="|"):
				msg=msg+"|"
			try:
				self.addrs[addr].descr.send(msg.encode(self.charset))
			except:
				logging.debug('socket error %s' % trace())
		else:
			logging.warning('uknown addres: %s' % addr)

	def get_nick_list( self ):
		nicklist="$NickList "
		oplist="$OpList "
		for user in self.nicks.values():
			nicklist+=user.nick+"$$"
			if user.level in self.oplevels:
				oplist+=user.nick+"$$"
		
		return "%s|%s|" % (nicklist[:-2], oplist[:-2])
	def get_op_list(self):
		#repeat some code for faster access
		oplist="$OpList "
		for user in self.nicks.values():
			if user.level in self.oplevels:
				oplist+=user.nick+"$$"
		#return "%s|" % (oplist[:-2],)
		return oplist+'|'

	def get_userip_list( self ):
		uip='$UserIP '
		for user in self.nicks.values():
			uip+='%s %s$$' % (user.nick, user.get_ip())
		return uip+'|'
	def get_userip_acc_list(self):
		uip=[]
		for user in self.nicks.values():
			if user.level in self.core_settings['userip']:
				uip.append(user.nick)
		return uip

	def save_settings(self):
		logging.debug('saving settigs')
		try:
			for mod, sett in self.settings.items():
				try:
					logging.info('saving settings for %s' % mod)
					f=open(self.path_to_settings+'/'+mod+'.yaml','wb')
					f.write(yaml.safe_dump(sett,default_flow_style=False,allow_unicode=True))
				except:
					logging.error('fail to load settings for module %s. cause:' % mod)
					logging.error('%s' %  trace())
					return False

		except:
			logging.error('!!! SETTINGS NOT SAVED !!!')
			return False
		return True


	def load_settings(self):
		logging.debug('reading settigs')
		try:
			for i in os.listdir(self.path_to_settings):
				if self.recp['.yaml'].search(i)!=None:
					mod=self.recp['before.yaml'].search(i).group(0)
					logging.debug('loading settings for %s' % mod)
					try:
						f=codecs.open(self.path_to_settings+'/'+ i,'r','utf-8')
						text=f.read()
						dct=yaml.load(text)
						if dct!=None:
								self.settings[mod]=dct
					except:
						logging.error('fail to load settings for module %s. cause:' % mod)
						logging.error('%s' %  trace())
		except:
			logging.error('error while loading settings: %s', trace())
				

	def check_rights(self, user, command):
		rights=self.privlist.get(user.level,[])
		if ('*' in rights) or (command in rights):
			return True
		else:
			return False

	
	def send_usercommands_to_nick(self, nick):
		for i in range(1,4):
			self.send_to_nick(nick, '$UserCommand 255 %s |' % i)
		for name, cmd in self.usercommands.items():
			if self.check_rights(self.nicks[nick],name):
				self.send_to_nick(nick, cmd)

	def send_usercommands_to_all(self):
		for nick in self.nicks.keys():
			self.send_usercommands_to_nick(nick)


	def on_exit(self):
		self.work=False
		self.save_settings()
		sys.exit()


	# COMMANDS
		
		#  -- Hub Control

	def Quit(self,addr,params=[]):
		self.work=False
		exit
		return True
		
	def Set(self,addr,params=[]): # Setting param for core or plugin
		# Params should be: 'core/plugin name' 'parameter' 'value'
		# Cause 'value' can contain spaces - join params[2:]
		if len(params)<2:
			return self._('Params error')
		try:
			value=yaml.load(" ".join(params[2:]))
			self.settings[params[0]][params[1]]=value
			return self._('Settings for %s - %s setted for %s') % (params[0], params[1], value)
		except:
			return self._('Error: %s') % trace()
	
	def Get(self,addr, params=[]): #Getting params or list
		# Params can be 'core/plugin name' 'parameter' or 'core/plugin name'
		if len(params)==0:
			return self._(' -- Aviable settings --:\n%s' ) % (unicode(yaml.safe_dump(self.settings.keys(),allow_unicode=True),'utf-8'))

		elif len(params)==1:
			if params[0] in self.settings:
				return self._(' -- Settings for %s --\n%s' ) % (params[0], unicode(yaml.safe_dump(self.settings.get(params[0],''),allow_unicode=True),'utf-8'))
			elif len(params)==2:
				if params[0] in self.settings and params[1] in self.settings[params[0]]:
					return self._(' -- Settings for %s - %s --\n%s' ) % ( params[0], params[1], unicode(yaml.safe_dump(self.settings[params[0]][params[1]],allow_unicode=True),'utf-8'))
				else:
					return self._('Params error')
			else:
				return self._('Params error')

	def Save(self, params=[]):
		try:
			self.save_settings()
			return True
		except:
			return False

		
	def RegenMenu( self, params = [] ):
		try:
			self.Gen_UC()
			self.send_usercommands_to_all()
			return True
		except:
			return False

	def ReloadSettings( self, params = [] ):
		try:
			self.load_settings()
		except:
			return False
		return True

	# --- User Control
	def AddReg(self,addr,params=[]):
		# Params should be: 'nick' 'level' 'passwd'
		if len(params)==3:
			# Check if 'nick' already registred
			if params[0] not in self.reglist:
				self.reglist[params[0]]={'level': params[1],'passwd':params[2]}
				return self._('User Registred:\n nick: %s\n level: %s\n passwd:%s') % (params[0],params[1],params[2])
			else:
				return self._('User already registred')
		else:
			return self._('Params error.')

	def DelReg(self,addr,params=[]):
		# Params should be 'nick'
		if len(params)==1:
			# Check if 'nick' registred
			if params[0] in self.reglist:
				if params[0] not in self.protected:
					del self.reglist[params[0]]
					return self._('User deleted')
				else:
					return self._('User protected!')

			else:
				return self._('User not registred')
		else:
			return self._('Params error')

	def ListReg(self,addr):
		s=self._('--- REGISTRED USERES --- \n')
		for nick, param in self.reglist.items():
			s=s+('nick: %s level: %s' % (nick, param['level'],))+'\n'
		return s
		#return self._('--- REGISTRED USERES --- \n') + "\n".join('nick: %s level: %s' % (nick, param['level'],) for nick, param in self.reglist.iteritems())


	def SetLevel(self,addr,params=[]):
		# Params should be: 'nick' 'level'
		if len(params)==2:
			if params[0] in self.reglist:
				self.reglist[params[0]]['level']=yaml.load(params[1])
				return self._('Success')
			else:
				return self._('No such user')
		else:
			return self._('Params error.')



	def Kick (self, addr, params=[]):
		# Params should be: 'nick'

		if len(params)==1:
			if params[0] in self.nicks:
				if self.nicks[params[0]].level in self.protected:
					return self._('User protected!')
				self.drop_user_by_nick(params[0])
				return self._('Success')
			else:
				return self._('No such user')
		else:
			return self._('Params error')


	# -- Help System

	def Help(self,addr,params=""):
		# Params can be empty or 'command'
		if len(params)==1:
			if self.check_rights(self.addrs[addr], params[0]):
				return self.help[params[0]]
			else:
				return self._('Premission denied')
				
		elif len(params)==0:
			ans=self._(' -- Aviable commands for you--\n')
			for cmd in self.commands.keys():
				if self.check_rights(self.addrs[addr],cmd):
					ans+='%s\n' % self.help.get(cmd,cmd)
			return ans
		else:
			return self._('Params error')

	# -- Plugin control

	def get_aviable_plugins( self ):
		ans = []
		try:
			for i in os.listdir(self.path_to_plugins):
				if self.recp['.py'].search(i)!=None and i!="__init__.py" and i!="plugin.py":
					mod=self.recp['before.py'].search(i).group(0)
					ans.append( mod )
			return ans
		except:
			logging.error('error while listing plugins: %s', trace())
		return None


	def ListPlugins(self,addr):
		logging.debug('listing plugins')
		ans = self._(' -- Aviable plugins --\n%s') % '\n'.join( self.get_aviable_plugins() )
		return ans

	def LoadPlugin(self,addr,params=[]):
		# Params should be: 'plugin'
		if len(params)==1:
			logging.debug('loading plugin %s' % params[0])
			if params[0] not in self.plugs:
				try:
					if 'plugins.'+params[0] not in sys.modules:
						plugins=__import__('plugins.'+params[0])
						plugin=getattr(plugins,params[0])
					else:
						plugin=reload(sys.modules['plugins.'+params[0]])
					logging.getLogger().setLevel(self.settings['core']['loglevel'])
					logging.debug('loaded plugin file success')
					cls=getattr(plugin,params[0]+'_plugin')
					obj=cls(self)
					self.plugs[params[0]]=obj
					self.commands.update(obj.commands)
					#self.usercommands.update(obj.usercommands)
					logging.debug( 'Plugin %s slots: %s' % (params[0], repr( obj.slots ) ) )
					for key,value in obj.slots.iteritems():
						logging.debug( 'Activating Slot: %s, on plugin %s' % ( key, params[0] ) )


						if key in self.slots:
							self.slots[key].append(value)
							
						else:
							self.slots[key]=[value]
					logging.debug( 'MessageMap: %s' % repr( self.slots ))

					self.Gen_UC()
					self.send_usercommands_to_all()
					return self._('Success')
				except:
					e=trace()
					logging.debug( 'Plugin load error: %s' % (e,) )
					return self._( 'Plugin load error: %s' % (e,) )
			else:
				return self._('Plugin already loaded')
		else:
			return self._('Params error')

	def UnloadPlugin(self,addr,params=[]):
			# Params should be: 'plugin'
			logging.debug('unloading plugin')
			if len(params)==1:
				try:
					if params[0] in self.plugs:
						plug=self.plugs.pop(params[0])
						plug.unload()
						for key in plug.commands.keys():
							self.commands.pop(key,None)
						for key in plug.usercommands.keys():
							self.usercommands.pop(key,None)
						for key, value in plug.slots.iteritems():
							if key in self.slots:
								if value in self.slots[key]:
									self.slots[key].remove(value)
						self.send_usercommands_to_all()
						return self._('Success')
					else:
						return self._('Plugin not loaded')
				except:
					return self._('Plugin unload error: %s' % trace())
			else:
				return self._('Params error')

	def ReloadPlugin(self, addr, params=[]):
		# Params 'plugin'
		return 'Unload: %s, Load %s' % (self.UnloadPlugin(addr, params), self.LoadPlugin(addr, params))
			
	def ActivePlugins(self,addr,params=[]):
		return self._(' -- ACTIVE PLUGINS -- \n')+"\n".join(self.plugs.keys())

	def Passwd(self,addr,params=[]):
		# Params 'nick'
		if len(params)>0:
			newpass=" ".join(params)
			nick=self.addrs[addr].nick
			if nick in self.reglist:
				self.reglist[nick]['passwd']=newpass
				return self._('Your password updated')
			else:
				return self._('You are not registred')

		else:
			return self._('Params error')
	def PasswdTo(self,addr,params=[]):
		# Params: 'nick' 'newpass'
		if len(params)>1:
			nick=params[0]
			newpass=" ".join(params[1:])
			if nick in self.reglist:
				if self.nicks[nick].level in self.protected:
						return self._('User protected!')
				self.reglist[nick]['passwd']=newpass
				return self._('User password updated')
			else:
					return self._('User not registred')

		else:
				return self._('Params error')
	
	def UI(self,addr,params=[]):
		# params: 'nick'

		if len(params)==1:
			user=self.nicks.get(params[0],None)
			if user!=None:
				return self._(' -- USER %s INFO --\n addres: %s\n level: %s\n is op?: %s\n is protected?: %s') % (user.nick, user.addr, user.level, repr(user.level in self.oplevels), repr(user.level in self.protected))
			else:
				return self._('No such user')
		else:
				return self._('Params error')

	def SetTopic(self,addr,params=[]):
		#params: ['topic']
		if len(params)>=1:
			topic=' '.join(params)
			self.core_settings['topic']=topic
			self.send_to_all('$HubTopic %s|' % topic)
			return self._('Success')
		else:
			return self._('Params error')







	# -- EXTENDED FUNCTIONS USED FOR SIMPLIFY SOME WRK

	def masksyms(self, str):
		''' return string with ASCII 0, 5, 36, 96, 124, 126 masked with: &# ;. e.g. chr(5) -> &#5; '''
		cds=[0, 5, 36, 96, 124, 126]
		for i in cds:
			str=str.replace(chr(i),'&#%s;' % i)

		return str

	def unmasksyms(self, str):
		''' return string with ASCII 0, 5, 36, 96, 124, 126 unmasked from: &# ; mask. e.g. &#5; -> chr(5) '''
		cds=[0, 5, 36, 96, 124, 126]
		for i in cds:
			str=str.replace('&#%s;' % i, chr(i))

		return str
			
			









				


#RUNNING HUB
if __name__=='__main__':
	hub=DCHub()
	hub.run()
