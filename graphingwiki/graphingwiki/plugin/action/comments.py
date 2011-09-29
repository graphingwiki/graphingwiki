# -*- coding: iso-8859-1 -*-
import time

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.user import getUserIdentification

from graphingwiki import values_to_form
from graphingwiki.editing import set_metas

def save_comment(request, commentpage, sender, comment):
    comment = u'%s -- %s' % (comment, sender)
    edittime = time.strftime("%Y-%m-%d %H:%M:%S")
    metas = {commentpage: {edittime: [comment]}}

    return set_metas(request, dict(), dict(), metas)

def execute(pagename, request):
    form = values_to_form(request.values)

    comment = form.get('comment', [str()])[0].replace("\r\n", " ")
    commentpage = wikiutil.escape(form.get('commentpage', [str()])[0])

    if not commentpage:
        request.theme.add_msg('Missing commentpage.', 'error')
        Page(request, pagename).send_page()
        return

    if not comment:
        request.theme.add_msg('Missing comment.', 'error')
        Page(request, pagename).send_page()
        return

    if request.user.exists():
        sender = '[['+request.user.name+']]'
    else:
        sender = getUserIdentification(request)

    try:
        result, msg = save_comment(request, commentpage, sender, comment)
        if not result:
            request.theme.add_msg(msg, 'error')
            Page(request, pagename).send_page()
            return
    except:
        request.theme.add_msg('Failed to save comment.', 'error')
        Page(request, pagename).send_page()
        return

    Page(request, pagename).send_page()
