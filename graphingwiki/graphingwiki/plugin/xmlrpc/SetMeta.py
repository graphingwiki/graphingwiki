# -*- coding: utf-8 -*-"
"""
    SetMeta xmlrpc plugin to MoinMoin/Graphingwiki
     - Appends metadata from pages or replaces them

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import xmlrpclib

from graphingwiki.editing import set_metas, getmetas
from MoinMoin.formatter.text_plain import Formatter as TextFormatter

# To be deprecated, now mimics the original interface with its quirks
def execute(xmlrpcobj, page, input, action='add',
            createpage=True, category_edit='', catlist=[],
            template=''):
    request = xmlrpcobj.request
    _ = request.getText
    request.formatter = TextFormatter(request)

    # Using the same access controls as in MoinMoin's xmlrpc_putPage
    # as defined in MoinMoin/wikirpc.py
    if (request.cfg.xmlrpc_putpage_trusted_only and
        not request.user.trusted):
        message = "You are not allowed to edit pages by XML-RPC"
        return xmlrpclib.Fault(1, _(message))

    # Fault at empty pagenames
    if not page.strip():
        return xmlrpclib.Fault(2, _("No page name entered"))

    if action == 'repl':
        action = 'set'
    # Just to be on the safe side, I don't think this was used
    if category_edit == 'repl':
        category_edit = 'set'

    cleared, added, discarded = {page: dict()}, {page: dict()}, {page: dict()}

    if action == 'add':
        added[page] = input
    elif action == 'set':
        old = getmetas(request, page, input.keys(), display=False)
        for key in old:
            discarded[page][key] = old[key]
            added[page][key] = input[key]

    if category_edit == 'del':
        discarded[page].setdefault('gwikicategory', list()).extend(catlist)
    elif category_edit == 'set':
        oldcats = getmetas(request, page, ['gwikicategory'], display=False)
        discarded[page].setdefault('gwikicategory', list()).extend(oldcats)
        added[page].setdefault('gwikicategory', list()).extend(catlist)
    # default to add category
    else:
        added[page].setdefault('gwikicategory', list()).extend(catlist)

    if template:
        added[page]['gwikitemplate'] = template

    _, msg = set_metas(request, cleared, discarded, added)

    return msg
