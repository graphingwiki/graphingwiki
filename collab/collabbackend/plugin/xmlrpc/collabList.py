# -*- coding: utf-8 -*-"
"""
    CollabList xmlrpc plugin to MoinMoin
     - Lists collaborations user has access to

    @copyright: 2007-2010 by Timo Mäkinen,
                             Marko Laakso <fenris@iki.fi> and
                             Mika Seppänen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

Dependencies = ['myfilesystem']

import os

# returns 1 if path has .htaccess with access to authuser
def checkAccess(user, path):
    try:
        f = open(os.path.join(path, ".htaccess"), "r")
    except IOError:
        return False
    for l in f:
        l = l.strip().split()
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
            link = text.strip().decode('iso8859-15')
        except IOError:
            link = baseurl
            link += shortName
            link += '/'

        try:
            text = open(os.path.join(path, shortName, ".title")).read()
            title = text.strip().decode('iso8859-15')
        except IOError:
            title = shortName.replace("_", " ")

        try:
            text = open(os.path.join(path, shortName, ".motd")).read()
            motd = text.strip().decode('iso8859-15')
        except IOError:
            motd = ""

        if shortName == activeCollab:
            output.append((shortName, title, motd, link, True))
        else:
            output.append((shortName, title, motd, link, False))

    output.sort(key = lambda x: x[1])

    return output

def getActiveCollab(request):
    user = request.user.name
    active = request.cfg.interwikiname
    path = request.cfg.collab_basedir
    baseurl = request.cfg.collab_baseurl
    for collab in listCollabs(baseurl, user, path, active):
        if collab[4]:
            return collab

    return None

def execute(self):
    user = self.request.user.name
    active = self.request.cfg.interwikiname
    path = self.request.cfg.collab_basedir
    baseurl = self.request.cfg.collab_baseurl
    return listCollabs(baseurl, user, path, active)
