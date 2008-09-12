# -*- coding: utf-8 -*-"
"""
    InlineGraph macro plugin to MoinMoin
     - Just like ShowGraph-action, inlined on a page without controls

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
from urllib import unquote as url_unquote
from urllib import quote as url_quote
from copy import copy

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin import config

from graphingwiki.patterns import encode

Dependencies = ['metadata']

def uri_params(uri):
    args = {}
    allstr = uri.split('?')
    if len(allstr) > 1:
        uri, argstr = allstr
        argstr = argstr.split('&')

        for arg in argstr:
            key, val = arg.split('=')
            args.setdefault(encode(url_unquote(key)),
                            []).append(encode(url_unquote(val)))

    return uri, args

def list_params(arglist):
    form = {}

    if len(arglist) % 2:
        arglist = arglist[:-1]
    while len(arglist) > 1:
        key, val = arglist[:2]

        form.setdefault(encode(key), []).append(encode(val))

        arglist = arglist[2:]

    return form

def join_params(uri, args):
    argstr = ""
    for key in args:
        for val in args[key]:
            argstr = argstr + "&%s=%s" % (url_quote(key), url_quote(val))
    return uri + "?" + argstr[1:]
    
def execute(macro, args):
    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

    # Import the plugin action to print out the graph html form
    graphshower = wikiutil.importPlugin(request.cfg,
                                        'action', 'ShowGraphSimple',
                                        'execute_graphs')

    arglist = [x.strip() for x in args.split(',') if x]
    kw = {}

    for arg in arglist:
        data = arg.split('=')
        key = data[0]
        val = '='.join(data[1:])

    if not arglist:
        return ""

    uri, args = uri_params(arglist[0])

    if not args:
        return ""

    # Legacy fix
    args['action'] = ['ShowGraphSimple']
    pagename = uri

    # Check out if the start page exists, if not, we'll just bail out
    try:
        if not request.user.may.read(pagename):
            return _("InlineGraph: User may  not read page") + \
                   " %s" % pagename
        request.graphdata.getpage(url_quote(encode(uri)))
    except:
        return _("InlineGraph: No data on") + " %s" % pagename

    graph_request = copy(request)

    graph_request.page = Page(request, pagename)
    graph_request.form = args
    req_url = request.getScriptname() + '/' + url_quote(encode(pagename))

    graph_request.request_uri = join_params(req_url, args)

    urladd = '?' + graph_request.request_uri.split('?')[1]
    kw['urladd'] = urladd

    request.write(u'<div class="inlinegraph">')
    graphshower(graph_request.page.page_name, graph_request, **kw)

    req_url = request.getScriptname() + '/' + uri
    req_url = join_params(req_url, args)
    return u'<a href="%s" id="footer">[%s]</a>\n' % \
           (graph_request.getQualifiedURL(req_url), _('examine')) + \
           u'</div>'
