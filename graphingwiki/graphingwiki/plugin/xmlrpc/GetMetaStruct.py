#! -*- coding: utf-8 -*-"
"""
    GetMeta xmlrpc plugin to MoinMoin/Graphingwiki
     - Sends the Metadata of desired pages

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @copyright: 2009 by Erno Kuusela <erno@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import urllib
 
from graphingwiki.editing import metatable_parseargs, get_metas


def execute(xmlrpcobj, args):
    request = xmlrpcobj.request
    _ = request.getText

    # Expects MetaTable arguments
    pagelist, metakeys, _ = metatable_parseargs(request, args, 
                                                get_all_keys=True)

    out = {}
    # We're pretty sure the user has the read access to the pages,
    # so don't check again
    for page in pagelist:
        metas = get_metas(request, page, metakeys, 
                          checkAccess=False, formatLinks=None)
        out[page] = dict(metas)
    return out
