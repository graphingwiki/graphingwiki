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
import re
import string

from urllib import unquote as url_unquote
from urllib import quote as url_quote

from MoinMoin import config
from MoinMoin import wikiutil

from graphingwiki.editing import metatable_parseargs, getvalues

Dependencies = ['metadata']

def t_cell(macro, vals, head=0):
    if head:
        out = macro.formatter.table_cell(1, {'class': 'meta_page'})
    else:
        out = macro.formatter.table_cell(1, {'class': 'meta_cell'})

    # It is assumed that this function is called
    # either with a string, in which case it is the
    # sole non-link value used in the table cell
    # or with a set of tuples, in which case the
    # values will be individually handled by its
    # source to be either textual or link
    if isinstance(vals, basestring):
        vals = [(vals, 'meta')]

    first_val = True

    for data, src in sorted(vals):
        # cosmetic for having a "a, b, c" kind of lists
        if not first_val:
            out += macro.formatter.text(',') + \
                   macro.formatter.linebreak()

        data = url_unquote(data.strip('"'))
        if not isinstance(data, unicode):
            data = unicode(data, config.charset)

        if head or src == 'link':
            out = out + macro.formatter.pagelink(1, data)

        out = out + macro.formatter.text(data)

        if head or src == 'link':
            out = out + macro.formatter.pagelink(0)

        first_val = False

    return out

def execute(macro, args):
    globaldata, pagelist, metakeys = metatable_parseargs(macro.request, args)
    _ = macro.request.getText

    # Start table
    out = macro.formatter.linebreak() + macro.formatter.table(1)

    # No data -> bail out quickly, Scotty
    if not pagelist:
        out += t_cell(macro, "%s: %s" % (_("Empty Metatable"), args))
        out += macro.formatter.table(0)

        globaldata.closedb()
        return out

    # Give a class to headers to make it customisable
    out += macro.formatter.table_row(1, {'rowclass': 'meta_header'})
    # Upper left cell is empty
    out += t_cell(macro, '')
    for key in metakeys:
        out = out + t_cell(macro, key)
    out += macro.formatter.table_row(0)

    pagelist = sorted(pagelist)

    for page in pagelist:
        out = out + macro.formatter.table_row(1)
        out = out + t_cell(macro, page, head=1)
        for key in metakeys:
            vals = getvalues(globaldata, page, key)
            out = out + t_cell(macro, vals)
        out += macro.formatter.table_row(0)
    out += macro.formatter.table(0)

    globaldata.closedb()

    req_url = macro.request.getScriptname() + \
              '/' + macro.request.page.page_name + \
              '?action=MetaEdit&args=' + args

    out += '<a href="%s" id="footer">[%s]</a>\n' % \
           (macro.request.getQualifiedURL(req_url), _('edit'))

    return out
