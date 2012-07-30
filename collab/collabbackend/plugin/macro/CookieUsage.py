import re
import StringIO
import spanner

from urllib import unquote as url_unquote
from urllib import quote as url_quote

from MoinMoin import config
from MoinMoin.parser.text_moin_wiki import Parser
from MoinMoin.Page import Page

from graphingwiki.editing import metatable_parseargs, get_metas

Dependencies = ['metadata']

def timeToString(x):
    return "<<DateTime(%d)>>" % x

def stringToTime(x):
    result = re.match("\<\<DateTime\(([0-9]+)\)\>\>", x)
    if result:
        return int(result.group(1))

    return 0

def t_cell(macro, value, head=0):
    out = macro.request

    style = dict()
    style['class'] = 'meta_cell'

    out.write(macro.formatter.table_cell(1, attrs=style))

    if not isinstance(value, unicode):
        value = unicode(value, config.charset)

    value = value.strip()

    if head:
        kw = {}
        if '?' in value:
            value, query = value.split('?')
            kw['querystr'] = query
        out.write(macro.formatter.pagelink(1, value, **kw))
        out.write(macro.formatter.text(value))
        out.write(macro.formatter.pagelink(0))
    else:
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

def construct_table(macro, pagelist, metakeys, 
                    legend='', checkAccess=True, styles={}):
    request = macro.request
    request.page.formatter = request.formatter

    days = dict()
    times = dict()

    orginalPage = request.page

    for page in pagelist:
        pageobj = Page(request, url_unquote(page))
        request.page = pageobj
        request.formatter.page = pageobj

        metas = get_metas(request, page,
                          metakeys, checkAccess=checkAccess)

        spans = days.setdefault(page, spanner.Spanner())
        count = times.get(page, 0)

        for key in metakeys:
            values = metas[key]
            key = url_unquote(key)
            style = styles.get(key, {})
            for value in values:
                value = value.strip().split()
                if len(value) != 2:
                    continue

                start, end = value
                start = stringToTime(start)
                end = stringToTime(end)
                if not (start and end):
                    continue

                count += 1
                spans.addSpan(start, end)

        times[page] = count


    request.write(macro.formatter.linebreak() +
                  u'<div class="metatable">' +
                  macro.formatter.table(1))
    request.write(macro.formatter.table_row(1, {'rowclass':
                                                'meta_header'}))
    t_cell(macro, "User")
    t_cell(macro, "Used (days)")
    t_cell(macro, "Used (times)")
    request.write(macro.formatter.table_row(0))

    tmp = list()

    for key in days:
        value = days[key]
        total = sum(map(lambda (start, end): end-start, value))
        total /= float(60*60*24)

        count = times.get(key, 0)

        if count == 0:
            continue

        tmp.append((total, count, key))

    tmp.sort(reverse=True)

    row = 0
    for (days, times, user) in tmp:
        row = row + 1

        if row % 2:
            request.write(macro.formatter.table_row(1, {'rowclass':
                                                        'metatable-odd-row'}))
        else:
            request.write(macro.formatter.table_row(1, {'rowclass':
                                                        'metatable-even-row'}))
        t_cell(macro, url_unquote(user), head=1)
        t_cell(macro, u"%.02f" % days)
        t_cell(macro, u"%d" % times)
        request.write(macro.formatter.table_row(0))


    request.page = orginalPage 
    request.formatter.page = orginalPage 

    request.write(macro.formatter.table(0))
    request.write(u'</div>')

def execute(macro, args):
    if args is None:
        args = ''

    # Note, metatable_parseargs deals with permissions
    pagelist, metakeys, styles = \
                metatable_parseargs(macro.request, args,
                                    get_all_keys=True)

    request = macro.request
    _ = request.getText

    # No data -> bail out quickly, Scotty
    if not pagelist:
        request.write(macro.formatter.linebreak() +
                      u'<div class="metatable">' +
                      macro.formatter.table(1))
        t_cell(macro, "%s (%s)" % (_("Metatable has no contents"), args))
        request.write(macro.formatter.table(0) + 
                      u'</div>')

        return ""

    # We're sure the user has the access to the page, so don't check
    construct_table(macro, pagelist, metakeys,
                    checkAccess=False, styles=styles)

    return ""
