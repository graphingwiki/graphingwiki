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
from urllib import quote

from MoinMoin.Page import Page

from graphingwiki import url_escape, id_escape, SEPARATOR
from graphingwiki.editing import metatable_parseargs, get_metas, \
    get_properties, PROPERTIES, add_matching_redirs
from graphingwiki.util import format_wikitext, form_writer

try:
    import simplejson as json
except ImportError:
    import json

Dependencies = ['metadata']

# SVG color scheme
COLORS = ['aliceblue', 'antiquewhite', 'aqua', 'aquamarine', 
          'azure', 'beige', 'bisque', 'black', 'blanchedalmond', 
          'blue', 'blueviolet', 'brown', 'burlywood', 'cadetblue', 
          'chartreuse', 'chocolate', 'coral', 'cornflowerblue', 
          'cornsilk', 'crimson', 'cyan', 'darkblue', 'darkcyan', 
          'darkgoldenrod', 'darkgray', 'darkgreen', 'darkgrey', 
          'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange', 
          'darkorchid', 'darkred', 'darksalmon', 'darkseagreen', 
          'darkslateblue', 'darkslategray', 'darkslategrey', 
          'darkturquoise', 'darkviolet', 'deeppink', 'deepskyblue', 
          'dimgray', 'dimgrey', 'dodgerblue', 'firebrick', 'floralwhite', 
          'forestgreen', 'fuchsia', 'gainsboro', 'ghostwhite', 'gold', 
          'goldenrod', 'gray', 'grey', 'green', 'greenyellow', 'honeydew', 
          'hotpink', 'indianred', 'indigo', 'ivory', 'khaki', 'lavender', 
          'lavenderblush', 'lawngreen', 'lemonchiffon', 'lightblue', 
          'lightcoral', 'lightcyan', 'lightgoldenrodyellow', 'lightgray', 
          'lightgreen', 'lightgrey', 'lightpink', 'lightsalmon', 
          'lightseagreen', 'lightskyblue', 'lightslategray', 'lightslategrey', 
          'lightsteelblue', 'lightyellow', 'lime', 'limegreen', 'linen', 
          'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 
          'mediumorchid', 'mediumpurple', 'mediumseagreen', 'mediumslateblue', 
          'mediumspringgreen', 'mediumturquoise', 'mediumvioletred', 
          'midnightblue', 'mintcream', 'mistyrose', 'moccasin', 'navajowhite', 
          'navy', 'oldlace', 'olive', 'olivedrab', 'orange', 'orangered', 
          'orchid', 'palegoldenrod', 'palegreen', 'paleturquoise', 
          'palevioletred', 'papayawhip', 'peachpuff', 'peru', 'pink', 
          'plum', 'powderblue', 'purple', 'red', 'rosybrown', 'royalblue', 
          'saddlebrown', 'salmon', 'sandybrown', 'seagreen', 'seashell', 
          'sienna', 'silver', 'skyblue', 'slateblue', 'slategray', 
          'slategrey', 'snow', 'springgreen', 'steelblue', 'tan', 'teal', 
          'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'white', 
          'whitesmoke', 'yellow', 'yellowgreen']

def wrap_span(request, pagename, key, data, id):
    fdata = format_wikitext(request, data)

    if not key:
        return fdata

    if '->' in key:
        # Get indirection data, the same function get_metas uses
        linkdata = add_matching_redirs(request, request.page, {}, {}, {},
                                       key, pagename, key, linkdata={})

        # Broken link, do not give anything editable as this will not
        # work in any case.
        if not linkdata:
            return fdata

        if key in linkdata:
            for pname in linkdata[key]:
                # data == key when we're writing out the header
                if data in linkdata[key][pname] or data == key:
                    pagename = pname
                    key = key.split('->')[-1]
                    break

    if data == fdata:
        return form_writer(
            u'<span data-page="%s" data-key="%s" data-index="%s">',
            pagename, key, str(id)) + fdata +'</span>'

    return form_writer(
        u'<span data-page="%s" data-key="%s" data-value="%s" data-index="%s">',
        pagename, key, data, str(id)) + fdata +'</span>'

