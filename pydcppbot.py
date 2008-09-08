
# -*- coding: utf-8 -*-
# Based on Apkawa's PyDC++ bot
# Currently used for viperhive stability testing.
# Emulate numerous client connections.
import socket, re, time
import traceback
import thread

class dcpp(object):
	def __init__(self,HOST, PORT, NICK, PASS=None, DESCR='PYDCPPBOT', TAG='<PyDC++BOT V:0.002>', SHARE=0):
		self.HOST=HOST
		self.PORT=PORT
		self.NICK=NICK
		self.DESCR=DESCR
		self.TAG=TAG
		self.SHARE=SHARE
		self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.connect((HOST,PORT))
		lock=self.sock.recv(1024)
		lock_key=re.findall('\$Lock[\s](.*?)[\s]', lock)[0]
		key =self._createKey(lock).encode("utf-8")
		self.sock.send('$Key %s|$ValidateNick %s|'%(key,NICK))
		print self.view_chat()
		if PASS == None:
			self.sock.send('$Version 1,0091|$GetNickList|$MyINFO $ALL %s %s%s$ $0$$%s$|' %(NICK,DESCR,TAG,SHARE))
		else: 
			self.sock.send('$Version 1,0091|\
			$MyPass %s\
			|$GetNickList\
			|$MyINFO $ALL %s %s%s$ $0$$%s$|' %(PASS,NICK,DESCR,TAG,SHARE))
			
	def close(self):
		self.sock.close()
	def view_chat(self):
		return  (self.sock.recv(2048))
	def raw_view(self):
		self.sock.recv(2048)
	def send_mainchat(self, text):
		text=('<%s> %s|'%(self.NICK,text))
		self.sock.send(text)
	def send_pm(self,to,text):
		text=('$To: %s From: %s $<%s> %s|'%(to,self.NICK,self.NICK,text))
		self.sock.send(text)
		
	def drop_msgs(self):
		while True:
			self.view_chat()
		
	def _createKey(self,lock):
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

class dcppbot (dcpp):
	def __init__(self,HOST, PORT, NICK, PASS=None, DESCR='PYDCPPBOT', TAG='<PyDC++BOT V:0.002>', SHARE=0):
		super(dcppbot,self).__init__(HOST, PORT, NICK, PASS, DESCR, TAG, SHARE)


	
#HE WE ARE. LAUNCHING...	
if __name__=='__main__':
	k=[]
	for i in xrange(0,10):
		try:
			dc=dcppbot('localhost', 411, '%s' % i)
			thread.start_new_thread(dc.drop_msgs,())
			k.append(dc)
			print(len(k))
			time.sleep(0.1)
		except:
			print(len(k))
			print(traceback.format_exc())
			
			
	while True:
		#pass
		time.sleep(100)
		
		

				
				
				
