# -*- coding: iso-8859-1 -*-
"""
    MetaTable macro plugin to MoinMoin/Graphingwiki
     - Shows in tabular form the Metadata of desired pages

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
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
from codecs import getencoder

from MoinMoin import config

from graphingwiki.patterns import GraphData

Dependencies = ['metadata']

# Encoder from unicode to charset selected in config
encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]

def t_cell(macro, data, head=0):
    out = macro.formatter.table_cell(1)
    data = url_unquote(data)
    if not isinstance(data, unicode):
        data = unicode(data, config.charset)

    if head:
        out = out + macro.formatter.pagelink(1, data)
    
    out = out + macro.formatter.text(data)

    if head:
        out = out + macro.formatter.pagelink(0)

    return out
    
def execute(macro, args):
    arglist = [x.strip() for x in args.split(',')]

    globaldata = GraphData(macro.request).get_shelve()

    pagelist = []
    metakeys = set([])

    for arg in arglist:
        if arg.startswith('Category'):
            if not globaldata['in'].has_key(arg):
                # no such category
                continue
            for newpage in globaldata['in'][arg]:
                if not (newpage.endswith('Template') or
                        newpage.startswith('Category')):
                    pagelist.append(newpage)
        else:
            pagelist.append(arg)

    out = '\n' + macro.formatter.table(1)
    for page in pagelist:
        metakeys.update([x for x in globaldata['meta'].get(page, {}).keys()])

    metakeys = sorted(metakeys)
    # Give a class to headers to make it customisable
    out = out + macro.formatter.table_row(1, {'rowclass': 'meta_header'})
    out = out + t_cell(macro, '')
    for key in metakeys:
        out = out + t_cell(macro, key)
    out = out + macro.formatter.table_row(0)

    pagelist.sort()

    for page in pagelist:
        out = out + macro.formatter.table_row(1)
        out = out + t_cell(macro, page, head=1)
        for key in metakeys:
            data = ', '.join(globaldata['meta'].get(page, {}).get(key, ""))
            out = out + t_cell(macro, data)
            
        out = out + macro.formatter.table_row(0)

    out = out + macro.formatter.table(0)

    return out