def t_cell(request, pagename, vals, head=0, 
           style=None, rev='', key='', pathstrip=0, linkoverride=''):
    formatter = request.formatter
    out = str()

    if style is None:
	style = dict()

    if not style.has_key('class'):
        if head:
            style['class'] = 'meta_page'
        else:
            style['class'] = 'meta_cell'

    out += formatter.table_cell(1, attrs=style)
    cellstyle = style.get('gwikistyle', '').strip('"')

    if cellstyle == 'list':
        out += formatter.bullet_list(1)

    first_val = True

    for i, data in sorted(enumerate(vals), cmp=lambda x,y: cmp(x[1], y[1])):
        # cosmetic for having a "a, b, c" kind of lists
        if cellstyle not in ['list'] and not first_val:
            out += formatter.text(',') + formatter.linebreak()

        if head:
            page = Page(request, data)
            if request.user.may.write(data):
                img = request.theme.make_icon('edit')
                out += formatter.span(1, css_class="meta_editicon")
                out += page.link_to_raw(request, img,
                                        querystr={'action': 'edit'},
                                        rel='nofollow')
                img = request.theme.make_icon('formedit')
                out += page.link_to_raw(request, img,
                                        querystr={'action': 'MetaFormEdit'},
                                        rel='nofollow')
                out += formatter.span(0)
            kw = dict()
            if rev:
                kw['querystr'] = '?action=recall&rev=' + rev
            linktext = data
            if linkoverride:
                linktext = linkoverride
            elif pathstrip:
                dataparts = data.split('/')
                if pathstrip > len(dataparts):
                    pathstrip = len(dataparts) - 1
                if pathstrip:
                    linktext = '/'.join(reversed(
                            dataparts[:-pathstrip-1:-1]))
            out += formatter.pagelink(1, data, **kw)
            out += formatter.text(linktext)
            out += formatter.pagelink(0)
        elif data.strip():
            if cellstyle == 'list':
                out += formatter.listitem(1)

            out += wrap_span(request, pagename, key, data, i)

            if cellstyle == 'list':
                out += formatter.listitem(0)

    if not vals:
        out += wrap_span(request, pagename, key, '', 0)

        first_val = False

    if cellstyle == 'list':
        out += formatter.bullet_list(1)

    out += formatter.table_cell(0)
    return out

