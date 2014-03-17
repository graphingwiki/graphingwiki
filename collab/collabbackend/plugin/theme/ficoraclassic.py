# -*- coding: utf-8 -*-
"""
    MoinMoin - Ficora theme.

    Based on MoinMoin Modernized Theme.

    Modifications (c) by Pasi Kemi (Media Agency Bears: http://www.mediakarhut.fi)

    @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""

from MoinMoin.theme import modernized as basetheme


class Theme(basetheme.Theme):
    name = "ficoraclassic"

    def logo(self):
        mylogo = basetheme.Theme.logo(self)
        if not mylogo:
            mylogo = u'<div id="logo"><img src="' + \
                self.cfg.url_prefix_static + \
                '/ficoraclassic/img2/kyberturvallisuus_pos_rgb.png" alt="Kyberturvallisuuskeskus"></div>'
        return mylogo

    def header(self, d, **kw):
        """ Assemble wiki header

        @param d: parameter dictionary
        @rtype: unicode
        @return: page header html
        """
        html = [
            # Pre header custom html
            self.emit_custom_html(self.cfg.page_header1),

            # Header
            u'<div id="header">',
            u'<div id="blueline1">&nbsp;</div>',
            u'<div id="blueline2">&nbsp;</div>',
            self.logo(),
            self.searchform(d),
            self.username(d),
            #self.logo(),
            #u'<h1 id="locationline">',
            #self.interwiki(d),
            #self.title_with_separators(d),
            #u'</h1>',
            self.trail(d),
            self.navibar(d),
            #u'<hr id="pageline">',
            u'<div id="pageline"><hr style="display:none;"></div>',
            self.msg(d),
            self.editbar(d),
            u'</div>',

            # Post header custom html (not recommended)
            self.emit_custom_html(self.cfg.page_header2),

            # Start of page
            self.startPage(),
        ]
        return u'\n'.join(html)

    def footer(self, d, **keywords):
        """ Assemble wiki footer

        @param d: parameter dictionary
        @keyword ...:...
        @rtype: unicode
        @return: page footer html
        """

        if hasattr(self.cfg, 'footer_string'):
            footer_string = self.cfg.footer_string
        else:
            footer_string = u'<p>Viestintävirasto<br>' + \
                u'Kyberturvallisuuskeskus<br>PL 313<br>00181 Helsinki' + \
                u'<br>Puh. 0295 390 230</p>'

        page = d['page']
        html = [
            # End of page
            self.endPage(),

            # Pre footer custom html (not recommended!)
            self.emit_custom_html(self.cfg.page_footer1),

            # Footer
            u'<div id="footer">',
            self.pageinfo(page),
            #self.editbar(d),
            #self.credits(d),
            #self.showversion(d, **keywords),
            footer_string,
            u'</div>',
            u'<div id="blueline1">&nbsp;</div>',


            # Post footer custom html
            self.emit_custom_html(self.cfg.page_footer2),
            ]
        return u'\n'.join(html)


def execute(request):
    """
    Generate and return a theme object

    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)

