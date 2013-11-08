# -*- coding: utf-8 -*-
"""
    Codenomicon branded bootstrap theme.
    @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""
from collabbackend.plugin.theme.opencollabnew import Theme as ThemeParent


class Theme(ThemeParent):
    name = "codenomicon"


    def logo(self):
        url = self.cfg.url_prefix_static + "/codenomicon/img/logo.png"
        return u'''<div id="logo">
        <img width="75%%" height="75%%" src="%s"></img>
        </div>'''%url

def execute(request):
    """
    Generate and return a theme object

    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)

