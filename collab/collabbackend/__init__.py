# -*- coding: utf-8 -*-
"""
    @copyright: 2010-2011 by Marko Laakso
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import ConfigParser
import sys
import os
import posixpath

def scriptbasename(name):
    myname = posixpath.dirname(name)

    if myname == '/':
        return ''

    return myname


def pathbasename(name):
    return os.path.basename(os.path.dirname(os.path.abspath(name)))


def wsgiapplication(environ, start_response):
    environ['SCRIPT_NAME'] = scriptbasename(environ['SCRIPT_NAME'])
    from MoinMoin.wsgiapp import application
    return application(environ, start_response)


class CollabBackend(object):
    def __init__(self, inifile='/etc/local/collab/collab.ini'):
        self.config = ConfigParser.RawConfigParser()
        self.config.read('/etc/local/collab/collab.ini')

        self.wikidir = self.config.get('collab', 'wikidir')
        self.logconf = self.config.get('collab', 'logconf')


class Collab(object):
    def __init__(self, myinfra, name):
        self.name = name
        self.instancedir = os.path.join(myinfra.wikidir, name)
        self.configdir = os.path.join(self.instancedir, 'config')
        sys.path.insert(0, self.configdir)

	from MoinMoin import log
	log.load_config(myinfra.logconf)

    def getwsgiconfig(self):
        """
        Dummy config function to help with 1.8 -> 1.9 migration
        """
        return None
