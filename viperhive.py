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

logging.basicConfig(level=logging.DEBUG,stream=sys.stdout)

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

class DCUser:

	def __init__(self,myinfo="",descr=None,addr=None):
		
                self.nick=None
	        self.connection=None
	        self.flag=None
	        self.mail=None
	        self.share=None
	        self.descr=None
	        self.MyINFO=None
	        self.level=0
                
                if len(myinfo)>0:
			self.upInfo(myinfo)
		self.descr=descr
		self.addr=addr

                

	def upInfo(self,myinfo):
		self.MyINFO=myinfo
		ar=myinfo.split("$")
		ar2=ar[2].split(" ",2)
		self.nick=ar2[1]#nick
		self.description=ar2[2]
		self.connection=ar[4][0:-1]
		self.flag=ar[4][-1]
		self.mail=ar[5]


class DCHub:

       
	
        # CONSTANTS
        LOCK='EXTENDEDPROTOCOL_viperhive pk=version0.1-svn'
	SUPPORTS='NoHello NoGetINFO'
     

        def _(self,string):  # Translate function
                return self.lang.get(string,string)


    	def __init__( self ):

                # COMMANDS
	        self.commands={}
        
                # SIGNAL-SLOT EVENT SUBSYSTEM
        	self.slots={}
		

		# COMPILE REGEXPS
		self.recp={}
		self.recp['Key']=re.compile('(?<=\$Key ).*(?=[|])')
		self.recp['ValidateNick']=re.compile('(?<=\$ValidateNick ).*(?=[|])')
		self.recp['Supports']=re.compile('(?<=\$Supports ).*(?=[|])')
		self.recp['MyPass']=re.compile('(?<=\$MyPass ).*(?=[|])')
		self.recp['MyINFO']=re.compile('\$MyINFO .*(?=[|])')

		self.recp['NoGetINFO']=re.compile('NoGetINFO')
		self.recp['NoHello']=re.compile('NoHello')

		self.recp['.yaml']=re.compile('\.yaml$')
                self.recp['before.yaml']=re.compile('.*(?=\.yaml)')
                self.recp['.py']=re.compile('\.py$')
                self.recp['before.py']=re.compile('.*(?=\.py)')
                

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
		defcore_settings['port']=1411
		defcore_settings['hubname']='Panter powered hub'
		defcore_settings['cmdsymbol']='!'
		defcore_settings['OpLevels']=['owner']
                defcore_settings['Lang']='ru.cp1251'
                defcore_settings['autoload']=['motd']
                defcore_settings['loglevel']=10

		defreglist={'admin':{'level':'owner', 'passwd':'megapass'}}


		defprivlist={'*':['owner']}

		# If loaded core_settings miss some stuff - load defaults
                if len(self.core_settings)==0:
                        self.settings['core']=self.core_settings={}

		for i in defcore_settings.iterkeys():
			if not i in self.core_settings:
				self.core_settings[i]=defcore_settings[i]

		if len(self.reglist)==0:
			self.settings['reglist']=self.reglist=defreglist
		
		if len(self.privlist)==0:
			self.settings['privlist']=self.privlist=defprivlist

		# MORE SHORTCUTS
		self.oplevels=self.core_settings['OpLevels']

		self.KEY=lock2key(self.LOCK)

                # ---- SOCKETS ----

        	self.srvsock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        	self.srvsock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        	self.srvsock.bind( ("",self.core_settings['port']) )
        	self.srvsock.listen( 5 )
        	self.descriptors = [self.srvsock]

		# User hashes
		self.nicks={}
		self.addrs={}

		# Support for very, VERY old clients
		self.hello=[]
		self.getinfo=[]
		
		self.threads=[]

		
                # Reinitialize Logging

                logging.basicConfig(level=self.settings['core']['loglevel'])



		# REGISTERING CORE COMMANDS
		self.commands['Quit']=self.Quit
                self.commands['AddReg']=self.AddReg
                self.commands['DelReg']=self.DelReg
                self.commands['ListReg']=self.ListReg
                self.commands['Get']=self.Get
                self.commands['Set']=self.Set
		self.commands['SetLevel']=self.SetLevel
                self.commands['Help']=self.Help
                self.commands['ListPlugins']=self.ListPlugins
                self.commands['LoadPlugin']=self.LoadPlugin
                self.commands['UnloadPlugin']=self.UnloadPlugin
                self.commands['ActivePlugins']=self.ActivePlugins
                self.commands['Save']=self.Save
                self.commands['ReloadPlugin']=self.ReloadPlugin
                self.commands['RP']=self.ReloadPlugin

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
						#	arr[key]=value.encode(cpage)

						self.lang.update(arr)
					except:
						logging.error('file %s in wrong format: %s' % ((lpath+i), traceback.format_exc()))
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
                                                        logging.error('file %s in wrong format: %s' % ((lpath+i), traceback.format_exc()))
                except:
                        logging.error('language directory not found %s' % (traceback.format_exc()))

		
                logging.info('Language loaded: %s strings' % str(len(self.lang)))
                logging.info('Help loaded: %s strings' % str(len(self.help)))

                # USERCOMMANDS
	        self.usercommands={}


                # PLUGINS
                self.plugs={}

                # AUTOLOAD PLUGINS
                for i in self.core_settings['autoload']:
                        self.LoadPlugin(None,[i])

        	logging.info ('Hub ready to start on port %s...' % self.core_settings['port'])


        # SIGNAL-SLOT SUBSYSTEM EMITTER
	def emit(self,signal,*args):
		#logging.debug('emitting %s' % signal)
		#logging.debug('emit map %s' % repr(self.slots))
		for slot in self.slots.get(signal,[]):
                        try:
                                if not slot(*args):
                                        return False
                        except:
                                logging.error('PLUGIN ERROR: %s' % traceback.format_exc())
		return True

        def run( self ):
                logging.info ('Hub started!')
		try:
			self.work=True
			while self.work:
				(sread, swrite, sexc) = select.select( self.descriptors, [], [], 1 )

				for thr in self.threads[:]:
					if not thr.isAlive():
						self.threads.remove(thr)
				# Iterate through the tagged read descriptors
				for sock in sread:
					# Received a connect to the server (listening) socket
					if sock == self.srvsock:
						# self.accept_new_connection()
                                                # Start new thread to avoid hub lock when user connecting
                                                thread.start_new_thread(self.accept_new_connection,())
					else:
                                                try:
                                                        # Received something on a client socket
                                                        str = unicode(sock.recv(4096), self.charset)
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
                                                                        str=str+unicode(sock.recv(4096),self.charset)
                                                                        i-=1
                                                                # --

                                                                host,port = sock.getpeername()
                                                                addr = '%s:%s' % (host, port)
                                                                logging.debug ('recived: %s from %s' % (str, addr))
                                                                if str[-1]=="|":
                                                                        if self.emit('onRecivedSomething',addr):
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
                                                                        logging.warning ('Too big or wrong message recived from %s: %s' % (addr,s))
                                                except:
                                                        self.drop_user_by_sock(sock)
                                                        logging.error(traceback.format_exc()) 

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
						logging.warning('Wrong MyINFO by: %s with addr %s' (acmd[2],addr))
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

		else:
			logging.debug('Unknown protocol command: %s from: %s' % (cmd,addr))


	def parse_cmd(self,cmd,addr):
		logging.debug('command recived %s' % cmd)
                #cmd=self.decode(cmd)
		acmd=cmd.split(' ')

		if self.check_rights(self.addrs[addr],acmd[0]):
			if acmd[0] in self.commands:
				try:
					if (len(acmd[1:]))>0:
						result=self.commands[acmd[0]](addr,acmd[1:])
					else:
						result=self.commands[acmd[0]](addr)
                                        if result!='':
                                                self.send_to_addr(addr,self._('<HUB> %s|') % result)

				except SystemExit:
					raise SystemExit

				except:
					self.send_to_addr(addr,self._('<HUB> Error while proccessing command %s|') % traceback.format_exc())
			else:
				self.send_to_addr(addr,self._('<HUB> No such command'))
		else:
			self.send_to_addr(addr,self._('<HUB> Premission denied'))



	def parse_chat_msg(self,msg,addr):
		acmd=msg.split(' ',1)
		if len(acmd)==2:
			if acmd[0][1:-1]==self.addrs[addr].nick:
				if acmd[1][0]==self.core_settings['cmdsymbol']:
					thread.start_new_thread(self.parse_cmd,(acmd[1][1:],addr,))
				else:
					if self.emit('onMainChatMsg',acmd[0][1:-1],acmd[1]):
						self.send_to_all(msg+"|")
			else:
				logging.warning('user tried to use wrong nick in MC. Real nick: %s. Message: %s' % (self.addrs[addr].nick, msg))
				self.drop_user_by_addr(addr)


        def accept_new_connection( self ):
		try:
			newsock, (host, port) = self.srvsock.accept()
			addr='%s:%s' % (host, port)
			logging.debug ('connecting: %s' % addr)
			if self.emit('onConnecting', addr):
				newsock.send('$Lock %s|$HubName %s|' % ( self.LOCK , self.core_settings['hubname'].encode(self.charset) ) )
				(sock, sw, sx)=select.select([newsock],[],[],15)
				
				logging.debug(repr(sock))

				if sock!=[]:
					s=unicode(newsock.recv(4096),self.charset)
					supports=self.recp['Supports'].search(s)
					clisup=[]	
					validated=True

					if supports!=None:
						#Normal clients should support this
						supports=supports.group(0)
						logging.debug('client supports: %s' % supports)
						if self.recp['NoGetINFO'].search(supports)!=None:
							clisup.append('NoGetINFO')
						if self.recp['NoHello'].search(supports)!=None:
							clisup.append('NoHello')

					nick=self.recp['ValidateNick'].search(s)
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
										logging.debug('wrong pass')
										newsock.send('$BadPass|')
										validated=False
									else:
										if nick in self.nicks:
											logging.debug('reconnecting identified user')
											self.nicks[nick].descr.send('<HUB> youre connecting from different machine. bye.|')
											self.drop_user_by_nick(nick)
								else:
									validated=False
							else:
								validated=False

						else: # if nick in self.reglist
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
						for i in self.hello:
							i.send('$Hello %s|' %  nick)
						if not 'MyINFO' in s:
							(sock, sw, sx)=select.select([newsock],[],[],15)
							if sock!=[]:
								s+=unicode(newsock.recv(4096),self.charset)
						info=self.recp['MyINFO'].search(s)
						if info!=None:
							tr=True
							info=info.group(0)
							try:
								user=DCUser(info,newsock,addr)
							except:
								logging.warning('wrong myinfo from: %s addr: %s info: %s ' % (nick, addr, info))
								tr=False
							if tr:
                                                                if nick in self.reglist:
                                                                        user.level=self.reglist[nick]['level']
                                                                else:
                                                                        user.level='unreg'
                                                                self.nicks[nick]=user
                                                                self.addrs[addr]=user
                                                                try:
                                                                        if self.emit('onConnected',user):
                                                                                self.descriptors.append( newsock )

                                                                                
                                                                                if nick in self.oplevels:
                                                                                        self.send_to_all(self.get_op_list())

                                                                                if not 'NoHello' in clisup:
                                                                                        self.hello.apppend(newsock)
                                                                                
                                                                                if not 'NoGetINFO' in s:
                                                                                        newsock.send(self.get_nick_list())
                                                                                else:
                                                                                        for i in self.nicks.itervalues():
                                                                                                newsock.send(i.MyINFO.encode(self.charset)+"|")
                                                                                                newsock.send(self.get_op_list().encode(self.charset))
                                                                                self.send_to_all(info+"|")
                                                                                
                                                                                

                                                                                self.send_usercommands_to_nick(nick)
                                                                                        #logging.debug (repr(self.nicks))
                                                                                        #logging.debug (repr(self.addrs))
                                                                        else:
                                                                                self.drop_user(addr, nick, newsock)
                                                                except:
                                                                        self.drop_user(addr, nick, newsock)
						else:
							newsock.close()
					else:
						newsock.close()
				else:
					logging.debug('timeout: %s' % addr)
					newsock.send('login timeout')
					newsock.close()
			return
		except:
			logging.error('Unexpected error: %s' % traceback.format_exc())



	def drop_user_by_addr(self,addr):
                if addr in self.addrs:
                        sock=self.addrs[addr].descr
                        nick=self.addrs[addr].nick
                        self.drop_user(addr,nick,sock)

	def drop_user(self,addr,nick,sock):
                try:
                        if sock in self.descriptors: self.descriptors.remove(sock)
                        self.addrs.pop(addr)
                        self.nicks.pop(nick)
                        if sock in self.hello: self.hello.remove(sock)
                        sock.close
                except:
                        logging.error('something wrong while dropping client %s' % traceback.format_exc())
                logging.debug ('Quit %s' % nick)
                self.send_to_all('$Quit %s|' % nick)

	def drop_user_by_nick(self,nick):
                if nick in self.nicks:
                        sock=self.nicks[nick].descr
                        addr=self.nicks[nick].addr
                        self.drop_user(addr,nick,sock)

        def drop_user_by_sock(self, sock):
                A=None
                N=None

                for nick, user in self.nicks.iteritems():
                        if user.descr==sock:
                                N=nick

                for addr, user in self.addrs.iteritems():
                        if user.descr==addr:
                                A=addr

                self.drop_user(A,N,sock)


	def send_to_all(self, msg, omitSock=None):
		logging.debug('sending to all %s' % msg)
                if not (len(msg)>0 and msg[-1]=="|"):
                                msg=msg+"|"
		for sock in self.descriptors:
			if sock!=self.srvsock and sock!=omitSock:
				try:
					sock.send(msg.encode(self.charset))
				except:
					logging.error('socket error %s' % traceback.format_exc())

	def send_to_nick(self,nick,msg):
		if nick in self.nicks:
                        if not (len(msg)>0 and msg[-1]=="|"):
                                msg=msg+"|"
			try:
				logging.debug('senging %s to %s' % (msg, nick))
				self.nicks[nick].descr.send(msg.encode(self.charset))
			except:
				logging.error('socket error %s' % traceback.format_exc() )
		else:
			logging.warning('send to unknown nick: %s' % nick)

	def send_to_addr(self,addr,msg):
		if addr in self.addrs:
                        if not (len(msg)>0 and msg[-1]=="|"):
                                msg=msg+"|"
			try:
				self.addrs[addr].descr.send(msg.encode(self.charset))
			except:
				logging.error('socket error %s' % traceback.format_exc())
		else:
			logging.warning('uknown addres: %s' % addr)

	def get_nick_list(self):
		nicklist="$NickList "
		oplist="$OpList "
		for user in self.nicks.itervalues():
			nicklist+=user.nick+"$$"
			if user.level in self.oplevels:
				oplist+=user.nick+"$$"
		
		return "%s|%s|" % (nicklist[:-2], oplist[:-2])
	def get_op_list(self):
		#repeat some code for faster access
		oplist="$OpList "
		for user in self.nicks.itervalues():
			if user.level in self.oplevels:
				oplist+=user.nick+"$$"
		return "%s|" % (oplist[:-2],)
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
					logging.error('%s' %  traceback.format_exc())
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
                                                logging.error('%s' %  traceback.format_exc())
		except:
			logging.error('error while loading settings: %s', traceback.format_exc())
				

	def check_rights(self, user, command):
		if (user.level in self.privlist.get('*',[])) or (user.level in self.privlist.get(command,[])):
			return True
		else:
			return False

	
	def send_usercommands_to_nick(self, nick):
                for i in range(1,4):
			self.send_to_nick(nick, '$UserCommand 255 %s |' % i)
		for name, cmd in self.usercommands.iteritems():
			if self.check_rights(self.nicks[nick],name):
				self.send_to_nick(nick, cmd)

	def send_usercommands_to_all(self):
		for nick in self.nicks.iterkeys():
			self.send_usercommands_to_nick(nick)


	def on_exit(self):
                self.save_settings()


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
                        return self._('Error: %s') % traceback.format_exc()
        
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

        def Save(self, params):
                try:
                        self.save_settings()
                        return True
                except:
                        return False

        
        # -- User Control

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
                                del self.reglist[params[0]]
                                return self._('User deleted')

                        else:
                                return self._('User not registred')
                else:
                        return self._('Params error')

        def ListReg(self,addr):
                return self._('--- REGISTRED USERES --- \n') + "\n".join('nick: %s level: %s' % (nick, param['level'],) for nick, param in self.reglist.iteritems())
	

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
                        if  (self.addrs[addr].level in self.privlist.get('*',[])):
                                return ans+"\n".join(self.help.get(key, key) for key in self.commands.iterkeys())
                        else:
                                for key in self.commands.iterkeys():
                                      if (self.addrs[addr].level in self.privlist.get(key,[])):
                                              ans+='%s\n\n' % self.help.get(key,key)
                                return ans
                else:
                        return self._('Params error')

        # -- Plugin control

        def ListPlugins(self,addr):
                logging.debug('listing plugins')
                ans=' -- Aviable plugins --\n'
		try:
			for i in os.listdir(self.path_to_plugins):
                                if self.recp['.py'].search(i)!=None and i!="__init__.py" and i!="plugin.py":
                                        mod=self.recp['before.py'].search(i).group(0)
                                        ans+="%s\n" % mod
                        return ans
		except:
			logging.error('error while listing plugins: %s', traceback.format_exc())

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

				       
				       cls=getattr(plugin,params[0]+'_plugin')
				       obj=cls(self)
					
				       self.plugs[params[0]]=obj
				       self.commands.update(obj.commands)
				       self.usercommands.update(obj.usercommands)
					
				       for key,value in obj.slots.iteritems():
					       if key in self.slots:
						       self.slots[key].append(value)
					       else:
						       self.slots[key]=[value]


				       self.send_usercommands_to_all()

				   

				       return self._('Success')
			       except:
				       return self._('Plugin load error: %s' % (traceback.format_exc()))
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

                                        for key in plug.commands.iterkeys():
                                                self.commands.pop(key,None)

					for key in plug.usercommands.iterkeys():
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
                                return self._('Plugin unload error: %s' % traceback.format_exc())
                else:
                        return self._('Params error')

        def ReloadPlugin(self, addr, params=[]):
                return 'Unload: %s, Load %s' % (self.UnloadPlugin(addr, params), self.LoadPlugin(addr, params))
				
        def ActivePlugins(self,addr=[]):
                return self._(' -- ACTIVE PLUGINS -- \n')+"\n".join(self.plugs.iterkeys())

                    


#RUNNING HUB
if __name__=='__main__':
	hub=DCHub()
	hub.run()
