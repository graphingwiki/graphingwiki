from MoinMoin.Page import Page

from graphingwiki.editing import get_metas

from raippa import RaippaUser

def execute(macro, text):
    request = macro.request
    pagename = request.page.page_name 
    username = text
    html = unicode()

    user = RaippaUser(request, username)

    if user.user != request.user.name and not user.isTeacher():
        html += u'You are not allowed to view users (%s) status.' % user.user
        return html

    courselist = user.getcourses()
    courses = dict()
    for coursepage in courselist:
        metas = get_metas(request, coursepage, ["id", "name"], display=True, checkAccess=False)

        coursename = unicode()
        if metas["id"]:
            coursename += metas["id"].pop()
        else:
            coursename += coursepage

        if metas["name"]:
            coursename += " - %s" % metas["name"].pop() 

        courses[coursepage] = coursename

    #TODO: action name!
    html += u'''
<form method="POST" enctype="multipart/form-data" action="%s">
<input type="hidden" name="action" value="ACTION NAME HERE">
<select name="course">
''' % (request.page.page_name.split("/")[-1]) 
    for coursepage, coursename in courses.iteritems():
        html += u'<option value="%s">%s</option>\n' % (coursepage, coursename)
    html += u'''
</select>
</form>
'''
    return html

#    getgroups = wikiutil.importPlugin(request.cfg, "action", 'editGroup', 'getgroups')
#    groups = getgroups(request, parentpage)

#    html += getgrouphtml(request, groups)
#    return html
