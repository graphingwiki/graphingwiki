# -*- coding: utf-8 -*-
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
import calendar, datetime, time


from MoinMoin.Page import Page
from graphingwiki.editing import get_metas, metatable_parseargs
import json

def to_json(data):
    try:
        dump = json.dumps(data)
    except AttributeError:
        dump = json.write(data)

    return dump

def macro_MetaMonthCalendar(macro, action, _trailing_args=[]):
    request = macro.request
    defaultaction = 'showCalendarDate'

    args = ",".join(_trailing_args)

    if not action:
        action = defaultaction

    # Note, metatable_parseargs deals with permissions
    pagelist, keys, s = metatable_parseargs(request, args, get_all_keys=True, checkAccess=True)
    entries = dict()

    for page in pagelist:
        metas = get_metas(request, page, keys, checkAccess=False)
        if u'Date' not in metas.keys():
            continue

        if metas[u'Date']:
            date = metas[u'Date'][0]
            datedata = entries.setdefault(date, list())
            entrycontent = dict()

            content = Page(request, page).getPageText()
            if '----' in content:
                content = content.split('----')[0]
            temp = list()
            for line in content.split("\n"):
                if not line.startswith("#acl"):
                    temp.append(line)
            content = "\n".join(temp)
            entrycontent['Content'] = content

            for meta in metas:
                if not metas[meta]:
                    continue
                entrycontent[meta] = metas[meta][0]
            datedata.append(entrycontent)

    #Getting current month
    now = datetime.datetime.today()
    today = now.strftime('%Y-%m-%d')
    now = now.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    year = now.year
    month = now.month
    
    last_date = now.replace(year = year + 1, day = 1)
    first_date = now.replace(day = 1, year = year -1, month = month)

    #adding reoccurring events to dict

    new_entries = dict()

    for date in entries.values():
        for entry in date:
            if not 'Type' in entry:
                continue

            type = entry['Type']

            if type == 'Once' or type == '0':
                continue

            until = None
            if 'Until' in entry:
                until = datetime.datetime.fromtimestamp(time.mktime(time.strptime(entry['Until'], '%Y-%m-%d')))
                
            #FIXME tähän niitä weekly ym

            try:
                type = int(type)
            except ValueError:
                continue
            
            curdate = datetime.datetime.fromtimestamp(time.mktime(time.strptime(entry['Date'], '%Y-%m-%d')))

            delta = datetime.timedelta(days = type)

            while curdate <= last_date:
                if until:
                    if curdate >= until:
                        break
                curdate += delta
                newdate = curdate.strftime('%Y-%m-%d')
                
                new_entries.setdefault(newdate, list())
                new_entries[newdate].append(entry)

    for entry in new_entries:
        entries.setdefault(entry, list())
        entries[entry].extend(new_entries[entry])

    categories = [x.strip() for x in args.split(',') if 'Category' in x]
    categories = ','.join(categories)

    data = {}

    for date, d in entries.iteritems():
        data[date] = []
        for i, cont in enumerate(d):
            if i == 4:
                data[date].append(u'<br><b>%s more...</b>' % (len(d) - i))
                break
            try:
                start_time = cont['Time']
            except:
                start_time = "?"

            try:
                location = '&nbsp;*&nbsp;Location:&nbsp;&nbsp;%s <br> ' % cont['Location']
            except:
                location = ""

            try:
                cap = '&nbsp;*&nbsp;Capacity:&nbsp;&nbsp;%s <br>' % cont['Capacity']
            except:
                cap = ""

            try:
                desc = cont['Content'].replace('\n','')
                if len(desc) > 35:
                    desc = desc[0:35] + " ..."
            except:
                desc = "?"

            data[date].append(u'<b>%s :</b> %s<br>%s%s' % (start_time,desc,location,cap))

    dateUrl = '?action=' +action + '&date=%Y-%m-%d&categories=' + categories
    html = u'''
    <div id="MetaMonthCalendarCont"></div>
    <script type="text/javascript" src="%s/gwikicommon/js/MetaMonthCalendar.js"></script>
    <script>
    window.addEvent('domready', function(){
        var div = document.id('MetaMonthCalendarCont').set('id','');
        var cal = new MetaMonthCalendar(div, {
            tipContent : %s,
            dateUrl : '%s'
            });
    });
    </script>
    ''' % (request.cfg.url_prefix_static, to_json(data), dateUrl)

    return html

