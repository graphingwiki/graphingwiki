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

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.macro.Include import _sysmsg
from MoinMoin.support.werkzeug.datastructures import CombinedMultiDict, \
    MultiDict

from graphingwiki.util import form_escape, url_construct
from graphingwiki import url_unescape

Dependencies = ['metadata']

def uri_params(uri):
    args = {}
    allstr = uri.split('?')
    if len(allstr) > 1:
        uri, argstr = allstr
        argstr = argstr.split('&')

        for arg in argstr:
            key, val = map(url_unescape, arg.split('='))
            args.setdefault(key, list()).append(val)

    return uri, args
    
def execute(macro, args):
    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

    # Import the plugin action to print out the graph html form
    graphshower = wikiutil.importPlugin(request.cfg,
                                        'action', 'ShowGraph',
                                        'execute')

    if not args:
        return ""

    uri, args = uri_params(args.strip())

    if not args:
        return ""

    # Legacy fix
    args['action'] = ['ShowGraph']
    pagename = uri

    # Check out if the start page exists, if not, we'll just bail out
    try:
        if not request.user.may.read(pagename):
            return _sysmsg % (error, 
        _("InlineGraph: User may not read page") + " %s" % 
        form_escape(pagename))
    except:
        return _("InlineGraph: No data on") + " %s" % pagename

    old_page = request.page
    old_values = request.values
    old_url = getattr(request, 'url', '')

    request.page = Page(request, pagename)
    request.values = CombinedMultiDict([MultiDict(args)])

    req_url = url_construct(request, args)
    urladd = '?' + req_url.split('?')[1]

    request.url = url_construct(request, args, pagename)

    request.write(u'<div class="inlinegraph">')
    graphshower(request.page.page_name, request, 
                urladd=urladd, app_page=request.page.page_name, inline=1)

    request.page = old_page
    request.values = old_values
    del request.url
    if old_url:
        request.url = old_url

    return u'<a href="%s" id="footer" class="graph-link">[%s]</a>\n' % \
           (req_url, _('examine')) + u'</div>'
