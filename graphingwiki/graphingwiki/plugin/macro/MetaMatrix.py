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

from graphingwiki import url_escape
from graphingwiki.editing import metatable_parseargs, get_metas, \
    metas_to_abs_links
from graphingwiki.util import format_wikitext
from graphingwiki.editing import ordervalue

Dependencies = ['metadata']

def t_cell(macro, vals, head=0, style=dict(), rev=''):
    out = str()

    if not style.has_key('class'):
        if head:
            style['class'] = 'meta_page'
        else:
            style['class'] = 'meta_cell'

    out += macro.formatter.table_cell(1, attrs=style)
    cellstyle = style.get('gwikistyle', '').strip('"')

    if cellstyle == 'list':
        out += macro.formatter.bullet_list(1)

    first_val = True

    for data in sorted(vals):

        # cosmetic for having a "a, b, c" kind of lists
        if cellstyle not in ['list'] and not first_val:
            out += macro.formatter.text(',') + macro.formatter.linebreak()

        if head:
            kw = dict()
            if rev:
                kw['querystr'] = '?action=recall&amp;rev=' + rev
            out += macro.formatter.pagelink(1, data, **kw)
            out += macro.formatter.text(data)
            out += macro.formatter.pagelink(0)
        elif data.strip():
            if cellstyle == 'list':
                out += macro.formatter.listitem(1)

            out += format_wikitext(macro.request, data)

            if cellstyle == 'list':
                out += macro.formatter.listitem(0)

        first_val = False

    if cellstyle == 'list':
        out += macro.formatter.bullet_list(1)

    return out

def construct_table(macro, pagelist, metakeys, 
                    legend='', checkAccess=True, styles=dict(), 
                    addpagename=False):
    request = macro.request
    request.page.formatter = request.formatter
    _ = request.getText
    out = str()

    row = 0

    entryfmt = {'class': 'metamatrix_entry'}

    # Start table
    out += macro.formatter.linebreak() + u'<div class="metamatrix">' + \
        macro.formatter.table(1)

    # Give a class to headers to make it customisable
    out += macro.formatter.table_row(1, {'rowclass': 'meta_head'})
    # Upper left cell is empty or has the desired legend
    out += t_cell(macro, [legend])

    x_key, y_key = metakeys[:2]

    x_values, y_values = set(), set()

    page_vals = dict()

    for page in pagelist:
        page_vals[page] = get_metas(request, page, metakeys, 
                                    checkAccess=False, formatLinks=True)
        
        x_val = page_vals[page].get(x_key, set())
        y_val = page_vals[page].get(y_key, set())
        x_values.update([(page, x) for x in x_val])
        y_values.update([(page, y) for y in y_val])

    metakeys = metakeys[2:]

    header_cells = list()
    # Make header row
    for oval, value, page in sorted((ordervalue(y), y, page) \
                                        for page, y in y_values):

        style = styles.get(y_key, dict())
        
        # Styles can modify key naming
        name = style.get('gwikiname', '').strip('"')

        # We don't want stuff like bullet lists in out header
        headerstyle = dict()
        for st in style:
            if not st.startswith('gwiki'):
                headerstyle[st] = style[st]

        if name:
            if not (value, name) in header_cells:
                header_cells.append((value, name))
        else:
            showvalue = metas_to_abs_links(request, page, [value])
            if not (value, showvalue[0]) in header_cells:
                header_cells.append((value, showvalue[0]))

    for value, showvalue in header_cells:
        out += t_cell(macro, [showvalue], style=headerstyle)

    out += macro.formatter.table_row(0)

    tmp_page = request.page

    f = macro.formatter

    # Table
    row_cells = list()
    row_values = list()
    for oval, x_value, page in sorted((ordervalue(x), x, page) \
                                          for page, x in x_values):
        if not (oval, x_value) in row_values:
            row_cells.append((oval, x_value, page))
            row_values.append((oval, x_value))

    for oval, x_value, page in row_cells:
        row = row + 1

        if row % 2:
            out += f.table_row(1, {'rowclass': 'metamatrix-odd-row'})
        else:
            out += f.table_row(1, {'rowclass': 'metamatrix-even-row'})
        value = metas_to_abs_links(request, page, [x_value])
        out += t_cell(macro, value)
        
        for y_value, showvalue in header_cells:
            style = styles.get(y_value, dict())
            
            if not style.has_key('class'):
                style['class'] = 'meta_cell'

            out += f.table_cell(1, attrs=style)

            for page in pagelist:
                pageobj = Page(request, page)

                if (x_value in page_vals[page].get(x_key, set()) and
                    y_value in page_vals[page].get(y_key, set())):

                    result = ''

                    args = {'class': 'metamatrix_link'}

                    # Were there vals?
                    vals = None

                    for key in metakeys:
                        for val in page_vals[page].get(key, list()):
                            
                            # Strip ugly brackets from bracketed links
                            val = val.lstrip('[').strip(']')

                            result += f.listitem(1, **entryfmt)

                            result += pageobj.link_to(request, 
                                                      text=val, **args)
                            result += f.listitem(0)

                            vals = val

                    if addpagename:
                        result += f.listitem(1, **entryfmt)
                        result += pageobj.link_to(request, **args)
                        result += f.listitem(0)
                        
                    out += result
                    
        out += macro.formatter.table_row(0)

    request.page = tmp_page
    request.formatter.page = tmp_page

    out += macro.formatter.table(0)
    out += u'</div>'

    return out

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
                          self.request.getText('Need a minimum of two keys to build matrix'))

    legend = "%s/%s" % (keys[0], keys[1])

    return construct_table(self, pages, keys, legend=legend, 
                           checkAccess=False, styles=styles, 
                           addpagename=addpagename)
