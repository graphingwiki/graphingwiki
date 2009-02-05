# -*- coding: utf-8 -*-

from graphingwiki.invite import invite_user_by_email, check_inviting_enabled, user_may_invite, InviteException

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.action import ActionBase

NEW_TEMPLATE_VARIABLE = "invite_new_template"
NEW_TEMPLATE_DEFAULT = "InviteNewTemplate"
OLD_TEMPLATE_VARIABLE = "invite_old_template"
OLD_TEMPLATE_DEFAULT = "InviteOldTemplate"

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
        email = self.form.get('email', [u''])[0]
        email = wikiutil.clean_input(email).strip()
        if len(email) == 0:
            return False, "Please specify an email address."

        pagename = self.pagename

        try:
            new_template = self._load_template(NEW_TEMPLATE_VARIABLE, NEW_TEMPLATE_DEFAULT)
            old_template = self._load_template(OLD_TEMPLATE_VARIABLE, OLD_TEMPLATE_DEFAULT)
            
            return False, invite_user_by_email(self.request, pagename, email, new_template, old_template)
        except InviteException, ie:
            return False, unicode(ie)

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
