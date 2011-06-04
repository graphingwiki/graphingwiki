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

#Used by action/getMetaJSON.py
def do_action(request, args):
    # Expects MetaTable arguments
    pagelist, metakeys, _ = metatable_parseargs(request, args,
                                                get_all_keys=True)

    out = {}
    # We're pretty sure the user has the read access to the pages,
    # so don't check again
    for page in pagelist:
        metas = get_metas(request, page, metakeys, checkAccess=False)
        out[page] = dict(metas)
    return out

def execute(xmlrpcobj, args):
    return do_action(xmlrpcobj.request, args)
