# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Raippa, based on modern theme

    @copyright: 2003-2005 by Nir Soffer, Thomas Waldmann
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.theme import ThemeBase
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from graphingwiki.editing import get_metas

forbidden = ['CategoryTaskFlow',
             'CategoryTaskOptions',
             'CategoryQuestionOptions',
             'CategoryAnswer',
             'CategoryTestInput',
             'CategoryTestOutput',
             'CategoryHistory',
             'CategoryDeadline',
             'CategoryBotComment']

class Theme(ThemeBase):

    name = "raippa"

    def logo(self):
        newlogo = self.cfg.url_prefix + '/' + Theme.name + '/img2/raippa-logo.gif'
        html = ThemeBase.logo(self)
        import re
        html = re.sub(r'src="([^"]*)"', r'src="' + newlogo +'"', html)
        return html

    def header(self, d, **kw):
        """ Assemble wiki header
        
        @param d: parameter dictionary
        @rtype: unicode
        @return: page header html
        """
        #adding raippa comments to msg
        session = self.request.session
        comments = session.get("comments",[])
        if comments:
            self.add_msg("<br>".join(comments))
            session["comments"] = list()

        html = [
            # Pre header custom html
            self.emit_custom_html(self.cfg.page_header1),
            
            # Header
            u'<div id="header">',
            self.logo(),
            self.searchform(d),
            u'<div id="login">',
            self.username(d),
            u'</div>',
            # u'<div id="locationline">',
            # self.interwiki(d),
            # self.title(d),
            # u'</div>',
            self.trail(d),
            self.navibar(d),
            #u'<hr id="pageline">',
            u'<div id="pageline"><hr style="display:none;"></div>',
            self.msg(d),
            # self.editbar(d),
            u'</div>',
            
            # Post header custom html (not recommended)
            self.emit_custom_html(self.cfg.page_header2),
            
            # Start of page
            self.startPage(),
        ]
        return u'\n'.join(html)

    def editorheader(self, d, **kw):
        """ Assemble wiki header for editor
        
        @param d: parameter dictionary
        @rtype: unicode
        @return: page header html
        """
        html = [
            # Pre header custom html
            self.emit_custom_html(self.cfg.page_header1),
            
            # Header
            u'<div id="header">',
            self.title(d),
            self.msg(d),
            u'</div>',
            
            # Post header custom html (not recommended)
            self.emit_custom_html(self.cfg.page_header2),
            
            # Start of page
            self.startPage(),
        ]
        return u'\n'.join(html)

    def trail(self, d):
        """ Assemble page trail
        
        @param d: parameter dictionary
        @rtype: unicode
        @return: trail html
        """
        request = self.request
        user = request.user
        html = ''
        if not user.valid or user.show_page_trail:
            trail = user.getTrail()
            if trail:
                items = []

                for pagename in trail:
                    #hide forbidden pages from trail
                    if request.user.name not in request.cfg.superuser:
                        if not Page(request, pagename).exists():
                            continue

                        metas = get_metas(request, pagename, ['gwikicategory'], checkAccess=False)
                        page_categories = metas.get('gwikicategory', list())
                        
                        skip = False
                        for category in page_categories:
                            if category in forbidden:
                                skip = True
                                continue

                        if skip:
                            continue

                    try:
                        interwiki, page = wikiutil.split_interwiki(pagename)
                        if interwiki != request.cfg.interwikiname and interwiki != 'Self':
                            link = (self.request.formatter.interwikilink(True, interwiki, page) +
                                    self.shortenPagename(page) +
                                    self.request.formatter.interwikilink(False, interwiki, page))
                            items.append('<li>%s</li>' % link)
                            continue
                        else:
                            pagename = page

                    except ValueError:
                        pass
                    page = Page(request, pagename)
                    title = page.split_title()
                    title = self.shortenPagename(title)
                    link = page.link_to(request, title)
                    items.append('<li>%s</li>' % link)
                html = '''
<ul id="pagetrail">
%s
</ul>''' % ''.join(items)
        return html

    def footer(self, d, **keywords):
        """ Assemble wiki footer
        
        @param d: parameter dictionary
        @keyword ...:...
        @rtype: unicode
        @return: page footer html
        """
        page = d['page']
        html = [
            # End of page
            self.pageinfo(page),
            self.endPage(),
            
            # Pre footer custom html (not recommended!)
            self.emit_custom_html(self.cfg.page_footer1),
            
            # Footer
            u'<div id="footer">',
            self.editbar(d),
            self.credits(d),
            self.showversion(d, **keywords),
            u'</div>',
            
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

