# -*- coding: utf-8 -*-"
"""
    getMetaJSON2 action for graphingwiki
     - alternative meta retrieval action that uses get_metas2
     and its abuse-sa query language for filtering metas

    @copyright: 2014 Lauri Pokka <larpo@codenomicon.com>
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

from graphingwiki.util import format_wikitext
from graphingwiki import values_to_form
from graphingwiki.editing import get_metas2

try:
    import simplejson as json
except ImportError:
    import json

def execute(pagename, request):
    request.content_type = "application/json"

    form = values_to_form(request.values)

    args = form.get('args', [None])[0]

    try:
        metas = get_metas2(request, args)
    except ImportError:
        request.status_code = 501
        request.write(u"abusehelper package not available")
        return
    except ValueError:
        request.status_code = 400
        request.write(u"invalid query '" + args + u"'")
        return

    if form.get('formatted', [None])[0]:
        formatted = {}
        values = []
        for page, vals in metas.items():
            values.extend(vals.keys())
            for val in vals.values():
                values.extend(val)

        for value in values:
            f = format_wikitext(request, value)
            if f != value and value not in formatted:
                formatted[value] = f

        metas = {'metas': metas, 'formatted': formatted}

    json.dump(metas, request, indent=2)

