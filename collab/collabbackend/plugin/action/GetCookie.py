# -*- coding: iso-8859-1 -*-

import xmlrpclib
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.action import ActionBase

from collabbackend.plugin.xmlrpc.ClarifiedCookie import execute as generateCookie

from graphingwiki.editing import get_metas
from graphingwiki import values_to_form

SECONDS_IN_DAY = 24 * 60 * 60

class FakeXmlrpcObj(object):
    pass

class GetCookie(ActionBase):
    def __init__(self, pagename, request):
        ActionBase.__init__(self, pagename, request)
        self.getText = request.getText
        self.request = request
        self.use_ticket = True
        self.form_trigger = 'get'
        self.form_trigger_label = self.getText('Get cookie')

    def is_allowed(self):
        may = self.request.user.may
        return may.read(self.pagename)
    
    def do_action(self):
        form = values_to_form(self.request.values)
        days = form.get('days', [u''])[0]
        days = wikiutil.clean_input(days)

        try:
            days = int(days)
        except ValueError:
            return False, "Invalid number: %s" % days

        fake = FakeXmlrpcObj()
        fake.request = self.request
        cookie = generateCookie(fake, str(self.pagename), days * SECONDS_IN_DAY)
        if isinstance(cookie, xmlrpclib.Fault):
            return False, cookie.faultString

        default_filename = self.pagename + ".cookie"
        filename = form.get('filename', [default_filename])[0]

        self.filename = filename.encode("ascii", "ignore")
        self.cookie = cookie.data
    
        return True, "" 

    def do_action_finish(self, success):
        if success:
            self.request.headers['Content-Type'] = 'application/octet-stream'
            self.request.headers['Content-Disposition'] = 'attachment; ' + \
                                     'filename="%s"' % self.filename
            self.request.write(self.cookie)
        else:
            self.render_msg(self.make_form(), "dialog")

    def get_form_html(self, buttons_html):
        d = {
            'pagename': self.pagename,
            'email_label': self.getText("Days:"),
            'buttons_html': buttons_html,
            'querytext': self.getText('Get cookie for %s' % self.pagename),
        }
        return '''
<strong>%(querytext)s</strong>
<table>
    <tr>
        <td class="label"><label>%(email_label)s</label></td>
        <td class="content">
            <input type="text" name="days" maxlength="200">
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
    metas = get_metas(request, pagename, ["Type"], checkAccess=False)
    typeValue = metas.get("Type")
    if len(typeValue) == 0:
        licenseType = "cookie"
    else:
        licenseType = typeValue[0]

    if licenseType == "traditional":
        fake = FakeXmlrpcObj()
        fake.request = request
        cookie = generateCookie(fake, str(pagename))
        if isinstance(cookie, xmlrpclib.Fault):
            request.write(cookie.faultString)
            return

        filename = "license.key"
        request.headers['Content-Type'] = 'application/octet-stream',
        request.headers['Content-Disposition'] = 'attachment; ' + \
            'filename="%s"' % filename
        request.write(cookie.data)
    else:
        GetCookie(pagename, request).render()
