#!/usr/bin/env python


class plugin(object):
        
        commands={}
        slots={}
        hub=None
        def __init__(self,hub):
                self.hub=hub
