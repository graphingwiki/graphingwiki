# -*- coding: utf-8 -*-"
"""
    setMetaJSON action plugin for MoinMoin/Graphingwiki
     - Appends metadata from pages or replaces them

    @copyright: 2010 by Erno Kuusela <erno@iki.fi>
    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

from graphingwiki.plugin.xmlrpc.SetMeta import do_action
try:
    import json
except ImportError:
    import simplejson as json

def sendfault(request, code, msg):
    request.write(json.dumps(dict(status="error", errcode=code, errmsg=msg)))

def doit(request, pagename, indata):
    template = indata.get('template')
    createpage = indata.get('createpage')
    action = indata.get('action', 'add')
    inmetas = indata.get('metas')
    category_edit = inmetas.get('category_edit', 'add')
    catlist = inmetas.get('catlist', [])

    try:
        return do_action(request, pagename, inmetas, action, createpage,
                         category_edit, catlist, template)
    except ValueError, e:
        if len(tuple(e)) > 1 and type(e[0]) == int:
            sendfault(request, e[0], e[1])
        else:
            raise ValueError(e)

def execute(pagename, request):
    if not request.user.may.write(pagename):
        sendfault(request, 1, _("You are not allowed to edit this page"))
        return

    pagename = pagename.strip()
    if not pagename:
        sendfault(request, 2, _("No page name entered"))
        return

    indata = request.form.get('args', [None])[0]
    if not indata:
        request.write('No data')
        return

    indata = json.loads(indata)

    if 'metas' not in indata:
        msg = []
        for xpagename, metadict in indata.items():
            r = doit(request, xpagename, {'metas': metadict, 'action': 'set'})
            if not r:
                continue
            if type(r) is list:
                msg += r
            else:
                msg.append(r)
    else:
        msg = doit(request, pagename, indata)

    if msg:
        json.dump(dict(status="ok", msg=msg), request)

