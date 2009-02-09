# -*- coding: utf-8 -*-"
"""
    MetaCount macro plugin to MoinMoin/Graphingwiki
     - Counts how many mathces there are for given metatable argument string

    @copyright: 2008 by therauli <therauli@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""

from MoinMoin.Page import Page

from graphingwiki.editing import metatable_parseargs, get_metas
from graphingwiki.patterns import format_wikitext, url_escape

Dependencies = ['metadata']

def execute(macro, args):
    if args is None:
        args = ''

    # Note, metatable_parseargs deals with permissions
    pagelist, metakeys, styles = metatable_parseargs(macro.request, args,
                                                     get_all_keys=True)

    request = macro.request
    _ = request.getText

    # No data -> bail out quickly, Scotty
    if not pagelist:
        return "No matches for '%s'" % args

    return "%d matches for '%s'" % (len(pagelist), args)
