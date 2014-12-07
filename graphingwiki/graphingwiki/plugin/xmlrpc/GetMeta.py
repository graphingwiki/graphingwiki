#! -*- coding: utf-8 -*-"
"""
    GetMeta xmlrpc plugin to MoinMoin/Graphingwiki
     - Sends the Metadata of desired pages

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from graphingwiki.editing import metatable_parseargs, get_metas

def execute(xmlrpcobj, args, keysonly=True):
    request = xmlrpcobj.request
    _ = request.getText

    # Expects MetaTable arguments
    pagelist, metakeys, _ = metatable_parseargs(request, args, 
                                                get_all_keys=True)
    # If we only want the keys as specified by the args
    if keysonly:
        return list(metakeys), list(pagelist)

    # Keys to the first row
    out = []
    out.append(metakeys)

    # Go through the pages, give list that has
    # the name of the page followed by the values of the keys
    for page in pagelist:
        # We're pretty sure the user has the read access to the pages,
        # so don't check again
        metas = get_metas(request, page, metakeys, checkAccess=False)
        row = [page]
        for key in metakeys:
            row.append([value for value in metas[key]])
        out.append(row)

    return out
