# -*- coding: utf-8 -*-"
"""
    CollabList macro plugin to MoinMoin
     - Lists collaborations user has access to

    @copyright: 2007-2010 by Timo Mäkinen,
                             Marko Laakso <fenris@iki.fi> and
                             Mika Seppänen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""

Dependencies = ['myfilesystem']

from collabbackend import listCollabs


def formatCollabList(f, user, collabs):
    if not collabs:
        return f.text('No collaborations available for ') + f.text(user)

    divfmt = {'class': 'collab_area'}
    listfmt = {'class': 'collab_list'}
    keyfmt = {'class': 'collab_key'}
    activekeyfmt = {'class': 'collab_key', 'id': 'collab_active'}
    valfmt = {'class': 'collab_val'}
    activevalfmt = {'class': 'collab_val', 'id': 'collab_active'}
       
    result = ''
    result = f.div(1, **divfmt)

    for (shortName, title, motd, link, active) in collabs:
        result += f.definition_list(1, **listfmt)

        if active:
            result += f.definition_term(1, **activekeyfmt)
        else:
            result += f.definition_term(1, **keyfmt)

        result += f.url(1, link, 'collab_link')
        result += f.text(title)
        result += f.url(0)
        result += f.definition_term(0)

        if active: 
            result += f.definition_desc(1, **activevalfmt)
        else:
            result += f.definition_desc(1, **valfmt)
            
        result += f.text(motd)
        result += f.definition_desc(0)
        result += f.definition_list(0)

    result += f.div(0)

    return result

def execute(self, args):
    user = self.request.user.name
    active = self.request.cfg.interwikiname
    path = self.request.cfg.collab_basedir
    baseurl = self.request.cfg.collab_baseurl
    return formatCollabList(self.formatter, user, listCollabs(baseurl, user, path, active))
