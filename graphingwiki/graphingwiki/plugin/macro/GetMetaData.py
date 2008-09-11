# -*- coding: utf-8 -*-"
"""
    GetMetaData macro plugin to MoinMoin
     - Return the meta data of key x from page y

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

Dependencies = ['metadata']

import urllib
import StringIO

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

        vals = list()
        for val, typ in getvalues(request, page, key,
                                  display=False):
            vals.append(val)

    except:
        return ''

    request.page.formatter = request.formatter
    parser = Parser(', '.join(vals), request)
    # No line anchors of any type to table cells
    request.page.formatter.in_p = 1
    parser._line_anchordef = lambda: ''

    data = StringIO.StringIO()
    request.redirect(data)
    request.page.format(parser)
    request.redirect()

    return data.getvalue().strip()
