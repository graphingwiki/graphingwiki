# -*- coding: utf-8 -*-"
"""
    MetaRevisions macro plugin to MoinMoin/Graphingwiki
     - Outputs a table of metadata as seen in the page's history.
       Takes metatable arguments.

    @copyright: 2008 by Juhani Eronen <exec@iki.fi>
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

from graphingwiki.editing import get_revisions

from MetaTable import construct_table

Dependencies = ['metadata']

def execute(macro, args):
    request = macro.request
    _ = macro.request.getText

    if args:
        page = Page(request, args)
    else:
        page = request.page

    pagelist, metakeys = get_revisions(request, page)

    construct_table(macro, pagelist, metakeys, 'Meta by Revision')

    return ''
