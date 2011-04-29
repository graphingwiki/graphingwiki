# -*- coding: utf-8 -*-"
"""
    MetaValueDistribution macro plugin to MoinMoin/Graphingwiki
     - Shows distribution of meta values for desired metatable args

    @copyright: 2008-2010 by Juhani Eronen <exec@iki.fi> and
                          Mika Seppänen, Marko Laakso
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
import StringIO

from MoinMoin.parser.text_moin_wiki import Parser
from MoinMoin.Page import Page

from graphingwiki.editing import metatable_parseargs, get_metas

Dependencies = ['metadata']

def t_cell(macro, value):
    out = macro.request

    style = dict()
    style['class'] = 'meta_cell'

    out.write(macro.formatter.table_cell(1, attrs=style))

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

def construct_table(macro, pagelist, key, sort_order):
    request = macro.request
    request.page.formatter = request.formatter

    count = dict()

    orginalPage = request.page

    for page in pagelist:
        pageobj = Page(request, page)
        request.page = pageobj
        request.formatter.page = pageobj

        # WARNING: Skipping access check because we know that metatable_parseargs
        #          already  checked  them. If you plan to use this code elsewhere
        #          you should make sure that you check for access.
        metas = get_metas(request, page, [key], checkAccess=False)

        for value in metas[key]:
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

    s = sum(map(lambda (x,y): x, tmp))

    tmp.append((s, "Sum"))

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
    t_cell(macro, "%s: MetaValueDistribution(%s)" % (error, args))
    request.write(macro.formatter.table_row(0))
    request.write(macro.formatter.table(0) +
                  u'</div>')

def execute(macro, args):
    request = macro.request

    if not args:
        return u''

    args = args.strip().split(',')

    sort_order = 'value'
    if args[-1].strip().lower() == 'value':
         args = args[:-1]
    elif args[-1].strip().lower() == 'count':
        sort_order = 'count'
        args = args[:-1]
    args = ','.join(args)

    # Note, metatable_parseargs deals with permissions
    pagelist, metakeys, _ = \
        metatable_parseargs(request, args, get_all_keys=True)

    if not pagelist:
        show_error(macro, args, "No content")
        return ""

    if len(metakeys) != 1:
        show_error(macro, args, "Too many keys")
        return ""

    key = metakeys[0]

    if sort_order not in ["value", "count"]:
        show_error(macro, args, "Bad sort order (should be either '''value''' or '''count''')")
        return ""

    # We're sure the user has the access to the page, so don't check
    construct_table(macro, pagelist, key, sort_order)

    return ''
