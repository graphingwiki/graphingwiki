import urllib

from time import strftime, strptime, time, gmtime
from calendar import timegm
from xml.dom.minidom import Document

from MoinMoin.Page import Page
from MoinMoin import config
from MoinMoin.util import MoinMoinNoFooter

from graphingwiki.editing import metatable_parseargs, get_metas
from graphingwiki.patterns import format_wikitext

time_format = "%b %d %Y %H:%M:%S +0000"

# A method for 
def timestamp(text):
    format = "%b %d %Y %H:%M:%S"

    tz = text.split()[-1]

    add_to_hours = 0
    if tz[0] in ['-', '+']:
        text = ' '.join(text.split()[:-1])

        time_delta = tz[1:].rstrip('0')

        if time_delta:
            add_to_hours = int(tz[1:].rstrip('0')) * 3600
            
            if tz[0] == '-':
                add_to_hours = -add_to_hours


    return strftime(time_format, gmtime(timegm(strptime(text, format)) + 
                                         add_to_hours))

def execute(pagename, request):
    _ = request.getText

    args = ', '.join(x for x in request.form.get('arg', list()))

    request.http_headers(["Content-type: application/xml;charset=%s" %
                          config.charset])

    doc = Document()
    data = doc.createElement('data')
    doc.appendChild(data)

    # Note, metatable_parseargs deals with permissions
    pagelist, metakeys, _ = metatable_parseargs(request, args,
                                                get_all_keys=True)

    for page in pagelist:
        metas = get_metas(request, page, metakeys, checkAccess=False)

        timekey = metakeys[0]
        #request.write(repr(page))
        #request.write(repr(metas))
        #request.write(repr(timekey))
        #request.write(repr(metas.get(timekey, list())))
        #request.write('\n')

        time = metas.get(timekey, list())
        if not time:
            continue

        time = time[0]

        try:
            start_time = timestamp(time)
        except ValueError:
            request.write('problem')
            continue

        new_page = Page(request, page)

        page_link = new_page.url(request)

        event = doc.createElement('event')
        event.setAttribute('link', page_link)
        event.setAttribute('title', page)
        event.setAttribute('start', start_time)
        data.appendChild(event)

        comment = str()
        for key in metakeys[1:]:
            for val in metas.get(key, list()):
                comment += format_wikitext(request, ' %s:: %s\n' % (key, val))

        ptext = doc.createTextNode(comment)
        event.appendChild(ptext)

    request.write(doc.toprettyxml(indent='  '))

    raise MoinMoinNoFooter
