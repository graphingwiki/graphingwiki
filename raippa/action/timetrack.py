import time

from graphingwiki.editing import edit_meta
from graphingwiki.patterns import encode
from graphingwiki.patterns import getgraphdata

from raippa import randompage, addlink

from MoinMoin.Page import Page

timetrackcategory = u'CategoryTimetrack'

def execute(pagename, request):
    hours = request.form.get("hours", [None])[0]
    msg = None
    if hours:
        data = {"user":[addlink(request.user.name)],
                "course":[addlink(pagename)],
                "time":[time.strftime("%Y-%m-%d %H:%M:%S")],
                "hours":[hours],
                "description":[request.form.get("description", [""])[0]]}
        getgraphdata(request)
        timetrackpage = randompage(request, "TimeTrack")
        msg = edit_meta(request, timetrackpage, {u'': [u'']}, data, True, [timetrackcategory])

    page = Page(request, pagename)
    page.send_page(msg)
