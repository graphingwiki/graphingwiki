# -*- coding: utf-8 -*-

import cgi

from MoinMoin import wikiutil, config
from MoinMoin.Page import Page
from MoinMoin.action import ActionBase

from graphingwiki import values_to_form
from graphingwiki.invite import *

NEW_TEMPLATE_VARIABLE = "invite_new_template"
NEW_TEMPLATE_DEFAULT = "InviteNewTemplate"
OLD_TEMPLATE_VARIABLE = "invite_old_template"
OLD_TEMPLATE_DEFAULT = "InviteOldTemplate"
GROUP_DEFAULT_VARIABLE = "invite_group_default"
GROUP_DEFAULT_DEFAULT = ""

class Invite(ActionBase):
    def __init__(self, pagename, request):
        ActionBase.__init__(self, pagename, request)
        self.getText = request.getText
        self.request = request
        self.use_ticket = True
        self.form_trigger = 'invite'
        self.form_trigger_label = self.getText('Invite')

    def _load_template(self, variable, default):
        name = getattr(self.request.cfg, variable, default)
        if not self.request.user.may.read(name):
            raise InviteException("You are not allowed to read template page '%s'." % name)

        page = Page(self.request, name)
        if not page.exists():
            raise InviteException("Template page '%s' does not exist." % name)

        return page.get_raw_body()

    def check_condition(self):
        try:
            self._load_template(NEW_TEMPLATE_VARIABLE, NEW_TEMPLATE_DEFAULT)
            self._load_template(OLD_TEMPLATE_VARIABLE, OLD_TEMPLATE_DEFAULT)
            check_inviting_enabled(self.request)
        except InviteException, ie:
            return unicode(ie)
        return None

    def is_allowed(self):
        return user_may_invite(self.request.user, self.pagename)

    def do_action(self):
        form = values_to_form(self.request.values)
        
        email = form.get('email', [u''])[0]
        email = wikiutil.clean_input(email).strip()
        if len(email) == 0:
            return False, "Please specify an email address."

        pagename = self.pagename
        try:
            new_template = self._load_template(NEW_TEMPLATE_VARIABLE, NEW_TEMPLATE_DEFAULT)
            old_template = self._load_template(OLD_TEMPLATE_VARIABLE, OLD_TEMPLATE_DEFAULT)

            if wikiutil.isGroupPage(pagename, self.request.cfg):
                myuser = invite_user_to_wiki(self.request, pagename, email, new_template, old_template)
                mygrouppage = pagename
            else:
                myuser = invite_user_to_page(self.request, pagename, email, new_template, old_template)
                mygrouppage = getattr(self.request.cfg, GROUP_DEFAULT_VARIABLE, GROUP_DEFAULT_DEFAULT)

            if mygrouppage:
                mycomment = "invited %s" % (email)
                try:
                    add_user_to_group(self.request, myuser, mygrouppage, comment=mycomment)
                except GroupException, ge:
                    tmp = "User invitation mail sent to address '%s', but could not add the user to group '%s': %s"
                    return True, tmp % (email, mygrouppage, unicode(ge))
                tmp = "User invitation mail sent to address '%s' and the user was added to group '%s'."
                return True, tmp % (email, mygrouppage)           

        except InviteException, ie:
            return False, cgi.escape(unicode(ie).encode(config.charset))
        return True, cgi.escape("Invitation mail sent to address '%s'." % email)

    def get_form_html(self, buttons_html):
        d = {
            'pagename': self.pagename,
            'email_label': self.getText("Email:"),
            'buttons_html': buttons_html,
            'querytext': self.getText('Invite user to visit this page'),
        }
        return '''
<strong>%(querytext)s</strong>
<table>
    <tr>
        <td class="label"><label>%(email_label)s</label></td>
        <td class="content">
            <input type="text" name="email" maxlength="200">
        </td>
    </tr>
    <tr>
        <td></td>
        <td class="buttons">
            %(buttons_html)s
        </td>
    </tr>
</table>
''' % d

def execute(pagename, request):
    """ Glue code for actions """
    Invite(pagename, request).render()
