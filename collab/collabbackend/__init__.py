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
        self.config.read(inifile)

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


# returns 1 if path has .htaccess with access to authuser
def checkAccess(user, path):
    try:
        f = open(os.path.join(path, ".htaccess"), "r")
    except IOError:
        return False
    for l in f:
        l = l.strip().decode("utf-8").split()
        if len(l) > 1:
            l[0] = l[0].lower()
            l[1] = l[1].lower()
        try:
            if l[0] == "require" and l[1] == "user":
                if user in l[2:]:
                    return True
            elif l[0] == "require" and l[1] == "valid-user":
                return True
        except IndexError:
            pass
    f.close()
    return False


def getActiveCollab(request):
    user = request.user.name
    active = request.cfg.interwikiname
    path = request.cfg.collab_basedir
    baseurl = request.cfg.collab_baseurl
    for collab in listCollabs(baseurl, user, path, active):
        if collab[4]:
            return collab

    return None


def listCollabs(baseurl, user, path, activeCollab, nocheck=False):
    collabs = []
    output = []

    try:
        files = os.listdir(path)
    except:
        files = []

    for shortName in files:
      if nocheck or checkAccess(user, os.path.join(path, shortName)):
          collabs.append(shortName)

    if not collabs:
        return []

    collabs.sort()

    for shortName in collabs:
        try:
            text = open(os.path.join(path, shortName, ".url")).read()
            link = text.strip().decode('utf-8')
        except IOError:
            link = baseurl
            link += shortName
            link += '/'

        try:
            text = open(os.path.join(path, shortName, ".title")).read()
            title = text.strip().decode('utf-8')
        except IOError:
            title = shortName.replace("_", " ")

        try:
            text = open(os.path.join(path, shortName, ".motd")).read()
            motd = text.strip().decode('utf-8')
        except IOError:
            motd = ""

        if shortName == activeCollab:
            output.append((shortName, title, motd, link, True))
        else:
            output.append((shortName, title, motd, link, False))

    output.sort(key=lambda x: x[1].lower())

    return output
