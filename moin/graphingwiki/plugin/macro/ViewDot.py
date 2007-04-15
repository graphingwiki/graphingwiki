# -*- coding: iso-8859-1 -*-
"""
    ViewDot macro plugin to MoinMoin
     - Just like ViewDot-action, inlined on a page without controls

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

from InlineGraph import *

Dependencies = ['attachments']
    
def execute(macro, args):
    retval = ""

    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request

    # Import the plugin action to print out the graph html form
    dotviewer = wikiutil.importPlugin(request.cfg,
                                        'action', 'ViewDot',
                                        'execute')

    arglist = [x.strip() for x in args.split(',') if x]
    kw = {}
    
    for arg in arglist:
        data = arg.split('=')
        key = data[0]
        val = '='.join(data[1:])

        if key in ['height', 'width']:
            kw[str(key)] = str(val)

    view = ""
    uri, args = uri_params(arglist[0])
    args['action'] = ['ViewDot']
    if args.has_key('view'):
        view = args['view']

    pagename = url_unquote(uri.split('/')[-1])
    graph_request = copy(request)

    graph_request.page = Page(request, pagename)
    graph_request.form = args

    if view:
        args['view'] = view

    req_url = request.getScriptname() + '/' + url_quote(encode(pagename))
    graph_request.request_uri = join_params(req_url, args)
    urladd = '?' + graph_request.request_uri.split('?')[1]

    dotviewer(graph_request.page.page_name, graph_request, **kw)
    retval = '<a href="%s" id="footer">[view dot]</a>\n' % \
             (request.getScriptname() + '/' + uri.split('/')[-1] + urladd)

    return retval
