# -*- coding: utf-8 -*-"
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
from urllib import unquote as url_unquote

from MoinMoin.support.werkzeug.datastructures import CombinedMultiDict, \
    MultiDict
from MoinMoin.Page import Page
from MoinMoin import wikiutil
from MoinMoin import config

from graphingwiki.util import encode, url_construct

Dependencies = ['attachments']

def uri_params(uri):
    args = {}
    allstr = uri.split('?')
    if len(allstr) > 1:
        uri, argstr = allstr
        argstr = argstr.split('&')

        for arg in argstr:
            key, val = arg.split('=')
            # Do not encode the already-encoded attachments
            if key == 'attachment':
                key = url_unquote(key)
                val = url_unquote(val)
                # Attachment strings are encoded,
                # although Moin gives them as unicode ->
                # decode to unicode. This should be actually
                # done in the inline-bit in ViewDot-action,
                # but is done here to assure functionality
                # of existing wiki pages
                val = val.encode('raw_unicode_escape')
                val = unicode(val, config.charset)

                args.setdefault(key,
                                []).append(val)
            else:
                args.setdefault(encode(url_unquote(key)),
                                []).append(encode(url_unquote(val)))

    return uri, args

def execute(macro, args):
    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

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

    if not arglist:
        return ""

    uri, args = uri_params(arglist[0])

    if not args:
        return ""

    pagename = url_unquote(uri)

    old_page = request.page
    old_values = request.values
    old_url = getattr(request, 'url', '')

    request.page = Page(request, pagename)
    req_url = url_construct(request, args, pagename)
    request.values = CombinedMultiDict([MultiDict(args)])
    request.url = req_url

    request.write(u'<div class="viewdot">')
    dotviewer(pagename, request, **kw)

    request.page = old_page
    request.values = old_values
    del request.url
    if old_url:
        request.url = old_url

    return '<a href="%s&amp;view=View" class="graph-link">[%s]</a>\n</div>' % \
        (req_url, _('View'))
