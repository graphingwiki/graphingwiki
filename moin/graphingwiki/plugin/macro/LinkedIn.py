# -*- coding: iso-8859-1 -*-
"""
    LinkedIn macro plugin to MoinMoin/Graphingwiki
     - Shows pages in which the current page has been linked in

    @copyright: 2006 by Juhani Eronen <exec@iki.fi>
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
from urllib import quote as url_quote
from urllib import unquote as url_unquote
from codecs import getencoder

from MoinMoin import config

from graphingwiki.patterns import encode, GraphData

Dependencies = ['pagelinks']

def execute(macro, args):
    pagename = macro.formatter.page.page_name
    pagename = url_quote(encode(pagename))

    out = []
    nodes = set()
    globaldata = GraphData(macro.request)
    page = globaldata.getpage(pagename)
    for type in page.get('in', {}):
        for page in page['in'][type]:
            page = unicode(url_unquote(page), config.charset)
            if not page in nodes:
                out.append(macro.formatter.pagelink(1, page) +
                           macro.formatter.text(page) +
                           macro.formatter.pagelink(0, page))
                nodes.add(page)

    return "Linked in pages: " + ', '.join(out)
