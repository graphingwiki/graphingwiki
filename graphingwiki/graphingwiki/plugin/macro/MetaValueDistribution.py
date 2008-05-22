# -*- coding: utf-8 -*-"
"""
    MetaValueDistribution macro plugin to MoinMoin/Graphingwiki
     - Shows distribution of meta values for desired category & key

    @copyright: 2008 by Juhani Eronen <exec@iki.fi> and
                        Mika Seppänen
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
import StringIO

from urllib import unquote as url_unquote
from urllib import quote as url_quote

from MoinMoin import config
from MoinMoin.parser.wiki import Parser
from MoinMoin.Page import Page

from graphingwiki.editing import metatable_parseargs, getmetas

Dependencies = ['metadata']

def t_cell(macro, value):
    out = macro.request

    style = dict()
    style['class'] = 'meta_cell'

    out.write(macro.formatter.table_cell(1, attrs=style))

    if not isinstance(value, unicode):
        value = unicode(value, config.charset)

    value = value.strip()

    out.page.formatter = out.formatter
    parser = Parser(value, out)
    # No line anchors of any type to table cells
    out.page.formatter.in_p = 1
    parser._line_anchordef = lambda: ''

    # Using StringIO in order to strip the output
    value = StringIO.StringIO()
    out.redirect(value)
    # Produces output on a single table cell
    out.page.format(parser)
    out.redirect()

    out.write(value.getvalue().strip())

def construct_table(macro, globaldata, pagelist, key, sort_order):
    request = macro.request
    request.page.formatter = request.formatter

    count = dict()

    orginalPage = request.page

    for page in pagelist:
        pageobj = Page(request, unicode(url_unquote(page), config.charset))
        request.page = pageobj
        request.formatter.page = pageobj

        # WARNING: Skipping access check because we know that metatable_parseargs
        #          already  checked  them. If you plan to use this code elsewhere
        #          you should make sure that you check for access.
        metas = getmetas(request, globaldata, page, [key], display=False,
                         checkAccess=False)

        values = [x for x,y in metas[key]]
        for value in values:
            current = count.get(value, 0)
            count[value] = current + 1

    request.write(macro.formatter.linebreak() +
                  u'<div class="metatable">' +
                  macro.formatter.table(1))
    request.write(macro.formatter.table_row(1, {'rowclass':
                                                'meta_header'}))
    t_cell(macro, key)
    t_cell(macro, "Count")
    request.write(macro.formatter.table_row(0))

    row = 0

    tmp = list()

    for value, count in count.iteritems():
        tmp.append((count, value))

    if sort_order == "value":
        tmp.sort(key=lambda (x,y): y)
    elif sort_order == "count":
        tmp.sort(key=lambda (x,y): x, reverse=True)

    for value, key in tmp:
        row = row + 1

        if row % 2:
            request.write(macro.formatter.table_row(1, {'rowclass':
                                                        'metatable-odd-row'}))
        else:
            request.write(macro.formatter.table_row(1, {'rowclass':
                                                        'metatable-even-row'}))

        t_cell(macro, key)
        t_cell(macro, u"%d" % value)
        request.write(macro.formatter.table_row(0))

    request.page = orginalPage 
    request.formatter.page = orginalPage

    request.write(macro.formatter.table(0))
    request.write(u'</div>')

def show_error(macro, args, error):
    request = macro.request

    request.write(macro.formatter.linebreak() +
                  u'<div class="metatable">' +
                  macro.formatter.table(1))
    request.write(macro.formatter.table_row(1))
    t_cell(macro, "%s: MetaValueDistribution(%s)" % (error, ",".join(args)))
    request.write(macro.formatter.table_row(0))
    request.write(macro.formatter.table(0) +
                  u'</div>')

def execute(macro, args):
    request = macro.request

    args = args.split(",")
    args = map(lambda x: x.strip(), args)

    if len(args) not in [2,3]:
        show_error(macro, args, "Wrong nunber of arguments")
        return ""

    query = "%s,||%s||" % tuple(args[:2])

    # Note, metatable_parseargs deals with permissions
    globaldata, pagelist, metakeys, _ = \
                metatable_parseargs(request, query, get_all_keys=True)

    if not pagelist:
        show_error(macro, args, "No content")
        globaldata.closedb()
        return ""

    if len(metakeys) != 1:
        show_error(macro, args, "Too many keys")
        globaldata.closedb()
        return ""

    key = metakeys[0]

    if len(args) == 3:
        sort_order = args[2].strip().lower()
    else:
        sort_order = "value"

    if sort_order not in ["value", "count"]:
        show_error(macro, args, "Bad sort order (should be either '''value''' or '''count''')")
        globaldata.closedb()
        return ""

    # We're sure the user has the access to the page, so don't check
    construct_table(macro, globaldata, pagelist, key, sort_order)

    globaldata.closedb()
    return ""
