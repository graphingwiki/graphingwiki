# -*- coding: utf-8 -*-"
"""
    GetMetaData macro plugin to MoinMoin
     - Return the meta data of key x from page y

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

Dependencies = ['metadata']

import StringIO

from MoinMoin.parser.wiki import Parser

from graphingwiki.patterns import encode_page
from graphingwiki.editing import getmetas, metatable_parseargs

def execute(macro, args):
    request = macro.request

    if not request.user.may.read(args.split(',')[0]):
        return ''

    try:
        args = args.split(',')
        page = encode_page(args[0].strip())
        key = args[1]

        vals = getmetas(request, page, [key], display=False)
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
