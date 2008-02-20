# -*- coding: utf-8 -*-"
"""
    SetMeta xmlrpc plugin to MoinMoin/Graphingwiki
     - Appends metadata from pages or replaces them

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import urllib
import xmlrpclib

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page

from graphingwiki.patterns import encode
from graphingwiki.editing import process_edit, order_meta_input

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

    # Create page if not available, use templates if specified
    raw_body = Page(request, page).get_raw_body()
    if not raw_body and createpage:
        raw_body = ' '
        pageobj = PageEditor(request, page)
        if template:
            template_page = wikiutil.unquoteWikiname(template)
            if request.user.may.read(template_page):
                temp_body = Page(request, template_page).get_raw_body()
                if temp_body:
                    raw_body = temp_body

        pageobj.saveText(raw_body, 0)

    # process_edit requires a certain order to meta input
    output = order_meta_input(request, page, input, action)

    categories = {page: catlist}

    return process_edit(request, output, category_edit, categories)
