# -*- coding: utf-8 -*-
"""
    recentchangestimeline action
     - generates data needed by SIMILE timeline visualisation

    @copyright: 2008-2009 by Juhani Eronen <exec@iki.fi>
     somewhat based on the MoinMoin RecentChanges macro 
     by Juergen Hermann <jh@web.de>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
import urllib

from time import strftime, time
from xml.dom.minidom import Document

from MoinMoin import config
from MoinMoin.util import rangelist
from MoinMoin.logfile import editlog
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.macro.RecentChanges import format_comment, _MAX_DAYS

def format_entries(request, lines, doc, data):
    line = lines[0]
    is_new = line.action == 'SAVENEW'

    page = Page(request, line.pagename)
    page_link = page.url(request)

    infoimg = request.theme.make_icon('info')
    infolink = wikiutil.link_tag(request, 
                                 wikiutil.quoteWikinameURL(line.pagename) +
                                 "?action=info",
                                 infoimg)

    html_link = ""
    revision = ""
    if line.rev != '99999999':
        if not page.exists():
            # indicate page was deleted
            html_link = request.theme.make_icon('deleted')
        elif is_new:
            img = request.theme.make_icon('new')
            html_link = wikiutil.link_tag(request,
                                          wikiutil.quoteWikinameURL(line.pagename),
                                          img)
        else:
            img = request.theme.make_icon('diffrc')
            html_link = wikiutil.link_tag(request,
                                          wikiutil.quoteWikinameURL(line.pagename) +
                                          "?action=diff",
                                          img)

        revision = "rev %s" % (line.rev.lstrip('0'))

    user = line.getInterwikiEditorData(request)
    if user[0] == 'interwiki':
        user = ' '.join(user[1])
    else:
        user = user[1]

    # print editor name or IP
    editors = []
    if request.cfg.show_names:
        if len(lines) > 1:
            counters = {}
            for idx in range(len(lines)):
                name = lines[idx].getEditor(request)
                if not name in counters:
                    counters[name] = []
                counters[name].append(idx+1)
            poslist = map(None,  counters.values(), counters.keys())
            poslist.sort()
            ##request.write(repr(counters.items()))
            for positions, name in poslist:
                editors.append("%s [%s]" % (
                    name, rangelist(positions)))
        else:
            editors = [line.getEditor(request)]

    comments = []
    for idx in range(len(lines)):
        comment = format_comment(request, lines[idx])
        if comment:
            comments.append("%s %s" % (idx+1, wikiutil.escape(comment)))

    times = [x.time_tuple for x in lines]

    start_time = strftime("%b %d %Y %H:%M:%S %z", times[-1])
    end_time = ''
    if len(times) > 1:
        end_time = strftime("%b %d %Y %H:%M:%S %z", times[0])

    comment = " ".join((html_link,
                        page.link_to(request),
                        revision,
                        infolink,
                        ' '.join(editors),
                        ' '.join(comments)
                        ))

    event = doc.createElement('event')
    event.setAttribute('link', page_link)
    event.setAttribute('title', line.pagename)
    event.setAttribute('start', start_time)
    data.appendChild(event)
    if end_time:
        event.setAttribute('end', end_time)
    ptext = doc.createTextNode(comment)
    event.appendChild(ptext)

def execute(pagename, request):
    _ = request.getText
    log = editlog.EditLog(request)

    request.content_type = "application/xml;charset=%s" % config.charset

    doc = Document()
    data = doc.createElement('data')
    doc.appendChild(data)

    today = request.user.getTime(time())[0:3]
    this_day = today
    day_count = 0
    try:
        form = request.values.to_dict(flat=False)
        max_days = int(form.get('max_days', [_MAX_DAYS])[0])
    except ValueError:
        max_days = _MAX_DAYS

    pages = {}

    for line in log.reverse():
    
        if not request.user.may.read(line.pagename):
            continue
                    
        line.time_tuple = request.user.getTime(\
            wikiutil.version2timestamp(line.ed_time_usecs))
        day = line.time_tuple[0:3]

        if this_day != day and len(pages) > 0:
            this_day = day
            pages = pages.values()

            for page in pages:
                request.write(format_entries(request, page, doc, data))
            pages = {}

            day_count += 1
            if max_days and (day_count >= max_days):
                break

        elif this_day != day:
            this_day = day

        pages.setdefault(line.pagename, []).append(line)

    request.write(doc.toprettyxml(indent='  '))