def construct_table(request, pagelist, metakeys, 
                    legend='', checkAccess=True, styles=dict(), options=dict()):
    request.page.formatter = request.formatter
    formatter = request.formatter
    _ = request.getText
    pagename = request.page.page_name

    row = 0
    divfmt = { 'class': "metatable" }

    formatopts = {'tableclass': 'metatable' }

    # Limit the maximum number of pages displayed
    pagepathstrip = options.get('pathstrip', 0)
    try:
        pagepathstrip = int(pagepathstrip)
    except ValueError:
        pagepathstrip = 0
        pass
    if pagepathstrip < 0:
        pagepathstrip = 0

    # To include only a [link] to page instead of pagename
    pagelinkonly = options.get('pagelinkonly', 0)
    # Transpose table, i.e. make table lanscape instead of portrait
    transpose = options.get('transpose', 0)

    # Default and override properties
    propdefault = options.get('propdefault', '')
    propoverride = options.get('propoverride', '')
    if propoverride:
        propoverride = get_properties(request, propoverride)
    if propdefault:
        propdefault = get_properties(request, propdefault)

    # Limit the maximum number of pages displayed
    maxpages = len(pagelist)
    limit = options.get('limit', 0)
    try:
        limit = int(limit)
    except ValueError:
        limit = 0
        pass
    if limit > maxpages or limit < 0:
        limit = 0
    if limit:
        pagelist = pagelist[:limit]

    if 'width' in options:
        formatopts = {'tableclass': 'metatable wrap'}
        formatopts['tablewidth'] = options['width']

    # Start table
    out = formatter.linebreak() + \
        formatter.div(1, **divfmt).replace('div', 'div data-options="'
                                           +quote(json.dumps(options))+'"') + \
        formatter.table(1, attrs=formatopts)

    # If the first column is -, do not send page data
    send_pages = True
    if metakeys and metakeys[0] == '-':
        send_pages = False
        metakeys = metakeys[1:]

    if metakeys:
        # Give a class to headers to make it customisable
        out += formatter.table_row(1, {'rowclass': 'meta_header'})
        if send_pages:
            # Upper left cell contains table size or has the desired legend
            if legend:
                out += t_cell(request, pagename, [legend])
            elif limit:
                message = ["Showing (%s/%s) pages" % 
                           (len(pagelist), maxpages)]
                    
                out += t_cell(request, pagename, message)
            else:
                out += t_cell(request, pagename, [legend])


    def key_cell(out, request, metas, key, page, 
                 styles, propoverride, propdefault):
        style = styles.get(key, dict())

        if key == 'gwikipagename':
            out += t_cell(request, page, [page], head=1, style=style)
        else:
            if propoverride:
                properties = propoverride
            else:
                properties = get_properties(request, key)
            if properties == emptyprop:
                properties = propdefault

            colors = [x.strip() for x in properties 
                      if x.startswith('color')]
            colormatch = None
            # Get first color match
            for color in colors:
                colorval = properties.get(color)
                # See that color is valid (either in the colorlist
                # or a valid hex color)
                if not colorval in COLORS:
                    if not re.match('#[0-9a-f]{6}', colorval):
                        continue
                color = color.split()[-1]

                try:
                    color_p = re.compile(color)
                except:
                    continue
                for val in metas[key]:
                    if color_p.match(val):
                        colormatch = colorval
                if colormatch:
                    break
            if colormatch:
                style['bgcolor'] = colormatch

            out += t_cell(request, page, metas[key], style=style, key=key)

            if colormatch:
                del style['bgcolor']

            return out

    def page_rev_metas(request, page, metakeys, checkAccess):
        if '-gwikirevision-' in page:
            metas = get_metas(request, page, metakeys, 
                              checkAccess=checkAccess)
            page, revision = page.split('-gwikirevision-')
        else:
            metas = get_metas(request, page, metakeys, 
                              checkAccess=checkAccess)
            revision = ''

        return metas, page, revision

    def page_cell(out, request, page, revision, row, send_pages, 
                  pagelinkonly, pagepathstrip):

        pageobj = Page(request, page)
        request.page = pageobj
        request.formatter.page = pageobj

        if row:
            if row % 2:
                out += formatter.table_row(1, {'rowclass': 
                                               'metatable-odd-row'})

            else:
                out += formatter.table_row(1, {'rowclass': 
                                               'metatable-even-row'})

        if send_pages:
            linktext = ''
            if pagelinkonly:
                linktext = _('[link]')
            out += t_cell(request, page, [page], head=1, rev=revision, 
                          pathstrip=pagepathstrip, linkoverride=linktext)

        return out

    if transpose:
        for page in pagelist:
            metas, page, revision = page_rev_metas(request, page, 
                                                   metakeys, checkAccess)

            out = page_cell(out, request, page, revision, 0, send_pages, 
                            pagelinkonly, pagepathstrip)
    else:
        for key in metakeys:
            style = styles.get(key, dict())

            # Styles can modify key naming
            name = style.get('gwikiname', '').strip('"')

            if not name and legend and key == 'gwikipagename':
                name = [legend]

            # We don't want stuff like bullet lists in out header
            headerstyle = dict()
            for st in style:
                if not st.startswith('gwiki'):
                    headerstyle[st] = style[st]

            if name:
                out +=t_cell(request, pagename, [name], 
                             style=headerstyle, key=key)
            else:
                out += t_cell(request, pagename, [key], 
                              style=headerstyle, key=key)

    if metakeys:
        out += formatter.table_row(0)

    tmp_page = request.page

    if transpose:
        emptyprop = dict().fromkeys(PROPERTIES, '')
        for key in metakeys:
            style = styles.get(key, dict())

            # Styles can modify key naming
            name = style.get('gwikiname', '').strip('"')

            if not name and legend and key == 'gwikipagename':
                name = [legend]

            # We don't want stuff like bullet lists in out header
            headerstyle = dict()
            for st in style:
                if not st.startswith('gwiki'):
                    headerstyle[st] = style[st]

            if name:
                out +=t_cell(request, pagename, [name], 
                             style=headerstyle, key=key)
            else:
                out +=t_cell(request, pagename, [key], 
                             style=headerstyle, key=key)

            row = row + 1

            for page in pagelist:
                metas, page, revision = page_rev_metas(request, page, 
                                                       metakeys, checkAccess)
                out = key_cell(out, request, metas, key, page, 
                               styles, propoverride, propdefault)

            out += formatter.table_row(0)
    else:
        for page in pagelist:
            metas, page, revision = page_rev_metas(request, page, 
                                                   metakeys, checkAccess)

            row = row + 1

            out = page_cell(out, request, page, revision, row, send_pages, 
                            pagelinkonly, pagepathstrip)

            emptyprop = dict().fromkeys(PROPERTIES, '')
            for key in metakeys:
                out = key_cell(out, request, metas, key, page, 
                               styles, propoverride, propdefault)

            out += formatter.table_row(0)

    request.page = tmp_page
    request.formatter.page = tmp_page

    out += formatter.table(0)
    out += formatter.div(0)
    return out

