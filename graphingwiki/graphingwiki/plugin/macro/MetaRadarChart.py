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
from MoinMoin.Page import Page

from graphingwiki import cairo_found
from graphingwiki.util import url_construct

Dependencies = ['metadata']

def radarchart_args(args):
    urlargs = {u'action': [u'metaRadarChart']}

    if not args:
        return urlargs, ''

    arglist = [x.strip() for x in args.split(',') if x]
    macro_args = list()

    for arg in arglist:
        if arg.startswith('chartheight='):
            urlargs[u'height'] = [arg.split('=')[1]]
        elif arg.startswith('chartwidth='):
            urlargs[u'width'] = [arg.split('=')[1]]
        elif arg.startswith('chartscale='):
            urlargs.setdefault('scale', list()).append(arg.split('=')[1])
        else:
            urlargs.setdefault(u'arg', list()).append(arg)
            macro_args.append(arg)

    return urlargs, u','.join(macro_args)

def execute(macro, args):
    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

    if not cairo_found:
        return formatter.text(_(\
            "ERROR: Cairo Python extensions not installed. " +\
            "Not performing layout.")) + formatter.linebreak()

    urlargs, macro_args = radarchart_args(args)

    pagename = request.page.page_name
    # The first page mentioned will be the page of the chart
    for arg in macro_args.split(','):
        page = Page(request, arg)
        if page.exists():
            pagename = arg
            break

    return u'<div class="metaradarchart">' + \
           u'<img src="%s">' % url_construct(request, urlargs, pagename) + \
           u'</div>'
