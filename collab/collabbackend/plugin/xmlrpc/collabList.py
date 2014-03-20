# -*- coding: utf-8 -*-"
"""
    CollabList xmlrpc plugin to MoinMoin
     - Lists collaborations user has access to

    @copyright: 2007-2010 by Timo M�kinen,
                             Marko Laakso <fenris@iki.fi> and
                             Mika Sepp�nen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

Dependencies = ['myfilesystem']

from collabbackend import listCollabs


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
