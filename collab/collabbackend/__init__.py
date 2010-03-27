# -*- coding: utf-8 -*-
"""
    @copyright: 2010 by Marko Laakso
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import ConfigParser
import sys
import os
import posixpath

from MoinMoin.server.server_wsgi import WsgiConfig, moinmoinApp

def scriptbasename(name):
    myname = posixpath.dirname(name)

    if myname == '/':
        return ''

    return myname


def pathbasename(name):
    return os.path.basename(os.path.dirname(os.path.abspath(name)))


def wsgiapplication(environ, start_response):
    environ['SCRIPT_NAME'] = scriptbasename(environ['SCRIPT_NAME'])
    return moinmoinApp(environ, start_response)


class MyWsgiConfig(WsgiConfig):
    pass


class CollabBackend(object):
    def __init__(self, inifile='/etc/local/collab/collab.ini'):
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/etc/local/collab/collab.ini')

        self._logconf = self.config.get('collab', 'logconf')
        self.wikidir = self.config.get('collab', 'wikidir')

        from MoinMoin import log
        log.load_config(self._logconf) 


class Collab(object):
    def __init__(self, myinfra, name):
        self.name = name
        self.instancedir = os.path.join(myinfra.wikidir, name)
        self.configdir = os.path.join(self.instancedir, 'config')
        sys.path.insert(0, self.configdir)

    def getwsgiconfig(self):
        self.config = MyWsgiConfig()
        return self.config

        
