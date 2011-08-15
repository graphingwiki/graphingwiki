import urllib

from time import strftime, strptime, time, gmtime
from calendar import timegm
from xml.dom.minidom import Document

from MoinMoin.Page import Page
from MoinMoin import config

from graphingwiki.editing import metatable_parseargs, get_metas
from graphingwiki.util import format_wikitext

time_format = "%b %d %Y %H:%M:%S +0000"

datetime_format = "<<DateTime(%Y-%m-%dT%H:%M:%S)>>"

# A method for 
def timestamp(text):
    # First, try another time format
    try:
        return strftime(time_format, 
                        strptime(text.split('.')[0], "%Y%m%d %H:%M:%S"))
    except ValueError:
        try:
            return strftime(datetime_format, 
                            strptime(text.split('.')[0], "%Y%m%d %H:%M:%S"))
        except:
            pass
    
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

def check_time(time):
    if not time:
        return None

    time = time[0]

    try:
        start_time = timestamp(time)
    except ValueError:
        return None

    return start_time

def execute(pagename, request):
    _ = request.getText

    form = request.values.to_dict(flat=False)

    args = ', '.join(x for x in form.get('arg', list()))

    request.content_type = "application/xml;charset=%s" % config.charset

    doc = Document()
    data = doc.createElement('data')
    doc.appendChild(data)

    # Note, metatable_parseargs deals with permissions
    pagelist, metakeys, _ = metatable_parseargs(request, args,
                                                get_all_keys=True)

    for page in pagelist:
        metas = get_metas(request, page, metakeys, checkAccess=False)

        timekey = metakeys[0]
        time = metas.get(timekey, list())

        start_time = check_time(time)

        if start_time is None:
            continue

        keys_rest = metakeys[1:]

        # Opportunistically try to parse end_time
        end_time = None
        if len(metas) > 1:
            timekey = keys_rest[0]
            time = metas.get(timekey, list())

            end_time = check_time(time)

        new_page = Page(request, page)

        page_link = new_page.url(request)

        event = doc.createElement('event')
        event.setAttribute('link', page_link)
        event.setAttribute('title', page)
        event.setAttribute('start', start_time)
        if end_time:
            event.setAttribute('end', end_time)
            keys_rest = keys_rest[1:]
        data.appendChild(event)

        comment = str()
        for key in keys_rest:
            for val in metas.get(key, list()):
                comment += format_wikitext(request, ' %s:: %s\n' % (key, val))

        ptext = doc.createTextNode(comment)
        event.appendChild(ptext)

    request.write(doc.toprettyxml(indent='  '))
