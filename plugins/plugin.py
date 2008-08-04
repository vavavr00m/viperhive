#!/usr/bin/env python


class plugin(object):
        
        commands={}
        slots={}
	usercommands={}
        hub=None
        def __init__(self,hub):
                self.hub=hub
