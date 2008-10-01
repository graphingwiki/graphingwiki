# -*- coding: utf-8 -*-"
"""
    MetaInclude macro plugin to MoinMoin/Graphingwiki
     - Shows in pages that match give metatable arguments

    @copyright: 2008 therauli <therauli@ee.oulu.fi>
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

from MoinMoin import Page

from graphingwiki.editing import metatable_parseargs


def execute(macro, args):
    this_page = macro.request.page.page_name
    
    request = macro.request
    if args is None:
        args = ''
        
    globaldata, pagelist, metakeys, styles = metatable_parseargs(macro.request, args, get_all_keys=True)

    request = macro.request
    _ = request.getText

    for page_name in [url_unquote(name) for name in pagelist]:
        page = Page.Page(request, page_name)
        request.write('<h1> Page:%s </h1>' % page_name)
        page.send_page(content_only=1)
        request.write(macro.formatter.div(1, css_class="include-link"))
        request.write(page.link_to(request, '[Goto: %s]' % page_name, css_class="include-page-link"))
        request.write(page.link_to(request, '[%s]' % (_('edit', formatted=False),), css_class="include-edit-link", querystr={'action': 'edit', 'backto': this_page}))
        request.write(macro.formatter.div(0))
        request.write(macro.request.formatter.rule())
