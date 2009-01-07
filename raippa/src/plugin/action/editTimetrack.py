import time
from graphingwiki.editing import set_metas
from raippa import randompage, addlink, raippacategories
from MoinMoin.Page import Page

def execute(pagename, request):
    if not request.user.name:
        return u'<a href="?action=login">Login</a> or <a href="UserPreferences">create user account</a>.'

    course = request.form.get("course", [None])[0]
    date = request.form.get("date", [None])[0]
    start = request.form.get("start", [None])[0]
    end = request.form.get("end", [None])[0]
    description = request.form.get("description", [None])[0]

    msg = None
    if date and start and end and course and description:
        data = {"user": [addlink(request.user.name)],
                "course": [addlink(course)],
                "date": [date],
                "start": [start],
                "end": [end],
                "description": [description],
                "gwikicategory": [raippacategories["timetrackcategory"]]}

        timetrackpage = randompage(request, "TimeTrack")
        data = {timetrackpage: data}

        result, msg = set_metas(request, dict(), dict(), data)
        if result:
            Page(request, pagename).send_page(msg=u'Entry was saved successfully.')
        else:
            Page(request, pagename).send_page(msg=u'Failed to save')
        return None
    else:
        Page(request, pagename).send_page(msg=u'Missing parameters.')
        return None
