# -*- coding: utf-8 -*-
"""
    Synopsys branded bootstrap theme.
"""
from collabbackend.plugin.theme.opencollab import Theme as ThemeParent


class Theme(ThemeParent):
    name = "synopsys"
    css_files = ['screen']

    def logo(self):
        url = self.cfg.url_prefix_static + "/synopsys/img/logo.png"
        return u'''<img src="%s">''' % url


def execute(request):
    """
    Generate and return a theme object

    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)

