# -*- coding: utf-8 -*-"
"""
    SetMeta xmlrpc plugin to MoinMoin/Graphingwiki
     - Appends metadata from pages or replaces them

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import urllib
import xmlrpclib

from graphingwiki.editing import set_metas
from MoinMoin.formatter.text_plain import Formatter as TextFormatter

from graphingwiki.patterns import encode, getgraphdata
from graphingwiki.editing import process_edit, order_meta_input, save_template

def urlquote(s):
    if isinstance(s, unicode):
        s = s.encode(config.charset)
    return urllib.quote(s)

# Gets data in the same format as process_edit
# i.e. input is a hash that has page!key as keys
# and a list of values. All input is plain unicode.
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
        return xmlrpclib.Fault(1, _("You are not allowed to edit this page"))

    if not request.user.may.write(page):
        return xmlrpclib.Fault(1, _("You are not allowed to edit this page"))

    # Fault at empty pagenames
    if not page.strip():
        return xmlrpclib.Fault(2, _("No page name entered"))

    # Pre-create page if it does not exist, using the template specified
    if createpage:
        save_template(request, page, template)
        # Graphdata locked at once in hopes of reducing race conditions
        getgraphdata(request)

    cleared, added, discarded = {page: set()}, {page: dict()}, {page: dict()}

    if action == 'add':
        for key in input:
            added[page][key] = input[key]
    elif action == 'set':
        for key in input:
            cleared[page].add(key)
            added[page][key] = input[key]

    if category_edit == 'del':
        discarded[page].setdefault('gwikicategory', list()).extend(catlist)
    elif category_edit == 'set':
        cleared[page].add("gwikicategory")
        added[page].setdefault('gwikicategory', list()).extend(catlist)
    # default to add category
    else:
        added[page].setdefault('gwikicategory', list()).extend(catlist)
