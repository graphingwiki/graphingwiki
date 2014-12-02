# -*- coding: utf-8 -*-

from MoinMoin import wikiutil, config
from MoinMoin.Page import Page
from MoinMoin.action import ActionBase

from graphingwiki import values_to_form
from graphingwiki.invite import user_may_request_invite, request_invite, InviteException

from collabbackend import getCollabInfo

TEMPLATE_VARIABLE = "invite_request_template"
TEMPLATE_DEFAULT = "InviteRequestTemplate"


class requestinvite(ActionBase):
    def __init__(self, pagename, request, **kw):
        ActionBase.__init__(self, pagename, request)
        self.getText = request.getText
        self.request = request
        self.use_ticket = True
        self.form_trigger = 'requestinvite'
        self.form_trigger_label = wikiutil.escape(kw.get('button_text', [self.getText('Send Request')])[0], True)
        self.querytext = kw.get('text', [self.getText('Send invite request for collab')])[0]

        form = values_to_form(self.request.values)
        collab = form.get('collab', [u''])[0]
        self.collab = wikiutil.clean_input(collab).strip()

    def _load_template(self, variable, default):
        if not variable and default:
            name = default
        else:
            name = getattr(self.request.cfg, variable, default)

        if not self.request.user.may.read(name):
            raise InviteException("You are not allowed to read template page '%s'." % name)

        page = Page(self.request, name)
        if not page.exists():
            raise InviteException("Template page '%s' does not exist." % name)

        return page.get_raw_body()

    def check_condition(self):
        if not getattr(self.request.cfg, 'invite_request_default_contact', None):
            return "Invite request default contact not configured."

        try:
            self._load_template(TEMPLATE_VARIABLE, TEMPLATE_DEFAULT)
        except InviteException, ie:
            return unicode(ie)

        if not self.collab:
            return "Missing collab parameter."

        inviterequests = self.request.session.get("inviterequests", [])
        if self.collab in inviterequests:
            return "Already sent request for collab '%s'." % self.collab

        return None

    def is_allowed(self):
        return user_may_request_invite(self.request.user, self.pagename)

    def do_action(self):
        baseurl = self.request.cfg.collab_baseurl
        path = self.request.cfg.collab_basedir
        link, title, motd, contact = getCollabInfo(baseurl, path, self.collab)

        if not contact:
            contact = self.request.cfg.invite_request_default_contact

        try:
            template = self._load_template(TEMPLATE_VARIABLE, TEMPLATE_DEFAULT)
            request_invite(self.request, self.pagename, self.collab, link, contact, template)
        except InviteException, ie:
            return False, wikiutil.escape(unicode(ie).encode(config.charset))

        return True, "Invite request for collab '%s' sent." % self.collab

    def get_form_html(self, buttons_html):
        d = {
            'buttons_html': buttons_html,
            'querytext': wikiutil.escape(self.querytext),
            'collab': wikiutil.escape(self.collab),
        }
        return '''
<input type="hidden" name="collab" value="%(collab)s">
<strong>%(querytext)s '%(collab)s'?</strong>
<table>
    <tr>
        <td></td>
        <td class="buttons">
            %(buttons_html)s
        </td>
    </tr>
</table>
''' % d


def execute(pagename, request):
    requestinvite(pagename, request).render()
