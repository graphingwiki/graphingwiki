# -*- coding: utf-8 -*-
"""
    Oulu University branded bootstrap theme.
    @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""
from collabbackend.plugin.theme.opencollab import Theme as ThemeParent


class Theme(ThemeParent):
    name = "univoulu"
    css_files = ['screen']

    def logo(self):
        url = self.cfg.url_prefix_static + "/univoulu/img/logo_fin2.png"
        return u'''<img src="%s">''' % url


def execute(request):
    """
    Generate and return a theme object

    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)

