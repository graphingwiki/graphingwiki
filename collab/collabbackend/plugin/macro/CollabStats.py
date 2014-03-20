# -*- coding: utf-8 -*-"
"""
    CollabHome macro plugin to MoinMoin
     - Collect and render some stats about Collabs

    @copyright: 2008-2010 by Marko Laakso <fenris@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

Dependencies = ['myfilesystem']

from MoinMoin import user
from collabbackend import listCollabs

def execute(self, modearg):
    myuser = self.request.user.name
    active = self.request.cfg.interwikiname
    path = self.request.cfg.collab_basedir
    baseurl = self.request.cfg.collab_baseurl

    collablist = listCollabs(baseurl, myuser, path, active, nocheck=True)
    userlist = user.getUserList(self.request)
    domainset = {}

    for uid in userlist:
        account = user.User(self.request, uid)
        nameparts = account.name.split("@", 1)
        if len(nameparts) > 1:
            domainset[nameparts[1]] = 1

    f = self.formatter

    if not modearg or len(modearg) == 0:
        stattext = "Currently hosting " + str(len(collablist)) \
            + " collaboration instances"
        stattext += " for " + str(len(userlist)) + " collaborators"
        stattext += " from " + str(len(domainset)) + " organisations."
    else:
        stattext = "Uknown stat mode: " + modearg

    divfmt = {'class': 'collab_stats'}
       
    result = ''
    result = f.div(1, **divfmt)
    result += f.strong(1)
    result += f.text(stattext)
    result += f.strong(0)
    result += f.div(0)

    return result
