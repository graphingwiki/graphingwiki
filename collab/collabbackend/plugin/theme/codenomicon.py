# -*- coding: utf-8 -*-
"""
    Codenomicon branded bootstrap theme.
    @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""
from collabbackend.plugin.theme.opencollab import Theme as ThemeParent


class Theme(ThemeParent):
    name = "codenomicon"
    css_files = ['screen']

    def logo(self):
        url = self.cfg.url_prefix_static + "/codenomicon/img/logo.png"
        return u'''<img src="%s">''' % url


def execute(request):
    """
    Generate and return a theme object

    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)

