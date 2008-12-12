from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.edting import get_metas

from raippa import removelink

def getgroups(request, parentpage):
    linkedpage = request.graphdata.getpage(parentpage)
    linking_in = linkedpage.get('in', {})
    pagelist = linking_in.get("course", [])
    groups = dict()
    for page in pagelist:
        if page.endswith("Group"):
            groups[page] = list()
            raw = Page(request, page).getPageText()
            for line in raw.split("\n"):
                if line.startswith(" * "):
                    user_in_line = removelink(line[3:].rstrip())
                    #user can only be in one group/course
                    groups[page].append(user_in_line)
    return groups

def getgroup(request, pagename):
    raw = Page(request, page).getPageText()
    group = list()
    for line in raw.split("\n"):
        if line.startswith(" * "):
            user_in_line = removelink(line[3:].rstrip())
            group.append(user_in_line)

    return group

def removeuser(request, group, user):
    raw = Page(request, group).getPageText()
    newcontent = list()
    for line in raw.split("\n"):
        if line.startswith(" * ") and removelink(line[3:].rstrip()) == user:
            continue
        newcontent.append(line)

    newcontent = "\n".join(newcontent)

    page = PageEditor(request, group)
    try:
        msg = page.saveText(newcontent, page.get_real_rev())
        return True
    except:
        return False

def adduser(request, group, user):
    oldcontent = Page(request, group).getPageText().split("\n")
    newcontent = list()
    if len(oldcontent) > 0:
        if oldcontent[0].startswith("#acl"):
            newcontent.append(oldcontent[0])

    newcontent.append(" * [[%s]]" % user)

    for line in oldcontent:
        if not line.startswith("#acl"):
            newcontent.append(line)

    newcontent = "\n".join(newcontent)

    page = PageEditor(request, group)
    try:
        msg = page.saveText(newcontent, page.get_real_rev())
        return True
    except:
        return False
        

def execute(pagename, request):
    course = request.form.get("course", [None])[0]
    grouppage = request.form.get("grouppage", [None])[0]
    groupname = request.form.get("groupname", [None])[0]
    user = request.form.get("user", [request.user.name])[0]

    if not course:
        Page(request, pagename).send_page(msg=u'Missing course page.')
        return None

    if request.form.has_key("leave") and grouppage:
        group = getgroup(request, grouppage)
        if user not in group:
            meta = get_metas(request, group, ["name"])
            if meta["name"]:
                groupname = meta["name"].pop()
            else:
                groupname = group
            Page(request, pagename).send_page(msg=u'User %s not in group %s' % (user, groupname))
        else:
            if removeuser(request, grouppage, user):
                Page(request, pagename).send_page(msg=u'User removed successfully.')
            else:
                Page(request, pagename).send_page(msg=u'Failed to remove user.')

    elif request.form.has_key("join") and grouppage:
        removed = list()
        groups = getgroups(request, course)
        for group, users in groups.iteritems():
            if group != grouppage and user in users:
                if removeuser(request, group, user):
                    removed.append(group)
            elif group == grouppage and user in users:
                Page(request, pagename).send_page(msg=u'User already in the group.')
                return None
        
        if adduser(request, grouppage, user):
            Page(request, pagename).send_page(msg=u'User added successfully.')
        else:
            Page(request, pagename).send_page(msg=u'Failed to remove user.')

    elif request.form.has_key("create") and groupname:
        groups = getgroups(request, course)
        for group in groups:
            meta = get_metas(request, group, ["name"])
            if meta["name"]:
                name = meta["name"].pop() 
                if name == groupname:
                    Page(request, pagename).send_page(msg=u"Group '%s' already exists." % name)
                    return None

        pageform = u'%s/%s' % (course, groupname)
        grouppage = pageform
        index = 0
        while Page(request, grouppage).exists():
            grouppage = pageform + u'_%i' % index
            index += 1

        content = u' * [[%s]]' % user
        page = PageEditor(request, grouppage)
        try:
            msg = page.saveText(newcontent, page.get_real_rev())
            Page(request, pagename).send_page(msg=u'Group created successfully.')
        except:
            Page(request, pagename).send_page(msg=u'Failed to create group.')

    elif request.form.has_key("delete") and grouppage:
        try:
            success, msg = PageEditor(request, grouppage, do_editor_backup=0).deletePage()
        except:
            success = False

        if success:
            Page(request, pagename).send_page(msg=u'Group deleted successfully.')
        else:
            Page(request, pagename).send_page(msg=u'Failed to delete group.')

    else:
        Page(request, pagename).send_page(msg=u'Invalid input.')
