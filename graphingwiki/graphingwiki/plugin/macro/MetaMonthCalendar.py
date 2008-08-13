# -*- coding: utf-8 -*-"
"""
    FIXME DOCUMENT!

    @copyright: 2008 by therauli <therauli@ee.oulu.fi>
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
import calendar, datetime, time


from urllib import unquote as url_unquote
from urllib import quote as url_quote

from MoinMoin.Page import Page
from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.parser.text_moin_wiki import Parser


from graphingwiki.editing import metatable_parseargs, getmetas
from graphingwiki.editing import formatting_rules
from graphingwiki.patterns import encode

Dependencies = ['metadata', 'time']

def execute(macro, args):
    if args is None:
        args = ''
    pageTemplate = args.split(',')[-1].strip()
    if pageTemplate:
        args = ','.join(args.split(',')[:-1])

    # Note, metatable_parseargs deals with permissions
    globaldata, pagelist, metakeys, styles = metatable_parseargs(macro.request, args, get_all_keys=True)
    request = macro.request
    _ = request.getText

    out = macro.request

    entries = dict()

    for page in pagelist:
        metas = getmetas(request, globaldata, page, metakeys, display=False, checkAccess=True)
        if u'Date' not in metas.keys():
            continue
        #FIXME stoptime
        if metas[u'Date']:
            date = metas[u'Date'][0][0]
            datedata = entries.setdefault(date, list())
            entrycontent = dict()
            content = Page(request, page).get_raw_body()
            if '----' in content:
                content = content.split('----')[0]
            entrycontent['content'] = content
            for meta in metas:
                entrycontent[meta] = metas[meta][0][0]
            datedata.append(entrycontent)


    print entries

    globaldata.closedb()

    now = datetime.datetime.today()
    year = now.year
    month = now.month
    cal = calendar.monthcalendar(year, month)

    output = ""
    output += macro.formatter.table(1)

    categories = [x.strip() for x in args.split(',') if 'Category' in x]
    categories = ','.join(categories)

    cssClass = dict()

    for week in cal:
        output += macro.formatter.table_row(1)
        for day in week:
            output += macro.formatter.table_cell(1)
            timestamp =u'%04d-%02d-%02d' % (year, month, day)
            if day:
                urldict = dict(date = timestamp, backto = macro.request.page.page_name, categories = categories)
                url = macro.request.getQualifiedURL() + '/' + '?action=showCalendarDate&date=%(date)s&backto=%(backto)s&categories=%(categories)s' % urldict
                output += macro.formatter.url(1, url, u'metamonthcalendar_noentry_url')
                output += macro.formatter.text(u'%d' % day)
                output += macro.formatter.url(0)
            output += macro.formatter.table_cell(0)
        output += macro.formatter.table_row(1)
    output += macro.formatter.table_row(0)
    output += macro.formatter.table(0)


    return output

def makeCalendar():
    pass

