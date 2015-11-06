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

    def search_form(self, d):
        _ = self.request.getText
        url = self.request.href(d['page'].page_name)

        return u"""
  <form method="get" class="navbar-right navbar-form" action="%s">
    <div class="form-group">
      <div class="input-group">
        <input type="hidden" name="action" value="fullsearch">
        <input type="hidden" name="context" value="180">
        <input type="hidden" name="titlesearch" value="0">
        <input type="text" autocomplete="off" class="form-control search" placeholder="Search" name="value">
        <div class="input-group-btn">
            <button class="btn btn-primary" name="titlesearch" type="submit">
                <i class="glyphicon glyphicon-search"></i>
            </button>
        </div>
      </div>
    </div>
  </form>""" % url
