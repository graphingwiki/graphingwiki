# -*- coding: utf-8 -*-"
"""
    metaedit action to MoinMoin/Graphingwiki
     - For your new page editing pleasure 

    @copyright: 2009 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
# Request.py says that editing actions for new pages must start in lowercase:
# Disallow non available actions
# elif action[0].isupper() and not action in self.getAvailableActions( ...
# Besides allowing to use MetaEdit with NewPage, this function constructs
# the data for MetaEdit based on 

from MoinMoin import wikiutil
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import dl_proto_re

import MetaEdit

from savegraphdata import parse_text

def execute(pagename, request):
    template = request.form.get('template', [''])[0]

    if template and not request.page.exists():
        template_page = wikiutil.unquoteWikiname(template)
        if request.user.may.read(template_page):
            editor = PageEditor(request, template_page)
            editor.user = request.user
            text = editor.get_raw_body()
            editor.page_name = pagename
            request.page.set_raw_body(editor._expand_variables(text))
            newdata = parse_text(request, request.page,
                                 request.page.get_raw_body())

            # Add prototype metas (^ something::\s*$) as keys
            protokeys = [y for x,y in dl_proto_re.findall(text)]
            for key in protokeys:
                if not (key in newdata[pagename].get('out', dict()) or 
                        key in newdata[pagename].get('meta', dict())):
                    newdata[pagename].setdefault('meta', dict())[key] = list()

            # I'll lie, cheat, do anything to make this work
            newdata[pagename]['saved'] = True

            # Add the template metas to cache so that they'd show
            request.graphdata.cacheset(pagename, newdata.get(pagename, dict()))

    MetaEdit.execute(pagename, request)
