import urllib

from time import strftime

from MoinMoin import config
from MoinMoin.util import MoinMoinNoFooter
from MoinMoin.logfile import editlog
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.macro.RecentChanges import format_comment

def execute(pagename, request):
    _ = request.getText
    log = editlog.EditLog(request)

    request.http_headers(["Content-type: application/xml;charset=%s" %
                          config.charset])

    request.write("<data>\n")

    for line in log.reverse():

        is_new = line.action == 'SAVENEW'
    
        if not request.user.may.read(line.pagename):
            continue
                    
        line.time_tuple = request.user.getTime(wikiutil.version2timestamp(line.ed_time_usecs))
        edit_time = strftime("%b %d %Y %H:%M:%S %z", line.time_tuple)
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
                                              wikiutil.quoteWikinameURL(pagename),
                                              img)
            else:
                img = request.theme.make_icon('diffrc')
                html_link = wikiutil.link_tag(request,
                                              wikiutil.quoteWikinameURL(line.pagename) +
                                              "?action=diff",
                                              img)
        
            revision = "rev %s" % (line.rev.lstrip('0'))
        
        user = line.getInterwikiEditorData(request)[-1]
        comment = " ".join((html_link,
                            page.link_to(request),
                            revision,
                            infolink,
                            user,
                            line.hostname,
                            line.addr,
                            format_comment(request, line)
                            ))
        comment = comment.replace('<', '&lt;').replace('>', '&gt;')

        request.write('<event\nstart="%s"\ntitle="%s"\nlink="%s">\n%s\n</event>\n\n' %
                      (edit_time, line.pagename, page_link, comment))

    request.write("</data>\n")
        
    raise MoinMoinNoFooter
    
"""
    <event
    start="Aug 02 2006 00:00:00 GMT"
            title="Trip to Beijing"
            link="http://travel.yahoo.com/"
                    >
                            Woohoo!
                                    </event>

"""
