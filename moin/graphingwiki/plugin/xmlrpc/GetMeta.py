# -*- coding: iso-8859-1 -*-
"""
    GetMeta xmlrpc plugin to MoinMoin/Graphingwiki
     - Sends the Metadata of desired pages

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import urllib

from MoinMoin import config

from graphingwiki.editing import metatable_parseargs, getvalues

def url_unquote(s):
    s = urllib.unquote(s)
    if not isinstance(s, unicode):
        s = unicode(s, config.charset)
    return s

def execute(xmlrpcobj, args, keysonly=True):
    request = xmlrpcobj.request
    _ = request.getText

    
    # Expects MetaTable arguments
    globaldata, pagelist, metakeys = metatable_parseargs(request, args)
    
    # If we only want the keys as specified by the args
    if keysonly:
        globaldata.closedb()
        return list(metakeys), list(pagelist)

    # Keys to the first row
    out = [list(metakeys)]
    # Go through the pages, give list that has
    # the name of the page followed by the values of the keys
    for page in pagelist:

        row = [page]
        for key in metakeys:
            for val, typ in getvalues(request, globaldata, page, key):
                print val
                row.append(val)
        out.append(row)

    # Close db, get out
    globaldata.closedb()

    return out
