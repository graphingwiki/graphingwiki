# -*- coding: utf-8 -*-
"""
    groupedit action
     - adds, removes or deletes users from groups

    @copyright: 2014 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
from MoinMoin.datastruct.backends.wiki_groups import WikiGroup
from MoinMoin.wikiutil import isGroupPage
from MoinMoin.user import User
from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page

from graphingwiki import values_to_form
from graphingwiki.editing import edit_group, savetext
from graphingwiki.util import form_escape

def return_msg(request, errmsg, text='', error=True, backto=None):
    request.reset()
    if text:
        text = form_escape(text)
    if backto:
        page = Page(request, backto)
        request.http_redirect(page.url(request))

    if error:
        request.theme.add_msg(errmsg + text, "error")
    else:
        request.theme.add_msg(errmsg + text)

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

    accounts = form.get('account')

    grouppage = form.get('group', [''])[0]
    if not grouppage:
        grouppage = request.page.page_name

    if not isGroupPage(grouppage, request.cfg):
        return return_msg(request, _('Not a valid group page: '), grouppage)
    if not request.user.may.write(pagename):
        return return_msg(request, _('You are not allowed to edit this page.'))
    if action not in ['add', 'set', 'del']:
        return return_msg(request, _('Unkown action: '), action)
    if not accounts:
        return return_msg(request, _('No accounts specified.'))
    for uname in accounts:
        if not User(request, name=uname).exists():
            return return_msg(request, _('User not valid: '), uname)
    if action == 'set' and len(accounts) % 2:
        return return_msg(request, _('Wrong number of arguments for set.'))

    members = request.groups[grouppage].members

    if action == 'add':
        for uname in accounts:
            if uname in members:
                return return_msg(request, _('User already in group: '), uname)
        backto = request.page.page_name
        page = PageEditor(request, grouppage)
        pagetext = page.get_raw_body()
        newtext = edit_group(request, pagetext, action, accounts)
        msg = page.saveText(newtext, 0,
                            comment="Added to group: " + ', '.join(accounts))
        return return_msg(request, msg, error=False, backto=backto)
    elif action == 'del':
        for uname in accounts:
            if uname not in members:
                return return_msg(request, _('User not in group: '), uname)
        backto = request.page.page_name
        page = PageEditor(request, grouppage)
        pagetext = page.get_raw_body()
        newtext = edit_group(request, pagetext, action, accounts)
        msg = page.saveText(newtext, 0,
                            comment="Deleted from group: " + 
                            ', '.join(accounts))
        return return_msg(request, msg, error=False, backto=backto)
    if action == 'set':
        for uname in accounts[::2]:
            if uname not in members:
                return return_msg(request, _('User not in group: '), uname)
        backto = request.page.page_name
        page = PageEditor(request, grouppage)
        pagetext = page.get_raw_body()
        newtext = edit_group(request, pagetext, action, accounts)
        msg = page.saveText(newtext, 0,
                            comment="Changed group members: " + 
                            ' -> '.join(accounts))
        return return_msg(request, msg, error=False, backto=backto)
