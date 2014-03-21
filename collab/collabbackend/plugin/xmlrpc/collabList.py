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

#import all old functions for xmlrpc api backwards compatibility
from collabbackend import listCollabs, checkAccess, getActiveCollab

def execute(self):
    user = self.request.user.name
    active = self.request.cfg.interwikiname
    path = self.request.cfg.collab_basedir
    baseurl = self.request.cfg.collab_baseurl
    return listCollabs(baseurl, user, path, active)
