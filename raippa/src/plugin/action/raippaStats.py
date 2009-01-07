from MoinMoin.Page import Page
from MoinMoin import wikiutil

from graphingwiki.editing import get_metas

from raippa import RaippaUser
from raippa import raippacategories, removelink, getflow

def _enter_page(request, pagename):
    request.http_headers()
    request.theme.send_title(pagename)
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter
    request.write(request.page.formatter.startContent("content"))

def _exit_page(request, pagename):
    request.write(request.page.formatter.endContent())
    request.theme.send_footer(pagename)

def draw_taskstats(request, task, course=None, user=None):
    currentuser = RaippaUser(request, request.user.name)
    if currentuser.isTeacher():
        pass
        #TODO: draw link and edit link

    metas = get_metas(request, task, ["title", "description"], display=True, checkAccess=False)
    if metas["title"]:
        title = metas["title"].pop()
    else:
        title = unicode()
        reporterror(request, "%s doesn't have title meta." % task)

#    if metas["description"]:
#        description = metas["description"].pop()
#    else:
#        description = unicode()
#        reporterror(request, "%s doesn't have description meta." % task)

    html = u'''
Page: <a href="%s/%s">%s</a> <a href="%s/%s?action=EditTask">[edit]</a>
<h1>%s</h1>
''' % (request.getBaseURL(), task, task, request.getBaseURL(), task, title)

    return html

def execute(pagename, request):
#    for key, values in request.form.iteritems():
#        request.write("%s: %s<br>\n" % (key, ", ".join(values)))

    coursepage = request.form.get("course", [None])[0]
    username = request.form.get("user", [None])[0]
    taskpage = request.form.get("task", [None])[0]
    html = unicode()

    currentuser = RaippaUser(request, request.user.name)
    if username != currentuser.user and not currentuser.isTeacher():
        return u'You are not allowed to view users (%s) statistics.' % username
        
    getcourses = wikiutil.importPlugin(request.cfg, "macro", 'RaippaStats', 'getcourses')

    if username:
        user = RaippaUser(request, username)
        courses = getcourses(request, user)
    else:
        courses = getcourses(request)

    if coursepage and coursepage not in courses.keys():
        return u'%s not in courselist.' % coursepage
    elif coursepage:
        if not Page(request, coursepage).exists():
            message = u'%s does not exist.' % coursepage
            Page(request, pagename).send_page(msg=message)
            return None

        metas = get_metas(request, coursepage, ["gwikicategory"], display=True, checkAccess=False)
        if raippacategories["coursecategory"] not in metas["gwikicategory"]:
            message = u'%s is not coursepage.' % coursepage
            Page(request, pagename).send_page(msg=message)
            return None

    if request.form.has_key("compress"):
        compress = True
    else:
        compress = False

    draw_stats = wikiutil.importPlugin(request.cfg, "macro", 'RaippaStats', 'draw_coursestats')
    draw_courselist = wikiutil.importPlugin(request.cfg, "macro", 'RaippaStats', 'draw_courselist')

    if username:
        if taskpage:
            if coursepage:
                html += draw_courselist(request, courses, user, coursepage, show_compress=False)
                html += draw_taskstats(request, taskpage, coursepage, user)
            else:
                html += draw_taskstats(request, taskpage, user=user)
        else:
            if coursepage:
                html += draw_courselist(request, courses, user, coursepage, compress)
                html += draw_stats(request, coursepage, user, compress)
            else:
                html += draw_courselist(request, courses, user, compress)
    else:
        if taskpage:
            if coursepage:
                html += draw_courselist(request, courses,selected=coursepage, show_compress=False)
                html += draw_taskstats(request, taskpage, coursepage)
            else:
                html += draw_taskstats(request, taskpage)
        else:
            if coursepage:
                html += draw_courselist(request, courses, selected=coursepage, compress=compress)
                html += draw_stats(request, coursepage, compress=compress)
            else:
                html += draw_courselist(request, courses, compress=compress)

    _enter_page(request, pagename)
    request.write(html)
    _exit_page(request, pagename)
