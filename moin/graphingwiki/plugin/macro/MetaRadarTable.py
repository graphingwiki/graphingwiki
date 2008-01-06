# -*- coding: utf-8 -*-"
"""
    MetaRadarDiagram macro plugin to MoinMoin
     - Makes links to the action that provides for the images

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
import StringIO
from urllib import quote as url_quote
from urllib import unquote as url_unquote

from MoinMoin import wikiutil
from MoinMoin import config

from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import encode

Dependencies = ['metadata']

def execute(macro, args):
    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

    req_url = request.getScriptname() + '/' + request.page.page_name
    req_url += '?action=metaRadarChart'

    # Note, metatable_parseargs deals with permissions
    globaldata, pagelist, metakeys = metatable_parseargs(request, args,
                                                         get_all_keys=True)

    globaldata.closedb()

    out = StringIO.StringIO()
    out.write(macro.formatter.linebreak() + macro.formatter.table(1))

    for page in pagelist:
        pagerepr = unicode(url_unquote(page), config.charset)

        url = req_url + '&arg=' + page
        out.write(macro.formatter.table_row(1))
        out.write(macro.formatter.table_cell(1, {'class': 'meta_page'}))
        out.write(macro.formatter.pagelink(1, page))
        out.write(macro.formatter.text(pagerepr))
        out.write(macro.formatter.pagelink(0))
        
        out.write(macro.formatter.table_cell(1, {'class': 'meta_radar'}))

        if args:
            arglist = [x.strip() for x in args.split(',') if x]
            for arg in arglist:
                if arg.startswith('chartheight='):
                    url += '&height=%s' % \
                           (url_quote(encode(arg.split('=')[1])))
                elif arg.startswith('chartwidth='):
                    url += '&width=%s' % \
                           (url_quote(encode(arg.split('=')[1])))
                elif arg.startswith('||') and arg.endswith('||'):
                    url += '&arg=%s' % (url_quote(encode(arg)))
                    
        out.write(u'<img src="%s">' % (request.getQualifiedURL(url)))

    out.write(macro.formatter.table(0))

    return out.getvalue()
