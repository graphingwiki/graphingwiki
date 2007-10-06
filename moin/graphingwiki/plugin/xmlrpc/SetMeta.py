# -*- coding: iso-8859-1 -*-
"""
    SetMeta xmlrpc plugin to MoinMoin/Graphingwiki
     - Appends metadata from pages or replaces them

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import urllib
import xmlrpclib

from MoinMoin import config
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from MoinMoin.PageEditor import PageEditor

from graphingwiki.patterns import encode
from graphingwiki.editing import metatable_parseargs, getvalues
from graphingwiki.editing import process_edit

def urlquote(s):
    if isinstance(s, unicode):
        s = s.encode(config.charset)
    return urllib.quote(s)

# Gets data in the same format as process_edit
# i.e. input is a hash that has page!key as keys
# and a list of values. All input is plain unicode.
def execute(xmlrpcobj, page, input, action='add',
            createpage=True, category_edit='', catlist=[]):
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

    # Expects MetaTable arguments
    globaldata, pagelist, metakeys = metatable_parseargs(request, page)

    # Create page if it does not exists, and so desired
    try:
        globaldata.getpage(urlquote(page))
    except KeyError:
        # Don't litter readlocks, trigger save timeouts
        globaldata.closedb()
        if createpage:
            pageobj = PageEditor(request, page)
            msg = pageobj.saveText(' ', 0)
            # Continue reading
            globaldata.opendb()
            pass


    categories = {page: catlist}

    output = {}
    # Add existing metadata so that values would be added
    for key in input:
        pair = '%s!%s' % (page, key)
        output[pair] = input[key]

        if key in metakeys:
            if action == 'repl':
                # Add similar, purge rest
                # Do not add a meta value twice
                old = list()
                for val, typ in getvalues(request, globaldata,
                                          urlquote(page),
                                          key, display=False):
                    old.append(val)
                src = set(output[pair])
                tmp = set(src).intersection(set(old))
                dst = []
                # Due to the structure of the edit function,
                # the order of the added values is significant:
                # We want to have the common keys
                # in the same 'slot' of the 'form'
                for val in old:
                    # If we have the common key, keep it
                    if val in tmp:
                        dst.append(val)
                        tmp.remove(val)
                        src.discard(val)
                    # If we don't have the common key,
                    # but still have keys, add a non-common one
                    elif src:
                        added = False
                        for newval in src:
                            if not newval in tmp:
                                dst.append(newval)
                                src.remove(newval)
                                added = True
                                break
                        # If we only had common keys left, add empty
                        if not added:
                            dst.append(u'')
                    else:
                        dst.append(u'')
                if src:
                    dst.extend(src)
                output[pair] = dst
            else:
                # Do not add a meta value twice
                src = list()
                for val, typ in getvalues(request, globaldata,
                                          urlquote(page),
                                          key, display=False):
                    src.append(val)
                for val in src:
                    if val in output[pair]:
                        output[pair].remove(val)
                output[pair].extend(src)
                
    # Close db
    globaldata.closedb()

    return process_edit(request, output, category_edit, categories)
