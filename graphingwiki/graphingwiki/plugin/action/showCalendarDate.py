import datetime

from MoinMoin.Page import Page
from MoinMoin import wikiutil
from MoinMoin.parser.text_moin_wiki import Parser

from graphingwiki.editing import metatable_parseargs, getmetas

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
    request.write('<a href="%s?action=edit&backto=%s">Add entry</a>' % (date, pagename))

      
def printEvents(events, date, pagename, request):

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

    for event in events:
        request.write('<tr>')
        startTime = datetime.datetime.strptime(event['Date'][0][0] + ' ' + event['Time'][0][0], '%Y-%m-%d %H:%M')
        hours = int(event['Duration'][0][0].split(':')[0])
        minutes = int(event['Duration'][0][0].split(':')[1])
        endTime = startTime + datetime.timedelta(hours = hours, minutes = minutes)
        writeCell(startTime.strftime('%H:%M - ') + endTime.strftime('%H:%M'))
        
        #Parser('== foo ==', request).format(request.formatter)
        writeCell(request.formatter.text(event['Content']), width="50%")

        writeCell('<a href="%s?action=edit&backto=%s">edit</a>' % (event['Page'], backto)) #request.request_uri[1:]))
        writeCell('<a href="%s?action=DeletePage">remove</a>' % event['Page'])
        
        request.write('</tr>')
        
    request.write('</table>')


def execute(pagename, request):
    request.http_headers()
    
    #_enter_page(request, pagename)

    date = request.form.get('date', [None])[0]
                  
    categories = request.form.get('categories', [None])
                  
    categories = ','.join(categories)
    
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, 'Date=%s,%s' % (date, categories), get_all_keys=True)

    globaldata.closedb()

    if not pagelist:
        request.write('No Entries')
        addEntry(pagename, date, request)
        return

    events = list()

    for page in pagelist:
        metas = getmetas(request, globaldata, page, metakeys, display=False, checkAccess=True)
        content = Page(request, page).get_raw_body()
        if '----' in content:
            content = content.split('----')[0]
        metas['Page'] = page
        metas['Content'] = content
        events.append(metas)

    events.sort(key = lambda x: x['Time'])

    printEvents(events, date, pagename, request)
    
    addEntry(pagename, date, request)

    #_exit_page(request, pagename)
    
