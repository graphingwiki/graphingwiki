from MoinMoin.Page import Page
import MoinMoin.wikiutil as wikiutil

from graphingwiki.editing import get_metas

def getgrouphtml(request, groups):
    html = u'Select group from the list or create new.<br>\n'

    usershtml = unicode()
    selecthtml = u'<select name=grouppage>\n'
    selecthtml += u'<option>Create new</option>\n'

    for group in groups:
        meta = get_metas(request, group, ["name"])
        if meta["name"]:
            groupname = meta["name"].pop()
        else:
            groupname = group

        if request.user.name in groups[group]:
            selecthtml += u'<option value="%s" selected>%s</option>\n' % (group, groupname)
        else:
            selecthtml += u'<option value="%s">%s</option>\n' % (group, groupname)

        #create user tables
        usershtml += u'<table border="1">\n'
        usershtml += u'<tr><th>%s</th></tr>\n' % groupname
        for user in groups[group]:
            usershtml += u'<tr><th>%s</th></tr>\n' % user
        if request.user.name in groups[group]:
            usershtml += u'<tr><th>leave buttton</th></tr>\n'
        else:
            usershtml += u'<tr><th>join buttton</th></tr>\n'
        usershtml += u'</table>'

    selecthtml += u'</select><br>\n'

    html += selecthtml
    html += u'<input type="text" name="groupname" size="20"/>'
    html += usershtml

    return html

def execute(macro, text):
    request = macro.request
    pagename = request.page.page_name 
    parentpage = text
    html = u'<h2>Group selector</h2>'

    if not Page(request, parentpage).exists():
        html += u'Parent %s doesn\'t exist.' % parentpage
        return html

    getgroups = wikiutil.importPlugin(request.cfg, "action", 'editGroup', 'getgroups')
    groups = getgroups(request, parentpage)
    
    html += getgrouphtml(request, groups)
    return html