def do_macro(request, args, **kw):
    formatter = request.formatter
    _ = request.getText
    out = str()
    pagename = request.page.page_name

    # Note, metatable_parseargs deals with permissions
    pagelist, metakeys, styles = metatable_parseargs(request, args,
                                                     get_all_keys=True)

   # No data -> bail out quickly, Scotty
    if not pagelist:
        out += formatter.linebreak() + u'<div class="metatable">' + \
            formatter.table(1)
        if kw.get('silent'):
            out += t_cell(request, pagename, ["%s" % _("No matches")])
        else:
            out += t_cell(request, pagename, 
                          ["%s '%s'" % (_("No matches for"), args)])
        out += formatter.table(0) + u'</div>'
        return out


    # We're sure the user has the access to the page, so don't check
    out += construct_table(request, pagelist, metakeys,
                          checkAccess=False, styles=styles,
                          options=dict({'args': args}.items() + kw.items()))

    def action_link(action, linktext, args):
        req_url = request.getScriptname() + \
                  '/' + url_escape(request.page.page_name) + \
                  '?action=' + action + '&args=' + url_escape(args)
        return '<a href="%s" id="footer">[%s]</a>\n' % \
               (request.getQualifiedURL(req_url), _(linktext))

    # If the user has no write access to this page, omit editlink
    if kw.get('editlink', True):
        out += action_link('MetaEdit', 'edit', args)

    out += action_link('metaCSV', 'csv', args)
    out += action_link('metaPackage', 'zip', args)

    return out

def execute(macro, args):
    request = macro.request

    if args is None:
        args = ''

    optargs = {}

    #parse keyworded arguments (template etc)
    opts = re.findall("(?:^|,)\s*([^,|]+)\s*:=\s*([^,]+)\s*", args)
    args = re.sub("(?:^|,)\s*[^,|]+:=[^,]+\s*", "", args)
    for opt in opts:
        val = opt[1]
        if val == "True":
            val = True
        elif val == "False":
            val = False

        optargs[str(opt[0])] = val

    # loathful positional stripping (requires specific order of args), sorry
    if args.strip().endswith('gwikisilent'):
        optargs['silent'] = True
        args = ','.join(args.split(',')[:-1])

    if args.strip().endswith('noeditlink'):
        optargs['editlink'] = False
        args = ','.join(args.split(',')[:-1])

    return do_macro(request, args, **optargs)
