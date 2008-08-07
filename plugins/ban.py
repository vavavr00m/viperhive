#!/usr/bin/env python

# -- BAN PLUGIN
#
# Ban user by nick or ip
# 
# --

import plugin
import yaml
import datetime

class ban_plugin(plugin.plugin):
        
	def __init__(self, hub):
		super(ban_plugin,self).__init__(hub)

                if 'ban' not in self.hub.settings:
                        self.hub.settings['ban']={'nicks':{},'addrs':{}}

                self.banlist=self.hub.settings['ban']

                self.commands['Ban']=self.Ban
                self.commands['BanAddr']=self.BanAddr
                self.commands['BanNick']=self.BanNick
                self.commands['UnBanNick']=self.UnBanNick
                self.commands['UnBanAddr']=self.UnBanAddr
                self.commands['ListBans']=self.ListBans

                
                self.slots['onConnected']=self.onConnected

        def onConnected(self,user):
                if user.nick in self.banlist['nicks']:
                        if datetime.datetime.strptime(self.banlist['nicks'][user.nick]['expired'],'%Y-%m-%dT%H:%M:%S')>datetime.datetime.now():
                                return False
                        else:
                                self.banlist['nicks'].pop(user.nick)
                adr=user.addr.split(':')[0]
                if adr in self.banlist['addrs']:
                        if datetime.datetime.strptime(self.banlist['addrs'][adr]['expired'],'%Y-%m-%dT%H:%M:%S')>datetime.datetime.now():
                                return False
                        else:
                                self.banlist['addrs'].pop(adr)
                return True

        def Ban(self, addr, params):
                # params: 'nick' ('time') 'reason'
                if len(params)>=2:
                        if params[0] in self.hub.nicks:
                                baddr=self.hub.nicks[params[0]].addr.split(':')[0]

                                self.BanNick(addr, params)

                                params[0]=baddr
                                self.BanAddr(addr, params)
                                return self.hub._('Success')
                        else:
                                return self.hub._('No such nick')
                else:
                        return self.hub._('Params error: should be %s') % ('nick (time) reason')

        def BanAddr(self, addr, params):
                # params: addr (time) reason

                if len(params)>=2:
                        try:
                                bantime=float(params[1])
                                timeban=True
                        except:
                                timeban=False

                        if len(params)>2 and timeban:
                                # time ban
                                toban=(datetime.datetime.now()+datetime.timedelta(hours=bantime)).strftime('%Y-%m-%dT%H:%M:%S')
                                reason=" ".join(params[2:])
                        else:
                                # permanent ban
                                toban='never'
                                reason=" ".join(params[1:])

                        self.banlist['addrs'][params[0]]={'expired':toban,'reason':reason}

                        self.hub.drop_user_by_addr(params[0])

                        return self.hub._('Success')


                else:
                       return self.hub._('Params error: should be %s') % ('addr (time) reason') 

        def BanNick(self, addr, params):
                # params: nick (time) reason

                if len(params)>=2:

                        
                        try:
                                bantime=float(params[1])
                                timeban=True
                        except:
                                timeban=False

                        if len(params)>2 and timeban:
                                # time ban
                                toban=(datetime.datetime.now()+datetime.timedelta(hours=bantime)).strftime('%Y-%m-%dT%H:%M:%S')
                                reason=" ".join(params[2:]).decode(self.hub.charset)
                        else:
                                toban=(datetime.datetime.now()+datetime.timedelta(days=999999)).strftime('%Y-%m-%dT%H:%M:%S')
                                reason=" ".join(params[1:]).decode(self.hub.charset)

                        self.banlist['nicks'][params[0]]={'expired':toban,'reason':reason}

                        self.hub.drop_user_by_nick(params[0])

                        return self.hub._('Success')

                else:
                       return self.hub._('Params error: should be %s') % ('nick (time) reason') 

        def UnBanNick(self, addr, params):
                i=self.banlist['nicks'].pop(params[0],None)
                if i!=None:
                        return self.hub._('Success')
                else:
                        return self.hub._('Not Found')

        def UnBanAddr(self, addr, params):
                i=self.banlist['addrs'].pop(params[0],None)
                if i!=None:
                        return self.hub._('Success')
                else:
                        return self.hub._('Not Found')

        def ListBans(self, addr):
                return self.hub._(' -- Ban List --\n')+yaml.dump(self.hub.settings['ban'],default_flow_style=False)