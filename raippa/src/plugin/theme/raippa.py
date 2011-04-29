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

    def pageinfo(self, page):
        """ Return html fragment with page meta data

        Since page information uses translated text, it uses the ui
        language and direction. It looks strange sometimes, but
        translated text using page direction looks worse.

        @param page: current page
        @rtype: unicode
        @return: page last edit information
        """
        _ = self.request.getText
        html = ''
        if self.shouldShowPageinfo(page):
            info = page.lastEditInfo()
            if info:
#                if info['editor']:
#                    info = _("last edited %(time)s by %(editor)s") % info
#                else:
                info = _("last modified %(time)s") % info
                pagename = page.page_name
                if self.request.cfg.show_interwiki:
                    pagename = "%s: %s" % (self.request.cfg.interwikiname, pagename)
                info = "%s  (%s)" % (wikiutil.escape(pagename), info)
                html = '<p id="pageinfo" class="info"%(lang)s>%(info)s</p>\n' % {
                    'lang': self.ui_lang_attr(),
                    'info': info
                    }
        return html

    def recentchanges_entry(self, d):
        """
        Assemble a single recentchanges entry (table row)

        @param d: parameter dictionary
        @rtype: string
        @return: recentchanges entry html
        """
        _ = self.request.getText
        html = []
        html.append('<tr>\n')

        html.append('<td class="rcicon1">%(icon_html)s</td>\n' % d)

        html.append('<td class="rcpagelink">%(pagelink_html)s</td>\n' % d)

        html.append('<td class="rctime">')
        if d['time_html']:
            html.append("%(time_html)s" % d)
        html.append('</td>\n')

        html.append('<td class="rcicon2">%(info_html)s</td>\n' % d)

        html.append('<td class="rceditor">')
        if d['editors']:
            for span in d['editors']:
                try:
                    start = span.index('title="')+7
                    end = span.index('@')+2
                    span = span[:start] + span[end:]

                    start = span.index('title="', end)+7
                    end = span.index('@', end)+2
                    span = span[:start] + span[end:]
                    html.append(span+'<br>')
                except ValueError:
                    html.append(span+'<br>')
#            html.append('<br>'.join(d['editors']))
        html.append('</td>\n')

        html.append('<td class="rccomment">')
        if d['comments']:
            if d['changecount'] > 1:
                notfirst = 0
                for comment in d['comments']:
                    html.append('%s<tt>#%02d</tt>&nbsp;%s' % (
                        notfirst and '<br>' or '', comment[0], comment[1]))
                    notfirst = 1
            else:
                comment = d['comments'][0]
                html.append('%s' % comment[1])
        html.append('</td>\n')

        html.append('</tr>\n')

        return ''.join(html)
        
def execute(request):
    """
    Generate and return a theme object
        
    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)

