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

def execute(pagename, request):
#    for key, values in request.form.iteritems():
#        request.write("%s: %s<br>\n" % (key, ", ".join(values)))

    coursepage = request.form.get("course", [None])[0]
    username = request.form.get("user", [None])[0]

    if not coursepage:
        Page(request, pagename).send_page(msg=u'Missing course name.')
        return None

    if not username:
        Page(request, pagename).send_page(msg=u'Missing user.')
        return None

    if not Page(request, coursepage).exists():
        message = u'%s does not exist.' % coursepage
        Page(request, pagename).send_page(msg=message)
        return None

    metas = get_metas(request, coursepage, ["gwikicategory"], display=True, checkAccess=False)
    if raippacategories["coursecategory"] not in metas["gwikicategory"]:
        message = u'%s is not coursepage.' % coursepage
        Page(request, pagename).send_page(msg=message)
        return None

    user = RaippaUser(request, username)
    currentuser = RaippaUser(request, request.user.name)
    
    if user.user != currentuser.user and not currentuser.isTeacher():
        return u'You are not allowed to view users (%s) statistics.' % user.user

    if request.form.has_key("select"):
        if request.form.has_key("compress"):
            compress = True
        else:
            compress = False

        getcourses = wikiutil.importPlugin(request.cfg, "macro", 'UserStats', 'getcourses')
        draw_ui = wikiutil.importPlugin(request.cfg, "macro", 'UserStats', 'draw_ui')

        courses = getcourses(request, user)
        _enter_page(request, pagename)
        html = draw_ui(request, courses, user, coursepage, compress)
        request.write(html)
        _exit_page(request, pagename)
    else:
        Page(request, pagename).send_page(msg=u'Invalid parameters.')
