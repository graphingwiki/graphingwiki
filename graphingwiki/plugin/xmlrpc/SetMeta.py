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

#Used in action/setMetaJSON.py
def do_action(request, page, inmetas, action='add', createpage=True,
              category_edit='add', catlist=[], template=''):

    cleared, added, discarded = {page: set()}, {page: dict()}, {page: dict()}
    if action == 'add':
        for key in inmetas:
            added[page][key] = inmetas[key]
    elif action == 'set':
        for key in inmetas:
            cleared[page].add(key)
            added[page][key] = inmetas[key]
    else:
        #4 is used by action/setMetaJSON.py
        raise ValueError(4, "action must be one of add, set (got %s)" %
                         repr(action))

    if category_edit == 'del':
        discarded[page].setdefault('gwikicategory', list()).extend(catlist)
    elif category_edit == 'set':
        cleared[page].add("gwikicategory")
        added[page].setdefault('gwikicategory', list()).extend(catlist)
    elif  category_edit == 'add':
        added[page].setdefault('gwikicategory', list()).extend(catlist)
    else:
        raise ValueError("category_edit must be one of add, del, set (got %s)"%
                         repr(category_edit))

    if template:
        added[page]['gwikitemplate'] = template

    _, msg = set_metas(request, cleared, discarded, added)
    return msg

# Gets data in the same format as process_edit
# i.e. input is a hash that has page!key as keys
# and a list of values. All input is plain unicode.
def execute(xmlrpcobj, page, inmetas, action='add',
            createpage=True, category_edit='add', catlist=[],
            template=''):

    request = xmlrpcobj.request
    _ = request.getText
    request.formatter = TextFormatter(request)
    page = xmlrpcobj._instr(page)

    #this is from the trunk (1.5) I think...
    if action == 'repl':
        action = 'set'

    try:
        return do_action(request, page, inmetas, action, createpage,
                         category_edit, catlist, template)
    except ValueError, e:
        if len(tuple(e)) > 1 and type(e[0]) == int:
            raise ValueError(e[1])
        else:
            raise ValueError(e)
