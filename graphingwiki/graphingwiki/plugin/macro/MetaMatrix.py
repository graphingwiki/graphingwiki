# -*- coding: utf-8 -*-"
"""
    MetaSelecttion macro plugin to MoinMoin/Graphingwiki
     - Show a selection list based on metatable arguments

    @copyright: 2009 by Marko Laakso <fenris@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import re

from MoinMoin.Page import Page
from MoinMoin.macro.Include import _sysmsg

from graphingwiki.editing import metatable_parseargs, get_metas
from graphingwiki.util import format_wikitext, url_escape
from graphingwiki.editing import ordervalue

Dependencies = ['metadata']

def t_cell(macro, vals, head=0, style=dict(), rev=''):
    out = macro.request

    if not style.has_key('class'):
        if head:
            style['class'] = 'meta_page'
        else:
            style['class'] = 'meta_cell'

    out.write(macro.formatter.table_cell(1, attrs=style))
    cellstyle = style.get('gwikistyle', '').strip('"')

    if cellstyle == 'list':
        out.write(macro.formatter.bullet_list(1))

    first_val = True

    for data in sorted(vals):

        # cosmetic for having a "a, b, c" kind of lists
        if cellstyle not in ['list'] and not first_val:
            out.write(macro.formatter.text(',') + \
                      macro.formatter.linebreak())

        if head:
            kw = dict()
            if rev:
                kw['querystr'] = '?action=recall&rev=' + rev
            out.write(macro.formatter.pagelink(1, data, **kw))
            out.write(macro.formatter.text(data))
            out.write(macro.formatter.pagelink(0))
        elif data.strip():
            if cellstyle == 'list':
                out.write(macro.formatter.listitem(1))

            out.write(format_wikitext(out, data))

            if cellstyle == 'list':
                out.write(macro.formatter.listitem(0))

        first_val = False

    if cellstyle == 'list':
        out.write(macro.formatter.bullet_list(1))

def construct_table(macro, pagelist, metakeys, 
                    legend='', checkAccess=True, styles=dict(), 
                    addpagename=False):
    request = macro.request
    request.page.formatter = request.formatter
    _ = request.getText

    row = 0

    entryfmt = {'class': 'metamatrix_entry'}

    # Start table
    request.write(macro.formatter.linebreak() +
                  u'<div class="metamatrix">' +
                  macro.formatter.table(1))

    # Give a class to headers to make it customisable
    request.write(macro.formatter.table_row(1, {'rowclass':
                                                'meta_head'}))
    # Upper left cell is empty or has the desired legend
    t_cell(macro, [legend])

    x_key, y_key = metakeys[:2]

    x_values, y_values = set(), set()

    page_vals = dict()

    for page in pagelist:
        page_vals[page] = get_metas(request, page, metakeys, checkAccess=False)

        x_values.update(page_vals[page].get(x_key, set()))
        y_values.update(page_vals[page].get(y_key, set()))

    metakeys = metakeys[2:]

    # Make header row
    for oval, value in sorted((ordervalue(y), y) for y in y_values):

        style = styles.get(y_key, dict())
        
        # Styles can modify key naming
        name = style.get('gwikiname', '').strip('"')

        # We don't want stuff like bullet lists in out header
        headerstyle = dict()
        for st in style:
            if not st.startswith('gwiki'):
                headerstyle[st] = style[st]

        if name:
            t_cell(macro, [name], style=headerstyle)
        else:
            t_cell(macro, [value], style=headerstyle)

    request.write(macro.formatter.table_row(0))

    tmp_page = request.page

    f = macro.formatter

    # Table
    for oval, x_value in sorted((ordervalue(x), x) for x in x_values):
        row = row + 1

        if row % 2:
            request.write(f.table_row(1, {'rowclass':
                                              'metamatrix-odd-row'}))
        else:
            request.write(f.table_row(1, {'rowclass':
                                              'metamatrix-even-row'}))
        t_cell(macro, [x_value])
        
        for oval, y_value in sorted((ordervalue(y), y) for y in y_values):
            style = styles.get(y_value, dict())
            
            if not style.has_key('class'):
                style['class'] = 'meta_cell'

            macro.request.write(f.table_cell(1, attrs=style))

            for page in pagelist:
                if (x_value in page_vals[page].get(x_key, set()) and
                    y_value in page_vals[page].get(y_key, set())):

                    result = ''
                    result += f.listitem(1, **entryfmt)

                    for key in metakeys:
                        for val in page_vals[page].get(key, list()):
                            result += f.url(1, page, 'metamatrix_link')
                            result += format_wikitext(request, val)
                            result += f.url(0)

                    if addpagename:
                        result += f.url(1, page, 'metamatrix_link')
                        result += f.text(page)
                        result += f.url(0)

                    result += f.listitem(0)
                    macro.request.write(result)
                    
        request.write(macro.formatter.table_row(0))

    request.page = tmp_page
    request.formatter.page = tmp_page

    request.write(macro.formatter.table(0))
    request.write(u'</div>')

def execute(self, args):
    if args is None:
        args = ''

    addpagename = False

    if args.strip().endswith('addpagename'):
        addpagename = True
        args = ','.join(args.split(',')[:-1])

    # Note, metatable_parseargs deals with permissions
    pages, keys, styles = metatable_parseargs(self.request,
                                              args, get_all_keys=True)

    if len(keys) < 2:
        return _sysmsg % ('error', 
                          request.getText('Need a minimum of three keys to build matrix'))

    legend = "%s/%s" % (keys[0], keys[1])

    return construct_table(self, pages, keys, legend=legend, 
                           checkAccess=False, styles=styles, 
                           addpagename=addpagename)
