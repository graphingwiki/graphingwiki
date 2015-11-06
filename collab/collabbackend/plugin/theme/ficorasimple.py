# -*- coding: utf-8 -*-

from ficora import Theme as ThemeParent

class Theme(ThemeParent):
    BREADCRUMB_ACTIONS = [
        'AttachFile',
    ]
        
    def actionsmenu(self, d, is_footer):
        """
        Remove the wrench menu
        """
        return u""
