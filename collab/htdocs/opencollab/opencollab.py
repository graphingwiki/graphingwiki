# -*- coding: utf-8 -*-
"""
 @copyright: 2010 by Marko Laakso <fenris@iki.fi>
 @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""

from MoinMoin.theme.modernized import Theme as ThemeParent
from MoinMoin import  wikiutil

class Theme(ThemeParent):

    name = "opencollab"

    def logo(self):
        mylogo = ThemeParent.logo(self)
        if not mylogo:
            mylogo = u'''<div id="logo">%s</div>''' % \
                     wikiutil.escape(self.cfg.sitename, True)

        return mylogo
        
def execute(request):
    """
    Generate and return a theme object
        
    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)
