from MoinMoin.Page import Page
from MoinMoin import wikiutil
from graphingwiki.editing import get_metas
from raippa import RaippaUser

def execute(macro, text):
    request = macro.request
    pagename = request.page.page_name 
    coursepage = text

    if not request.user.name:
        return u'<a href="?action=login">Login</a> or <a href="UserPreferences">create user account</a>.'

    html = u'<h2>TimeTrack</h2>'

    if not Page(request, coursepage).exists():
        html += u'%s doesn\'t exist.' % coursepage
        return html

    user = RaippaUser(request)
    user_entries = user.gettimetrack(coursepage)

    for key, info in user_entries.iteritems():
        html += "%s %s %s %s<br>\n" % (info[0], info[1], info[2], info[3])

    getgroups = wikiutil.importPlugin(request.cfg, "action", 'editGroup', 'getgroups')
    groups = getgroups(request, coursepage)
    for group, users in groups.iteritems():
        if user.user in users:
            html += group
            html += ", ".join(users) 
    
    return html
