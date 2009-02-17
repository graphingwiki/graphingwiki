# -*- coding: utf-8 -*-

import datetime, time

from MoinMoin.Page import Page
from MoinMoin import wikiutil
from MoinMoin.parser.text_moin_wiki import Parser

from graphingwiki.editing import metatable_parseargs
from graphingwiki.editing import get_metas

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
    request.write('<br><a href="?action=editCalendarEntry&date=%s&categories=%s">Add entry</a>' % (date, request.form.get('categories',[u''])[0].encode()))

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
      
def printEntries(entries, date, pagename, request):

    def writeCell(stuff, width=''):
        if width:
            request.write('<td width="%s">' % width)
        else:
            request.write('<td>')
        request.write(stuff)
        request.write('</td>')
    
    request.write(u'''<script type="text/javascript"
    src="%s/raippajs/mootools-1.2-core-yc.js"></script>
    <script type="text/javascript">
    function toggle(el){
        var part_list = $(el).getParent('p').getNext('div');
        part_list.toggleClass('hidden');
        if(el.text == "hide"){
            el.set('text', 'show');
        }else{
            el.set('text', 'hide');    
        }
    }
    </script>
    '''% request.cfg.url_prefix_static )
    request.write(u'<table id="calEventList">')
    request.write(u'''<tr><th colspan="6">%s</th></tr>
    <tr>
    <th>Time</th><th>Location</th><th>Event</th><th>Participants/Capacity</th>
    <th colspan="2"></th>
    </tr>
    ''' % date)

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
                capacity = entry['Capacity']
            else:
                capacity = '?'

            participants = entry['Participants'] 
            if len(participants) > 0:
               participant_list = "<br>".join(participants)
               participant_div = '''<p><span style="float:left;">%s /
               <b>%s</b></span><span style="float:right;margin-left:5px;"><a class="jslink" 
               onclick="toggle(this);">show</a></span><br
               clear="all"></p><div class="hidden">%s</div>
               ''' % (len(participants), capacity, participant_list)
            else:
                participant_div = "0 / <b>%s</b>" % capacity

            writeCell(participant_div)

            #edit link
            writeCell('<a href="?action=editCalendarEntry&edit=%s&categories=%s">edit</a>' % (entry['Page'], request.form.get('categories',[u''])[0].encode()))
            #remove link
            writeCell('<a href="%s?action=DeletePage">remove</a>' % entry['Page'])

            request.write('</tr>')
        
    request.write('</table>')


def execute(pagename, request):

    
    _enter_page(request, pagename)

    thisdate = request.form.get('date', [None])[0]

    categories = request.form.get('categories', [None])
    categories = ','.join(categories)

    
    pagelist, metakeys, styles = metatable_parseargs(request, categories, get_all_keys=True)

    entries = dict()

    for page in pagelist:
        metas = get_metas(request, page, metakeys, display=False, checkAccess=True)

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

            participants, capacity = getParticipants(request, page)
            if participants:
                for i, p in enumerate(participants):
                    participants[i] = '<a href="%s">%s</a>' % (p,p)

            entrycontent['Participants'] = participants

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
    
    addEntry(pagename, thisdate, request)

    _exit_page(request, pagename)
    
