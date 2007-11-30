#! -*- coding: utf-8 -*-"
"""
    GetMeta xmlrpc plugin to MoinMoin/Graphingwiki
     - Sends the Metadata of desired pages

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import urllib
 
from graphingwiki.editing import metatable_parseargs, getvalues

def execute(xmlrpcobj, args, keysonly=True):
    request = xmlrpcobj.request
    _ = request.getText

    
    # Expects MetaTable arguments
    globaldata, pagelist, metakeys = metatable_parseargs(request, args)
    
    # If we only want the keys as specified by the args
    if keysonly:
        globaldata.closedb()
        return list(metakeys), list(pagelist)

    data = dict()
    keyoccur = dict()

    # Go through the pages, give list that has
    # the name of the page followed by the values of the keys
    for page in pagelist:
        data[page] = dict()
        for key in metakeys:
            keyoccur.setdefault(key, 0)

            data[page][key] = list()
            for val, typ in getvalues(request, globaldata, page, key):
                data[page][key].append(val)

            keyonpage = len(data[page][key])
            if keyonpage > keyoccur[key]:
                keyoccur[key] = keyonpage

    # Keys to the first row
    out = []
    keys = []
    for key in metakeys:
        keys.append([key] * keyoccur[key])
    out.append(keys)
        
    for page in pagelist:
        row = [page]
        for key in metakeys:
            vals = []
            for val in data[page][key]:
                vals.append(val)
            vals.extend([''] * (keyoccur[key] - len(vals)))
            row.append(vals)
        out.append(row)
    
    # Close db, get out
    globaldata.closedb()

    return out
