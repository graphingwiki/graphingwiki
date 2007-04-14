# -*- coding: iso-8859-1 -*-
"""
    .dot parser plugin to MoinMoin
     - Simple inline layouter of dot data

    @copyright: 2005 by Juhani Eronen <exec@iki.fi>
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

import os
from tempfile import mkstemp
from base64 import b64encode

from MoinMoin import wikiutil

from graphingwiki.graphrepr import Graphviz

Dependencies = ['attachments']

class Parser(object):

    extensions = ['.dot']

    def __init__(self, raw, request, **kw):
        # save call arguments for later use in format()
        self.raw = raw.encode('utf-8')
        self.request = request
        self.layoutformat = 'png'
        self.graphengine = 'neato'
        
        attrs, msg = wikiutil.parseAttributes(request,
                                              kw.get('format_args', ''))
        if 'engine' in attrs:
            self.graphengine = attrs['engine'].encode('utf-8')[1:-1]

    def getLayoutInFormat(self, graphviz, format):
        tmp_fileno, tmp_name = mkstemp()
        graphviz.layout(file=tmp_name, format=format)
        f = file(tmp_name)
        data = f.read()
        os.close(tmp_fileno)
        os.remove(tmp_name)

        return data

    def format(self, formatter):
        graphviz = Graphviz(engine=self.graphengine, string=self.raw)
        img = self.getLayoutInFormat(graphviz, self.layoutformat)

        imgbase = "data:image/" + self.layoutformat + ";base64," + \
                  b64encode(img)

        page = ('<img src="' + imgbase +
                '" alt="visualisation">\n')
        imgbase = "data:image/svg+xml;base64," + b64encode(img)

        self.request.write(page)
