# -*- coding: utf-8 -*-"
"""
    CollabHome macro plugin to MoinMoin
     - Created named link to Collab Home

    @copyright: 2007-2010 by Marko Laakso <fenris@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

Dependencies = ['myfilesystem']

def execute(self, linkText):
    baseurl = self.request.cfg.collab_baseurl
    f = self.formatter

    if len(linkText) == 0:
        linkText = "Collab Home"

    divfmt = {'class': 'collab_home'}
       
    result = ''
    result = f.div(1, **divfmt)
    result += f.url(1, baseurl, 'collab_link')
    result += f.strong(1)
    result += f.text(linkText)
    result += f.strong(0)
    result += f.url(0)
    result += f.div(0)

    return result
