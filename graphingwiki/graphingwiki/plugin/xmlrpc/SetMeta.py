# -*- coding: utf-8 -*-"
"""
    SetMeta xmlrpc plugin to MoinMoin/Graphingwiki
     - Appends metadata from pages or replaces them

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import xmlrpclib

from graphingwiki.editing import set_metas
from MoinMoin.formatter.text_plain import Formatter as TextFormatter

from graphingwiki.util import encode
from graphingwiki.editing import save_template

# Gets data in the same format as process_edit
# i.e. input is a hash that has page!key as keys
# and a list of values. All input is plain unicode.
def execute(xmlrpcobj, page, input, action='add',
            createpage=True, category_edit='add', catlist=[],
            template=''):

    request = xmlrpcobj.request
    _ = request.getText
    request.formatter = TextFormatter(request)

    #Could this be removed?
    if not request.user.may.write(page):
        return xmlrpclib.Fault(1, _("You are not allowed to edit this page"))

    page = page.strip()

    # Fault at empty pagenames
    if not page:
        return xmlrpclib.Fault(2, _("No page name entered"))

    # Pre-create page if it does not exist, using the template specified
    if createpage and template:
        save_template(request, page, template)

    #this is from the trunk (1.5) I think...
    if action == 'repl':
        action = 'set'

    cleared, added, discarded = {page: set()}, {page: dict()}, {page: dict()}

    if action == 'add':
        for key in input:
            added[page][key] = input[key]
    elif action == 'set':
        for key in input:
            cleared[page].add(key)
            added[page][key] = input[key]
    else:
        raise ValueError("action must be one of add, set, repl (got %s)" % 
                         repr(action))

    if category_edit == 'del':
        discarded[page].setdefault('gwikicategory', list()).extend(catlist)
    elif category_edit == 'set':
        cleared[page].add("gwikicategory")
        added[page].setdefault('gwikicategory', list()).extend(catlist)
    elif  category_edit == 'add':
        added[page].setdefault('gwikicategory', list()).extend(catlist)
    else:
        raise ValueError("category_edit must be one of add, del, set (got %s)" \
                             % repr(category_edit))

    if template:
        added[page]['gwikitemplate'] = template
   
    _, msg = set_metas(request, cleared, discarded, added)

    return msg
