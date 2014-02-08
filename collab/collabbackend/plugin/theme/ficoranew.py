from MoinMoin.theme import modernized as basetheme
from opencollabnew import Theme as ThemeParent

NAME = "ficoranew"

class Theme(ThemeParent):
    name = NAME

    def __init__(self, request):
        ThemeParent.__init__(self, request)
        self.stylesheets = self.stylesheets + (('screen', 'screen'),)

    def footer_string(self):
        if hasattr(self.cfg, 'footer_string'):
            footer_string = self.cfg.footer_string
        else:
            footer_string = \
            u'  <p class="footertext">Kyberturvallisuuskeskus<br>PL 313<br>00181 Helsinki'+ \
                '<br>Tel. +358 (0)295 390 230</p>'

        return footer_string

    def logo(self):
        mylogo = basetheme.Theme.logo(self)
        if not mylogo:
            mylogo = u'<a href="' + \
                self.request.script_root + '/' + self.request.cfg.page_front_page + \
                '"><img src="' + self.cfg.url_prefix_static + \
                '/ficoranew/img2/kyberturvallisuus_neg_rgb.png" alt="CERT-FI"></a>'
        return mylogo
