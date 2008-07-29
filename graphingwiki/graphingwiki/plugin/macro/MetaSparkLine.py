# -*- coding: utf-8 -*-"
"""
    SparkLine macro plugin to MoinMoin
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
from urllib import quote as url_quote

from graphingwiki.patterns import encode

Dependencies = ['metadata']

def execute(macro, args):
    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

    req_url = request.getScriptname() + '/' + request.page.page_name
    req_url += '?action=metasparkline'

    arglist = [x.strip() for x in args.split(',')]
    # Args: page name (mandatory)
    #       key name (mandatory)
    #       data points to include (optional)
    #       sparkline style (default (line+txt), line, dot)
    args = ['page', 'key', 'points', 'style']
    for i, x in enumerate(arglist):
        req_url += "&%s=%s" % (args[i], url_quote(encode(x)))

    return u'<img class="metasparkline" src="%s" alt="sparkline">' % \
        (request.getQualifiedURL(req_url)) 
