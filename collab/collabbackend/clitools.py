# -*- coding: utf-8 -*-
"""
    @copyright: 2014 Ossi Salmi
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import os
import sys
import errno
import posix
import pwd

from collabbackend import CollabBackend

backend = CollabBackend()

from MoinMoin import log
log.load_config(backend.logconf)

import MoinMoin.web.contexts
from MoinMoin.user import User
from MoinMoin.config import multiconfig

from graphingwiki import RequestCLI


class CollabRequest(object):
    def __init__(self, collab=None, user=None, backend=backend):
        farmconf = backend.config.get("collab", "farmconf")
        self.farmconfdir = os.path.dirname(farmconf)
        self.request = None

        if collab:
            self.confdir = os.path.join(backend.wikidir, collab, "config")
        else:
            baseinstancedir = backend.config.get("collab", "baseinstancedir")
            self.confdir = os.path.join(baseinstancedir, "config")

        if not os.path.isdir(self.confdir):
            raise OSError(errno.ENOENT, "No such directory: " + self.confdir)

        if user:
            self.user = user
        else:
            self.user = pwd.getpwuid(posix.getuid())[0]

        sys.path.insert(0, self.confdir)

        multiconfig._url_re_cache = None
        multiconfig._farmconfig_mtime = None
        multiconfig._config_cache = {}

        import farmconfig
        reload(farmconfig)

        self.request = RequestCLI("FrontPage", parse=False)
        self.request.user = self.getUser(self.user)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        if self.request:
            self.request.finish()
            self.request = None
        if sys.path:
            if self.confdir in sys.path:
                sys.path.remove(self.confdir)
            if self.farmconfdir in sys.path:
                sys.path.remove(self.farmconfdir)

    def getUser(self, user):
        return User(self.request, auth_username=user)


def listAllCollabs(wikidir=backend.wikidir):
    collabs = list()

    for collab in os.listdir(wikidir):
        mydata = os.path.join(wikidir, collab)
        myconfig = os.path.join(mydata, "config", collab + ".py")
        if os.path.exists(myconfig):
            collabs.append(collab)

    return collabs
