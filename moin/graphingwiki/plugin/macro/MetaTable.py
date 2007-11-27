# -*- coding: utf-8 -*-"
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
from MoinMoin.parser.wiki import Parser

from graphingwiki.editing import metatable_parseargs, getvalues
from graphingwiki.editing import check_link, formatting_rules

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

        if not isinstance(data, unicode):
            data = unicode(data, config.charset)

        if head:
            out = out + macro.formatter.pagelink(1, data)

        if src == 'link':
            # Check for link type
            link = check_link(macro.all_re, data)
            # If it does not match for any specific link type,
            # just make a page link. Also, as
            # u'SomePage/SomeOther Page' matches to
            # ('word', 'SomePage/SomeOther', detect this and make
            # a normal link
            if (not link \
                or link[1] != data):
                out = out + macro.formatter.pagelink(1, data)
                out = out + macro.formatter.text(data)
            else:
                typ, hit = link
                replace = getattr(macro.parser, '_' + typ + '_repl')
                attrs = replace(hit)
                out = out + attrs
            out = out + macro.formatter.pagelink(0)
        else:
            out = out + macro.formatter.text(data)

        if head:
            out = out + macro.formatter.pagelink(0)

        first_val = False

    return out

def execute(macro, args):
    # Note, metatable_parseargs deals with permissions
    globaldata, pagelist, metakeys = metatable_parseargs(macro.request, args)
    request = macro.request
    _ = request.getText

    # Start table
    out = macro.formatter.linebreak() + macro.formatter.table(1)

    # No data -> bail out quickly, Scotty
    if not pagelist:
        out += t_cell(macro, "%s (%s)" %
                      (_("Metatable has no contents"), args))
        out += macro.formatter.table(0)

        globaldata.closedb()
        return out

    if metakeys:
        # Give a class to headers to make it customisable
        out += macro.formatter.table_row(1, {'rowclass': 'meta_header'})
        # Upper left cell is empty
        out += t_cell(macro, '')

    # Start parser
    macro.parser = Parser('', request)
    macro.parser.formatter = request.formatter    
    macro.all_re = formatting_rules(request, macro.parser)

    for key in metakeys:
        key = unicode(url_unquote(key), config.charset)
        if check_link(macro.all_re, key):
            out = out + t_cell(macro, [(key, 'link')])
        else:
            out = out + t_cell(macro, key)
    out += macro.formatter.table_row(0)

    for page in pagelist:
        out = out + macro.formatter.table_row(1)
        out = out + t_cell(macro, url_unquote(page), head=1)
        for key in metakeys:
            vals = getvalues(request, globaldata, page, key)
            out = out + t_cell(macro, vals)
        out += macro.formatter.table_row(0)
    out += macro.formatter.table(0)

    globaldata.closedb()

    def action_link(action, linktext, args):
        req_url = request.getScriptname() + \
                  '/' + request.page.page_name + \
                  '?action=' + action + '&args=' + args 
        return '<a href="%s" id="footer">[%s]</a>\n' % \
               (request.getQualifiedURL(req_url), _(linktext))

    args = url_quote(args)
    out += action_link('MetaEdit', 'edit', args)
    out += action_link('metaCSV', 'csv', args)

    return out
