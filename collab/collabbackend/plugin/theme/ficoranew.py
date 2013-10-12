from MoinMoin.theme import modernized as basetheme
from opencollabnew import Theme as ThemeParent

class Theme(ThemeParent):
    name = "ficoranew"

    def footer_string(self):
        if hasattr(self.cfg, 'footer_string'):
            footer_string = self.cfg.footer_string
        else:
            footer_string = \
            u'  <p class="footertext">CERT-FI<br>PL 313<br>00181 Helsinki'+ \
                '<br>Tel. +358 (0)295 390 230</p>'

        return footer_string

    def logo(self):
        mylogo = basetheme.Theme.logo(self)
        if not mylogo:
            mylogo = u'<div id="logo"><a href="' + \
                self.request.script_root + '/' + self.request.cfg.page_front_page + \
                '"><img src="' + self.cfg.url_prefix_static + \
                '/bootstrap/img2/cert-fi.png" alt="CERT-FI"></a></div>'
        return mylogo
