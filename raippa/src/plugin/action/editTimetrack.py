import time
from graphingwiki.editing import set_metas
from graphingwiki.editing import get_metas
from graphingwiki.editing import get_keys
from raippa import randompage, addlink, pageexists, raippacategories
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

def execute(pagename, request):
    if not request.user.name:
        Page(request, pagename).send_page(msg=u'Login please.')
        return None

    if request.form.has_key("delete") and request.form.has_key("entry"):
        entry = request.form.get("entry", [None])[0]
        if entry and pageexist(request, entry):
            try:
                success, msg = PageEditor(request, entry, do_editor_backup=0).deletePage()
                if success:
                    Page(request, pagename).send_page(msg=u'%s deleted succesfully.' % entry)
                    return None
                else:
                    Page(request, pagename).send_page(msg=u'Failed to delete %s.' % entry)
                    return None
            except:
                Page(request, pagename).send_page(msg=u'Failed to delete %s.' % entry)
                return None
        else:
            Page(request, pagename).send_page(msg=u'Failed to delete %s.' % entry)
            return None
    else:
        course = request.form.get("course", [None])[0]
        date = request.form.get("date", [None])[0]
        start = request.form.get("start", [None])[0]
        end = request.form.get("end", [None])[0]
        description = request.form.get("description", [None])[0]
        old_entry = request.form.get("entry", [None])[0]

        if old_entry:
            metas = get_metas(request, old_entry, ["user"], display=True, checkAccess=False)
            if (metas["user"] and request.user.name not in metas["user"]) or not metas["user"]:
                Page(request, pagename).send_page(msg=u'You are not allowed to edit this entry.')
                return None

        msg = None
        if date and start and end and course and description:
            data = {"user": [addlink(request.user.name)],
                    "course": [addlink(course)],
                    "date": [date],
                    "start": [start],
                    "end": [end],
                    "description": [description],
                    "gwikicategory": [raippacategories["timetrackcategory"]]}

            if old_entry:
                timetrackpage = old_entry
                oldkeys = getkeys(requst, timetrackpage).keys()
                remove = {old_entry: oldkeys}
            else:
                timetrackpage = randompage(request, "TimeTrack")
                remove = dict()

            data = {timetrackpage: data}

            result, msg = set_metas(request, remove, dict(), data)
            if result:
                Page(request, pagename).send_page(msg=u'Entry was saved successfully.')
            else:
                Page(request, pagename).send_page(msg=u'Failed to save')
        else:
            Page(request, pagename).send_page(msg=u'Missing parameters.')
