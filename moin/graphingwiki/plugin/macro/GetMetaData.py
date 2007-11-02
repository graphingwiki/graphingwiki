# -*- coding: utf-8 -*-"
"""
    GetMetaData macro plugin to MoinMoin
     - Return the meta data of key x from page y

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

Dependencies = ['metadata']

import urllib

from MoinMoin import config

from graphingwiki.patterns import GraphData
from graphingwiki.editing import getvalues

def urlquote(s):
    if isinstance(s, unicode):
        s = s.encode(config.charset)
    return urllib.quote(s)

def execute(macro, args):
    request = macro.request

    if not request.user.may.read(args.split(',')[0]):
        return ''

    globaldata = GraphData(request)

    try:
        page, key = [urlquote(x.strip()) for x in args.split(',')]

        # Break if user may not read target page
        if not request.user.may.read(url_unquote(frompage)):
            raise

        vals = list()
        for val, typ in getvalues(request, globaldata, page, key):
            vals.append(val)
    except:
        globaldata.closedb()
        return ''

    globaldata.closedb()

    return request.formatter.text(', '.join(vals))
