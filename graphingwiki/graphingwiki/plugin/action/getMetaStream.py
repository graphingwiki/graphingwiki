# -*- coding: utf-8 -*-"
"""
    getMetaStream action for graphingwiki
     - alternative meta retrieval action that uses
      abuse-sa query language for filtering metas
      and returns Line Delimeted JSON or event-stream

    @copyright: 2015 Lauri Pokka <larpo@codenomicon.com>
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

from graphingwiki import values_to_form
from graphingwiki.editing import iter_metas

try:
    import simplejson as json
except ImportError:
    import json


def metas_to_json(req, q):
    def flatten(arr):
        if len(arr) == 1:
            return arr[0]
        else:
            return arr

    for page, metas in iter_metas(req, q):
        flattened = [(key, flatten(val)) for key, val in metas.items()]
        yield json.dumps(dict(flattened + [('gwikipagename', page)]))


class MetaStreamer(object):
    def __init__(self, iterator):
        self.iterator = iterator
        self.done = False

    def read(self, *args):
        if not self.done:
            try:
                row = self.iterator.next()
                return "data: " + row + "\n\n"
            except StopIteration:
                self.done = True
                return "event: done\ndata: \n\n"
        else:
            return None

    def close(self):
        self.done = True


def execute(pagename, request):
    form = values_to_form(request.values)
    query = form.get('q', [None])[0]
    output_format = form.get('type', [""])[0]
    try:
        json_rows = metas_to_json(request, query)

        accepts = unicode(request.request.accept_mimetypes)

        if output_format == "stream" or "text/event-stream" in accepts:
            request.content_type = "text/event-stream"

            ## send_file seems to be the least hacky way
            ## for sending streamed content in MoinMoin
            request.send_file(MetaStreamer(json_rows))
        else:
            request.content_type = "application/json;boundary=NL"

            for row in json_rows:
                request.write(row + "\n")

    except ImportError:
        request.status_code = 501
        request.write(u"abusehelper package not available")
    except ValueError:
        request.status_code = 400
        request.write(u"invalid query '" + query + u"'")