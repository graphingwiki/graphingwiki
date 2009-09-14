# -*- coding: utf-8 -*-

import datetime, time

from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin import wikiutil

from graphingwiki.editing import metatable_parseargs
from graphingwiki.editing import get_metas

def _enter_page(request, pagename):
    _ = request.getText
	   
    title = _('Calendar')

    request.emit_http_headers()
    request.theme.send_title(title, pagename=pagename)

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

def getParticipants(request, eventpage):
    meta = get_metas(request, eventpage, ["Capacity"], checkAccess=False)

    if meta["Capacity"]:
        capacity = int(meta["Capacity"][0])
    else:
        capacity = 0

    grouppage = "%s/EventGroup" % eventpage
    eventgroup = Page(request, grouppage)
    if eventgroup.exists():
        participants = list()
        raw = eventgroup.getPageText()
        for line in raw.split("\n"):
            if line.startswith(" * "):
                participants.append(line[3:].rstrip())
        return participants, capacity
    else:
        return [], capacity

def signupEvent(request, eventpage):
    _ = request.getText
    participants, capacity = getParticipants(request, eventpage)
    if (not capacity or len(participants) < capacity) and not request.user.name in participants:
        grouppage = "%s/EventGroup" % eventpage
        eventgroup = PageEditor(request, grouppage)
        pagecontent = eventgroup.getPageText() + u'\n * %s' % request.user.name
        msg = eventgroup.saveText(pagecontent, eventgroup.get_real_rev())
        if msg == _(u'Thank you for your changes. Your attention to detail is appreciated.'):
            return True
        else:
            return False
    return False

def leaveEvent(request, eventpage):
    _ = request.getText
    participants, capacity = getParticipants(request, eventpage)
    if request.user.name in participants:
        grouppage = "%s/EventGroup" % eventpage
        eventgroup = PageEditor(request, grouppage)
        if not eventgroup.exists():
            return True
        rawlines = eventgroup.getPageText().split("\n")
        for index, line in enumerate(rawlines):
            if line.rstrip() == u' * %s' % request.user.name:
                rawlines.pop(index)
                break
        if not "\n".join(rawlines).rstrip():
            msg = eventgroup.deletePage()
            return True
        pagecontent = "\n".join(rawlines)
        msg = eventgroup.saveText(pagecontent, eventgroup.get_real_rev())
        if msg == _(u'Thank you for your changes. Your attention to detail is appreciated.'):
            return True
        else:
            return False
    else:
        return True

def printEntries(entries, date, pagename, request):

    def writeCell(stuff, width=''):
        if width:
            request.write('<td width="%s">' % width)
        else:
            request.write('<td>')
        request.write(stuff)
        request.write('</td>')


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

            participants, capacity = getParticipants(request, entry['Page'])

            if 'Capacity' in entry:
                writeCell('%s/%s' % (len(participants), capacity))
            else:
                writeCell('?')

            categories = request.form.get('categories', [''])
            categoryhtml = u'&'
            for category in categories:
                categoryhtml += u'categories=%s' % category

            #select/unselect link
            if request.user.name in participants:
                writeCell('<a href="?action=selectCalendarEvent&leave=%s&date=%s%s">Unregister</a>' % (entry['Page'], entry['Date'], categoryhtml))
            else:
                if len(participants) >= capacity:
                    writeCell('Full')
                else:
                    writeCell('<a href="?action=selectCalendarEvent&signup=%s&date=%s%s">Signup</a>' % (entry['Page'], entry['Date'], categoryhtml))

            request.write('</tr>')
        
    request.write('</table>')


def execute(pagename, request):
    if not request.user.name:
        _enter_page(request, pagename)
        request.write(u'<a href="?action=login">Login</a> or <a href="UserPreferences">create user account</a>.')
        _exit_page(request, pagename)
        return None

    thisdate = request.form.get('date', [None])[0]
    categories = request.form.get('categories', [None])
    categories = ','.join(categories)

    if request.form.has_key("signup"):
        eventpage = request.form.get('signup', [u''])[0]
        if signupEvent(request, eventpage):
            categories = request.form.get('categories', [''])
            categoryhtml = u'&'
            for category in categories:
                categoryhtml += u'categories=%s' % category
            url = u'%s/%s?action=selectCalendarEvent&date=%s%s' % (
                    request.getBaseURL(), pagename, thisdate, categoryhtml)
            request.http_redirect(url)
        else:
            _enter_page(request, pagename)
            request.write(u'Sign up failed.')
            _exit_page(request, pagename)
            
    elif request.form.has_key("leave"):
        eventpage = request.form.get('leave', [None])[0]
        if leaveEvent(request, eventpage):
            categories = request.form.get('categories', [''])
            categoryhtml = u'&'
            for category in categories:                      
                categoryhtml += u'categories=%s' % category  
            url = u'%s/%s?action=selectCalendarEvent&date=%s%s' % (
                    request.getBaseURL(), pagename, thisdate, categoryhtml)
            request.http_redirect(url)
        else:
            _enter_page(request, pagename)
            request.write(u'Unregisteration failed.')
            _exit_page(request, pagename)

    else:
        _enter_page(request, pagename)
        pages, keys, s = metatable_parseargs(request, categories, get_all_keys=True, checkAccess=False)

        entries = dict()
        for page in pages:
            metas = get_metas(request, page, keys, display=False, checkAccess=False)

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

                entrycontent['Page'] = page

                for meta in metas:
                    if not metas[meta]:
                        continue
                    entrycontent[meta] = metas[meta][0]
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
    
        _exit_page(request, pagename)
