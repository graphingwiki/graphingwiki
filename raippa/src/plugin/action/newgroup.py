# -*- coding: iso-8859-1 -*-
from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page
from MoinMoin.user import User
from MoinMoin.wikiutil import quoteWikinameURL

from raippa.user import User as RaippaUser
from raippa import raippausers

def execute(pagename, request):
    user = RaippaUser(request, request.user.name)
    if not user.is_student() and not user.is_teacher():
        request.theme.add_msg(u'Your not allowed to do this action.', 'error')
        Page(request, pagename).send_page()
        return

    groupname = request.form.get('groupname', [unicode()])[0]
    if not groupname:
        request.theme.add_msg(u'Missing groupname.', 'error')
        Page(request, pagename).send_page()
        return

    grouppage = groupname.replace(u" ", u"")
    grouppage = grouppage.replace(u"_", u"")
    grouppage = grouppage+u"Group"

    page = PageEditor(request, grouppage)
    if page.exists():
        request.theme.add_msg(u'Group "%s" already exists.' % groupname, 'error')
        Page(request, pagename).send_page()
        return

    template = Page(request, "GroupTemplate").get_raw_body()
    template = template.replace("student", request.user.name)

    admin = User(request, name=raippausers[0])
    original = request.user
    request.user = admin

    try:
        msg = page.saveText(template, page.get_real_rev())
    except Exception, e:
        request.user = original
        request.theme.add_msg(unicode(e), 'error')
        Page(request, pagename).send_page()
        return

    request.user = original
    url = u'%s/%s?action=edit' % (request.getBaseURL(), quoteWikinameURL(grouppage))
    request.http_redirect(url)

