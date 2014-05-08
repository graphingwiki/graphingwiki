# -*- coding: utf-8 -*-"
"""
    GroupEditor action plugin for MoinMoin/Graphingwiki.
    The functionality is implemented on gwikicommon/js/GroupEditor.js.

    @copyright: 2014 by Lauri Pokka larpo@codenomicon.com
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import MoinMoin.wikiutil as wikiutil
from MoinMoin.Page import Page
from graphingwiki.util import enter_page, exit_page


def execute(pagename, request):
    enter_page(request, pagename, "Group Editor")
    macro = wikiutil.importPlugin(request.cfg, "macro", "GroupEditor", "do_macro")
    request.write(macro(request))
    page = Page(request, pagename)
    request.write(page.link_to(request, text=request.getText("back")))
    exit_page(request, pagename)
