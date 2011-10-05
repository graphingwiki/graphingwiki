# -*- coding: utf-8 -*-"
"""
    getMetaStructJSON action for graphingwiki

    @copyright: 2010 Erno Kuusela <erno@iki.fi>
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

import MoinMoin.wikiutil as wikiutil

from graphingwiki import values_to_form

try:
    import simplejson as json
except ImportError:
    import json

def execute(pagename, request):
    request.content_type = "text/plain; charset=ascii"

    form = values_to_form(request.values)

    args = form.get('args', [None])[0]
    key = form.get('getvalues', [None])[0]

    do_action = wikiutil.importPlugin(request.cfg, "xmlrpc", "GetMetaStruct",
                                      "do_action")

    if not args:
        if key:
            results = do_action(request, "%s=/.+/" % key)
            metas = dict()
            for page in results:
                values = results[page].get(key, [])
                if values:
                    metas.setdefault(page, list())
                    metas[page].extend(values)
        else:
            metas = do_action(request, pagename)
    else:
        metas = do_action(request, args)

    json.dump(metas, request, indent=2)

