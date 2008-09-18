# -*- coding: utf-8 -*-"
"""
    GetMetaData macro plugin to MoinMoin
     - Return the meta data of key x from page y

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

Dependencies = ['metadata']

from MoinMoin.macro.Include import _sysmsg

from graphingwiki.editing import getmetas
from graphingwiki.patterns import format_wikitext

def execute(macro, args):
    request = macro.request
    _ = request.getText

    args = [x.strip() for x in args.split(',')]
    # Wrong number of arguments
    if len(args) not in [1, 2]:
        return _sysmsg % ('error', 
                          _("GetMetaData: Need to specify page, or page and key"))

    # Get all non-empty args
    args = [x for x in args if x]

    # If not page specified, defaulting to current page
    if len(args) == 1:
        page = request.page.page_name
        key = args[0]
    elif len(args) == 2:
        page = args[0]
        key = args[1]
    # Faulty args
    else:
        return _sysmsg % ('error', 
                          _("GetMetaData: Need to specify page, or page and key"))

    vals = getmetas(request, page, [key], display=False)

    val = ', '.join(vals[key])

    return format_wikitext(request, val)
