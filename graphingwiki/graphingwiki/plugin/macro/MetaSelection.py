# -*- coding: utf-8 -*-"
"""
    MetaSelecttion macro plugin to MoinMoin/Graphingwiki
     - Show a selection list based on metatable arguments

    @copyright: 2009 by Marko Laakso <fenris@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from MoinMoin.Page import Page

from graphingwiki.editing import metatable_parseargs, get_metas
from graphingwiki.util import format_wikitext

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
                kw['querystr'] = '?action=recall&amp;rev=' + rev
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
                    legend='', checkAccess=True, styles=dict()):
    request = macro.request
    request.page.formatter = request.formatter
    _ = request.getText

    row = 0

    # Start table
    request.write(macro.formatter.linebreak() +
                  u'<div class="metaselection">' +
                  macro.formatter.table(1))

    if metakeys:
        # Give a class to headers to make it customisable
        request.write(macro.formatter.table_row(1, {'rowclass':
                                                    'meta_header'}))
        # Upper left cell is empty or has the desired legend
        t_cell(macro, [legend])

    for key in metakeys:
        style = styles.get(key, dict())
        
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
            t_cell(macro, [key], style=headerstyle)

    request.write(macro.formatter.table_row(0))

    tmp_page = request.page

    for page in pagelist:

        if '-gwikirevision-' in page:
            metas = get_metas(request, page, metakeys, 
                              checkAccess=checkAccess, formatLinks=True)
            page, revision = page.split('-gwikirevision-')
        else:
            metas = get_metas(request, page, metakeys, 
                              checkAccess=checkAccess, formatLinks=True)
            revision = ''

        pageobj = Page(request, page)
        request.page = pageobj
        request.formatter.page = pageobj

        row = row + 1

        if row % 2:
            request.write(macro.formatter.table_row(1, {'rowclass':
                                                        'metatable-odd-row'}))
        else:
            request.write(macro.formatter.table_row(1, {'rowclass':
                                                        'metatable-even-row'}))
        t_cell(macro, [page], head=1, rev=revision)

        for key in metakeys:
            style = styles.get(key, dict())
            t_cell(macro, metas[key], style=style)

        request.write(macro.formatter.table_row(0))

    request.page = tmp_page
    request.formatter.page = tmp_page

    request.write(macro.formatter.table(0))
    request.write(u'</div>')

def formatMetaSelection(request, pages, keys, styles, addpagename=False):

    f = request.formatter
    divfmt = {'class': 'metaselection_area'}
    listfmt = {'class': 'metaselection_list'}
    entryfmt = {'class': 'metaselection_entry'}
    
    result = ''
    result = f.div(1, **divfmt)
    result += f.bullet_list(1, **listfmt)
    
    tmp_page = request.page

    for page in pages:

        pageobj = Page(request, page)
        request.page = pageobj
        request.formatter.page = pageobj

        metas = get_metas(request, page, keys, 
                          checkAccess=True, formatLinks=True)

        result += f.listitem(1, **entryfmt)

        args = {'class': 'metaselection_link'}

        for key in keys:
            for val in metas[key]:
                text = format_wikitext(request, val)
                result += pageobj.link_to_raw(request, text=text, **args)

        if addpagename:
            result += pageobj.link_to_raw(request, 
                                          text=pageobj.page_name, **args)

        result += f.listitem(0)

    request.page = tmp_page
    request.formatter.page = tmp_page

    result += f.bullet_list(0)
    result += f.div(0)
    return result

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
    return formatMetaSelection(self.request, pages, keys, styles, addpagename)
