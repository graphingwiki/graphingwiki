# -*- coding: utf-8 -*-"
"""
    setMetaJSON action plugin for MoinMoin/Graphingwiki
     - Appends metadata from pages or replaces them

    @copyright: 2010 by Erno Kuusela <erno@iki.fi>
    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

from graphingwiki.editing import set_metas
from MoinMoin.formatter.text_plain import Formatter as TextFormatter

from graphingwiki.util import encode
from graphingwiki.editing import save_template

import json

def simple_to_traditional(indict):
    for pagename in indict.keys():
        yield pagename, {'metas': indict[pagename].copy(), 'action': 'set'}


def execute(pagename, request):
    indata = request.form.get('args', [None])[0]
    if not indata:
        request.write('No data')
        return

    indata = json.loads(indata)

    if 'metas' not in indata:
        msg = []
        for xpagename, metadict in indata.items():
            r = doit(request, xpagename, {'metas': metadict, 'action': 'set'})
            if type(r) is list:
                msg += r
            else:
                msg.append(r)
    else:
        msg = doit(request, pagename, indata)

    json.dump(dict(status="ok", msg=msg), request)

def doit(request, pagename, indata):
    template = indata.get('template')
    createpage = indata.get('createpage')    
    action = indata.get('action', 'add')
    inmetas = indata.get('metas')
    category_edit = inmetas.get('category_edit', 'add')
    catlist = inmetas.get('catlist', [])

    def sendfault(code, msg):
        request.write(json.dumps(dict(status="error", errcode=code, errmsg=msg)))

    if not request.user.may.write(pagename):
        sendfault(1, _("You are not allowed to edit this page"))
        return

    pagename = pagename.strip()
    if not pagename:
        sendfault(2, _("No page name entered"))
        return

    # Pre-create page if it does not exist, using the template specified
    if createpage and template:
        save_template(request, page, template)

    cleared, added, discarded = {pagename: set()}, {pagename: dict()}, {pagename: dict()}
    
    if action == 'add':
        for key in inmetas:
            added[page][key] = inmetas[key]
    elif action == 'set':
        for key in inmetas:
            cleared[pagename].add(key)
            added[pagename][key] = inmetas[key]
    else:
        sendfault(4, "action must be one of add, set(got %s)" % 
                         repr(action))

    if category_edit == 'del':
        discarded[pagename].setdefault('gwikicategory', list()).extend(catlist)
    elif category_edit == 'set':
        cleared[pagename].add("gwikicategory")
        added[pagename].setdefault('gwikicategory', list()).extend(catlist)
    elif  category_edit == 'add':
        added[pagename].setdefault('gwikicategory', list()).extend(catlist)
    else:
        raise ValueError("category_edit must be one of add, del, set (got %s)" \
                             % repr(category_edit))

    if template:
        added[pagename]['gwikitemplate'] = template
   
    _, msg = set_metas(request, cleared, discarded, added)
    return msg
