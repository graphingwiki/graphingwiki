# -*- coding: utf-8 -*-
"""
    groupedit action
     - adds, removes or deletes users from groups

    @copyright: 2014 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
from MoinMoin.Page import Page

from graphingwiki import values_to_form
from graphingwiki.groups import group_add, group_del, group_rename
from graphingwiki.util import form_escape

def return_msg(request, msg, error=True, backto=None):
    request.reset()
    msg = form_escape(msg)

    if error:
        request.theme.add_msg(msg, "error")
    else:
        if backto:
            page = Page(request, backto)
            request.http_redirect(page.url(request))
        request.theme.add_msg(msg)

    request.page.send_page()
    return

def execute(pagename, request):
    _ = request.getText

    if request.environ['REQUEST_METHOD'] != 'POST':
        request.page.send_page()
        return

    form = values_to_form(request.values)

    action = form.get('edit', ['None'])
    action = action[0]

    create = form.get('create', [False])
    create = create[0]

    grouppage = form.get('group', [''])[0]
    if not grouppage:
        grouppage = request.page.page_name

    accounts = form.get('account')

    if action not in ['add', 'del', 'rename']:
        return return_msg(request, _('Unkown action: ') + action)

    backto = request.page.page_name
    if action == 'add':
        succ, msg = group_add(request, grouppage, accounts)
        return return_msg(request, msg, error=not succ, backto=backto)
    elif action == 'del':
        succ, msg = group_del(request, grouppage, accounts)
        return return_msg(request, msg, error=not succ, backto=backto)
    elif action == 'rename':
        succ, msg = group_rename(request, grouppage, accounts)
        return return_msg(request, msg, error=not succ, backto=backto)
