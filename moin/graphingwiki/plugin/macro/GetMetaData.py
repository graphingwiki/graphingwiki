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
from MoinMoin.parser.wiki import Parser

from graphingwiki.editing import getvalues, metatable_parseargs

def urlquote(s):
    if isinstance(s, unicode):
        s = s.encode(config.charset)
    return urllib.quote(s)

def execute(macro, args):
    request = macro.request

    if not request.user.may.read(args.split(',')[0]):
        return ''

    try:
        page, key = [urlquote(x.strip()) for x in args.split(',')]

        # Note, metatable_parseargs deals with permissions
        globaldata, pagelist, metakeys, _ = metatable_parseargs(request, page,
                                                                get_all_keys=True)

        vals = list()
        for val, typ in getvalues(request, globaldata, page, key,
                                  display=False):
            vals.append(val)

    except:
        globaldata.closedb()
        return ''

    globaldata.closedb()

    request.page.formatter = request.formatter
    request.page.send_page_content(request, Parser,
                                   ', '.join(vals),
                                   do_cache=0,
                                   line_anchors=False)
