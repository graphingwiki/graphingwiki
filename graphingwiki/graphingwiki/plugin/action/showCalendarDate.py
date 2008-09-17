# -*- coding: utf-8 -*-

import datetime, time

from MoinMoin.Page import Page
from MoinMoin import wikiutil
from MoinMoin.parser.text_moin_wiki import Parser

from graphingwiki.editing import metatable_parseargs, getmetas
from graphingwiki.patterns import getgraphdata

def _enter_page(request, pagename):
    _ = request.getText
	   
    title = _('Calendar')

    request.theme.send_title(title,
                             pagename=pagename)

    # Start content - IMPORTANT - without content div, there is no
    # direction support!

    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    
    request.page.formatter = formatter

    request.write(request.page.formatter.startContent("content"))
    
def _exit_page(request, pagename):
    # End content
    request.write(request.page.formatter.endContent()) # end content div
    # Footer
    request.theme.send_footer(pagename)

def addEntry(pagename, date, request):
    backto = request.form.get('backto', [None])[0].encode()
    request.write('<br><a href="?action=editCalendarEntry&date=%s&backto=%s&categories=%s">Add entry</a>' % (date,
    backto, request.form.get('categories',[u''])[0].encode()))

      
def printEntries(entries, date, pagename, request):

    def writeCell(stuff, width=''):
        if width:
            request.write('<td width="%s">' % width)
        else:
            request.write('<td>')
        request.write(stuff)
        request.write('</td>')

    backto = request.form.get('backto', [None])[0].encode()


    request.write(u'<table>')
    request.write(u'<th colspan=4>%s</th>' % date)

    for day in entries:
        if day != date:
            continue

        for entry in entries[day]:

            request.write('<tr>')
            startTime = None

            if 'Time' in entry:
                startTime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(entry['Date'] + ' ' + entry['Time'], '%Y-%m-%d %H:%M')))
            endTime = None
            if 'Duration' in entry:
                hours = int(entry['Duration'].split(':')[0])
                minutes = int(entry['Duration'].split(':')[1])
                endTime = startTime + datetime.timedelta(hours = hours, minutes = minutes)
            if startTime and endTime:
                writeCell(startTime.strftime('%H:%M') + endTime.strftime(' - %H:%M'))
            elif startTime:
                writeCell(startTime.strftime('%H:%M'))
            else:
                writeCell('?')
            if 'Location' in entry:
                writeCell(entry['Location'])
            else:
                writeCell('?')

            writeCell(request.formatter.text(entry['Content'], width="40%"))

            if 'Capacity' in entry:
                writeCell(entry['Capacity'])
            else:
                writeCell('?')
            #edit link
            writeCell('<a href="?action=editCalendarEntry&edit=%s&backto=%s&categories=%s">edit</a>' % (entry['Page'],
            backto, request.form.get('categories',[u''])[0].encode())) #request.request_uri[1:]))
            #remove link
            writeCell('<a href="%s?action=DeletePage">remove</a>' % entry['Page'])

            request.write('</tr>')
        
    request.write('</table>')


def execute(pagename, request):

    request.http_headers()
    
    _enter_page(request, pagename)

    thisdate = request.form.get('date', [None])[0]

    categories = request.form.get('categories', [None])
    categories = ','.join(categories)

    
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, categories, get_all_keys=True)

    entries = dict()

    if not hasattr(request, 'graphdata'):
        getgraphdata(request)

    for page in pagelist:
        metas = getmetas(request, request.graphdata, page, metakeys, display=False, checkAccess=True)

        if u'Date' not in metas.keys():
            continue

        if metas[u'Date']:
            date = metas[u'Date'][0][0]
            datedata = entries.setdefault(date, list())
            entrycontent = dict()
            content = Page(request, page).get_raw_body()
            if '----' in content:
                content = content.split('----')[0]
            entrycontent['Content'] = content

            entrycontent['Page'] = page

            for meta in metas:
                if not metas[meta]:
                    continue
                entrycontent[meta] = metas[meta][0][0]
            datedata.append(entrycontent)


    #Getting current month
    now = datetime.datetime.fromtimestamp(time.mktime(time.strptime(thisdate, '%Y-%m-%d')))
    now = now.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    year = now.year
    month = now.month

    try:
        end_date = now.replace(month = month + 1, day = 1)
    except ValueError:
        end_date = now.replace(month = 1, year = year + 1)


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

            while curdate <= end_date:
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

    if 'Time' in entries:
        entries.sort(key = lambda x: x['Time'])

    printEntries(entries, thisdate, pagename, request)
    
    addEntry(pagename, thisdate, request)

    _exit_page(request, pagename)
    
