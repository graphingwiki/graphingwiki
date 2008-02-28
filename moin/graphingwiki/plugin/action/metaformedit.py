# -*- coding: utf-8 -*-"
"""
    metaformedit action to MoinMoin/Graphingwiki
     - For your new page editing pleasure 

    @copyright: 2008 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
# Request.py says that editing actions for new pages must start in lowercase:
# Disallow non available actions
# elif action[0].isupper() and not action in self.getAvailableActions( ...
# Editing new pages with MetaFormEdit is the only reason this action exists

import MetaFormEdit

def execute(pagename, request):
    MetaFormEdit.execute(pagename, request)
