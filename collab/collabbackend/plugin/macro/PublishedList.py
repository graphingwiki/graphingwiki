# -*- coding: utf-8 -*-"
"""
    PublishedList macro plugin to MoinMoin
     - Lists published collaborations user can request access for

    @copyright: 2014 Ossi Salmi
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""

Dependencies = ['myfilesystem']

import os

from collabbackend import listPublished
from graphingwiki.invite import user_may_request_invite


def formatCollabList(f, user, inviterequests, collabs):
    if not collabs:
        return f.text('No collaborations available for %s.') % f.text(user)

    divfmt = {'class': 'collab_area'}
    listfmt = {'class': 'collab_list'}
    keyfmt = {'class': 'collab_key'}
    valfmt = {'class': 'collab_val'}

    result = ''
    result = f.div(1, **divfmt)

    for (shortName, title, motd) in collabs:
        link = '?action=requestinvite&collab=' + shortName

        result += f.definition_list(1, **listfmt)

        result += f.definition_term(1, **keyfmt)
        if shortName not in inviterequests:
            result += f.url(1, link, 'collab_link')
            result += f.text(title)
            result += f.url(0)
        else:
            result += f.text(title)
            result += f.emphasis(1)
            result += f.text(' (request sent)')
            result += f.emphasis(0)
        result += f.definition_term(0)

        result += f.definition_desc(1, **valfmt)
        result += f.text(motd)
        result += f.definition_desc(0)

        result += f.definition_list(0)

    result += f.div(0)

    return result


def execute(self, args):
    f = self.formatter
    baseurl = self.request.cfg.collab_baseurl
    user = self.request.user.name
    path = self.request.cfg.collab_basedir
    inviterequests = self.request.session.get('inviterequests', [])
    if not user_may_request_invite(self.request.user, self.request.page.page_name):
        return f.text('No collaborations available for %s.') % f.text(user)
    return formatCollabList(f, user, inviterequests, listPublished(baseurl, user, path))
