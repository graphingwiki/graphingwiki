# -*- coding: utf-8 -*-
"""
    MoinMoin - Bootstrap theme.

    Based on the Ficora theme (c) by Pasi Kemi 
    (Media Agency Bears: http://www.mediakarhut.fi)

    Modifications by Juhani Eronen <exec@iki.fi> and Lauri Pokka

    @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""
import re

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.theme.modernized import Theme as ThemeParent
from MoinMoin.theme import get_available_actions

from graphingwiki.plugin.macro.LinkedIn import nodes

# FIXME: Caching of relevant portions

BREADCRUMB_ACTIONS = {'print': 'Print View',
                      'raw': 'Raw Text',
                      'info': 'Info',
                      'AttachFile': 'Attachments',
                      'Invite': 'Invite'}

BOOTSTRAP_THEME_CSS = [
    ("all", "bootstrap.min")
]

QUICKLINKS_RE = re.compile('<li class="userlink">.+?</li>', re.M)

NAME = "opencollabnew"
THEME_PATH = "../../" + NAME


class Theme(ThemeParent):
    name = NAME
    rev = ''
    available = ''

    css_files = []

    def __init__(self, request):
        ThemeParent.__init__(self, request)

        sheetsnames = ['stylesheets', 'stylesheets_print', 'stylesheets_projection']

        # include css and icon files from this theme when in inherited theme
        if self.name is not NAME:
            for sheetsname in sheetsnames:
                theme_sheets = getattr(self, sheetsname)
                parent_sheets = []
                for sheet in theme_sheets:
                    link = (sheet[0], THEME_PATH + "/css/" + sheet[1])
                    parent_sheets.append(link)

                # remove css files that are not defined in css_files of the inherited theme
                theme_sheets = [sheet for sheet in theme_sheets if sheet[1] in self.css_files]
                setattr(self, sheetsname, tuple(parent_sheets + theme_sheets))

            for key, val in self.icons.items():
                val = list(val)
                val[1] = THEME_PATH + "/img/" + val[1]
                self.icons[key] = tuple(val)

        # bootstrap css file should be before themes
        for sheet in reversed(BOOTSTRAP_THEME_CSS):
            link = (sheet[0], "../../bootstrap/css/" +sheet[1])
            self.stylesheets = (link,) + self.stylesheets

        self.available = get_available_actions(request.cfg,
                                               request.page,
                                               request.user)

    def logo(self):
        mylogo = ThemeParent.logo(self)
        if not mylogo:
            mylogo = u'''<div id="logo"><span class="navbar-brand">%s</span></div>''' % \
                     wikiutil.escape(self.cfg.sitename, True)

        return mylogo

    def _startnav(self):
        return u"""  <div class="navbar navbar-inverse navbar-fixed-top">
    <div class="navbar-header">
        <button type="button" class="navbar-toggle" data-toggle="collapse"
                data-target="#main-nav">
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
        </button>
        %s
      </div>
      <div class="collapse navbar-collapse" id="main-nav">
        <ul class="nav navbar-nav"> <!-- nav -->""" % (self.logo())

    def _endnav1(self):
        return u"""        </ul> <!-- /nav -->"""

    def _endnav2(self):
        return """    </div> <!-- /collapse -->
    </div>
  </div> <!-- /navbar -->"""

    def actionsmenu(self):
        request = self.request
        page = self.request.page
        _ = request.getText
        guiworks = self.guiworks(page)
        editor = request.user.editor_default
        editdisabled = False

        val = ""
        if not 'edit' in request.cfg.actions_excluded:
            if not (page.isWritable() and
                        request.user.may.write(page.page_name)):
                editdisabled = True
                val = """          <li class="disabled">
          <a title="%s"><i class="glyphicon glyphicon-edit"></i> </a>""" % \
                      _('Immutable Page')
            elif guiworks and editor == 'gui':
                val = """          <li class="active">
          <a title="%s" href="?action=edit&editor=gui">""" % _('Edit (GUI)')
                val += '<i class="glyphicon glyphicon-edit"></i></a>'
            else:
                val = """          <li class="active">
          <a title="%s" href="?action=edit">""" % _('Edit')
                val += '<i class="glyphicon glyphicon-edit"></i> </a>'
        else:
            editdisabled = True

        val += '\n          <li class="active dropdown"><a href="#" '
        val += 'title="%s" class="dropdown-toggle" data-toggle="dropdown">' % \
               _("More Actions:")
        val += '<i class="glyphicon glyphicon-folder-open"></i></a>'
        val += '\n            <ul class="dropdown-menu">\n'

        menu = [
            'info',
            'edit',
            'AttachFile',
            'raw',
            'print',
            '',
            'RenamePage',
            'CopyPage',
            'DeletePage',
            '',
            'revert',
            'PackagePages',
            'SyncPages',
            'refresh',
            '',
            'Despam',
            'SpellCheck',
            'LikePages',
            'LocalSiteMap',
            'RenderAsDocbook',
            'MyPages',
            'SubscribeUser',
        ]

        titles = {
            'info': _('Info'),
            'edit': _('Edit'),
            'AttachFile': _('Attachments'),
            'raw': _('Raw Text'),
            'print': _('Print View'),
            'refresh': _('Delete Cache'),
            'SpellCheck': _('Check Spelling'),
            'RenamePage': _('Rename Page'),
            'CopyPage': _('Copy Page'),
            'DeletePage': _('Delete Page'),
            'LikePages': _('Like Pages'),
            'LocalSiteMap': _('Local Site Map'),
            'MyPages': _('My Pages'),
            'SubscribeUser': _('Subscribe User'),
            'Despam': _('Remove Spam'),
            'revert': _('Revert to this revision'),
            'PackagePages': _('Package Pages'),
            'RenderAsDocbook': _('Render as Docbook'),
            'SyncPages': _('Sync Pages'),
        }

        _s = '              '
        val += _s + '<li>%s</li>\n' % (self.quicklinkLink(page))
        val += _s + '<li>%s</li>\n' % (self.subscribeLink(page))

        for action in menu:
            if not action:
                val += _s + '<li class="divider"></li>\n'
                continue
            disabled = False

            if action == 'refresh':
                if not page.canUseCache():
                    disabled = True
            elif action == 'revert' and not \
                request.user.may.revert(page.page_name):
                disabled = True
            elif action == 'SubscribeUser' and not \
                request.user.may.admin(page.page_name):
                disabled = True
            elif action == 'Despam' and not request.user.isSuperUser():
                disabled = True
            elif action[0].isupper() and not action in self.available:
                disabled = True

            if disabled:
                val += _s + '<li class="disabled"><a>%s</a></li>\n' % \
                       (titles[action])
            elif action == 'edit':
                if editdisabled:
                    continue
                if editor == "gui":
                    val += _s + '<li><a href="?action=edit%s">%s</a></li>\n' % \
                           (self.rev, titles[action])
                elif guiworks:
                    val += _s + '<li><a href="?action=edit&editor=gui' + \
                           '%s">%s</a></li>\n' % (self.rev, _('Edit (GUI)'))
            else:
                val += _s + '<li><a href="?action=%s%s">%s</a></li>\n' % \
                       (action, self.rev, titles[action])
        val += """            </ul>
          </li>
"""

        more = [item for item in self.available if not item in titles
        and not item in ('AttachFile', )]
        more.sort()
        if not more:
            return val

        val += """          <li class="active dropdown">
            <a href="#" class="dropdown-toggle" data-toggle="dropdown">
               <i class="glyphicon glyphicon-wrench" title="%s"></i></a>
            <ul class="dropdown-menu">\n""" % _("More Actions:")
        _s = '              '
        for action in more:
            val += _s + '<li><a href="?action=%s%s">%s</a></li>\n' % \
                   (action, self.rev, _(action))
        val += """            </ul>
          </li>"""

        return val

    def _wraplink(self, html):
        return u'          <li>' + html + u'</li>'

    def navibar(self, d):
        _ = self.request.getText

        content = ThemeParent.navibar(self, d)
        content = '\n'.join(content.split('\n')[2:-2])
        content = content.replace('</li>', '</li>\n          ')
        content = '          ' + content.rstrip()

        content = content.replace('current">', 'current active">')
        content = content.replace('>%s<' % self.request.cfg.page_front_page,
                                  ' title="%s">' %
                                  self.request.cfg.page_front_page +
                                  '<i class="glyphicon glyphicon-home"></i><')

        content = content.replace('>%s<' % _("CollabList"),
                                  ' title="%s">' % _("CollabList") +
                                  '<i class="glyphicon glyphicon-globe"></i><')
        content = content.replace('>%s<' % _("Collab"),
                                  ' title="%s">' % _("Collab") +
                                  '<i class="glyphicon glyphicon-comment"></i><')

        page_recentchanges = \
            wikiutil.getLocalizedPage(self.request, 'RecentChanges').page_name
        content = content.replace('>%s<' % (page_recentchanges),
                                  ' title="%s">' % (page_recentchanges) +
                                  '<i class="glyphicon glyphicon-list-alt"></i><')
        page_findpage = \
            wikiutil.getLocalizedPage(self.request, 'FindPage').page_name
        content = content.replace('>%s<' % (page_findpage),
                                  ' title="%s">' % (page_findpage) +
                                  '<i class="glyphicon glyphicon-search"></i><')
        page_help_contents = \
            wikiutil.getLocalizedPage(self.request, 'HelpContents').page_name
        content = content.replace('">' + page_help_contents,
                                  '" title="%s">' % page_help_contents +
                                  '<i class="glyphicon glyphicon-question-sign' +
                                  '"></i>')

        quicklinks = QUICKLINKS_RE.findall(content)
        content = QUICKLINKS_RE.sub('', content)

        if quicklinks:
            val = """<li class="active dropdown">
            <a href="#" class="dropdown-toggle" data-toggle="dropdown">
               <i class="icon-star-empty" title="%s"></i></a>
            <ul class="dropdown-menu">\n""" % _("Quicklinks")

            for item in quicklinks:
                val += "               %s\n" % (item.replace('', ''))

                val += """            </ul>
          </li>
"""
            content += val

        return content

    def username(self, d):
        request = self.request
        _ = request.getText

        userlinks = []
        # Add username/homepage link for registered users. We don't care
        # if it exists, the user can create it.
        if request.user.valid and request.user.name:
            interwiki = wikiutil.getInterwikiHomePage(request)
            linkpage = '#'
            if interwiki[0] == 'Self':
                wikitail = wikiutil.url_unquote(interwiki[1])
                linkpage = request.script_root + '/' + wikitail

            name = request.user.name
            urls = []

            plugins = wikiutil.getPlugins('userprefs', request.cfg)
            for sub in plugins:
                if sub in request.cfg.userprefs_disabled:
                    continue
                cls = wikiutil.importPlugin(request.cfg, 'userprefs',
                                            sub, 'Settings')
                obj = cls(request)
                if not obj.allowed():
                    continue
                url = request.page.url(request, {'action': 'userprefs',
                                                 'sub': sub})
                urls.append('<a href="%s">%s</a>' % (url, obj.title))

            out = ""

            if urls:
                out = """
                  <div class="input-group-btn">
        <button class="btn btn-default dropdown-toggle" data-toggle="dropdown" tabindex="-1">
          <i class="glyphicon glyphicon-user"></i> <span class="caret"></span>
        </button>
        <ul class="dropdown-menu pull-left">
            <li class="nav-header"><a href="%s">%s</a></li>
                """ % (linkpage, name)

                for url in urls:
                    out += "                  <li>%s</li>\n" % (url)

                out += """
                </ul>
            </div>"""

            return out

    def search_user_form(self, d):
        _ = self.request.getText
        url = self.request.href(d['page'].page_name)

        return """
  <form method="get" action="%s">

    <div class="input-group navbar-form form-group pull-right">\n%s
            <input type="hidden" name="action" value="fullsearch">
            <input type="hidden" name="context" value="180">


      <input class="form-control search" placeholder="Search" name="value">
      <div class="input-group-btn">
        <input class="btn btn-primary" name="titlesearch" type="submit" value="%s">
        <button type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown" tabindex="-1">
          <span class="caret"></span>
        </button>
        <ul class="dropdown-menu pull-right" role="menu">
          <li></li>
          <li><input class="btn btn-link" name="metasearch" type="submit" value="%s"></li>
          <li><input class="btn btn-link" name="fullsearch" type="submit" value="%s"></li>
        </ul>
      </div>
    </div>
  </form>
        """ % (url, self.username(d), _("Title"), _("Search Full Text"), _("Meta Search"))

    def header(self, d, **kw):
        """ Assemble wiki header

        @param d: parameter dictionary
        @rtype: unicode
        @return: page header html
        """
        if self.request.rev:
            if self.request.page.current_rev() != self.request.rev:
                self.rev = '&rev=%d' % (self.request.rev)
        else:
            self.rev = ''

        html = [
            # Pre header custom html
            self.emit_custom_html(self.cfg.page_header1),

            # Header
            u'<div id="header">',

            # Top-padding element that has height that matches
            # the height of the fixed position top navbar. Adding
            # padding to body would be normal approach, but some
            # pages that don't have the navbar, such as editors
            # would then show the extra padding on top.
            u'<div id="top-padding"></div>',

            self._startnav(),
            self.navibar(d),
            self.actionsmenu(),
            self._endnav1(),
            self.search_user_form(d),
            self._endnav2(),
            self.breadcrumbs(),
            self.msg(d),
            u'</div> <!-- /header -->',

            # Post header custom html (not recommended)
            self.emit_custom_html(self.cfg.page_header2),

            # Start of page
            self.startPage(),
        ]
        return u'\n'.join(html)

    def breadcrumbs(self):
        request = self.request
        _ = request.getText
        user = request.user
        items = []

        if not user.valid or user.show_page_trail:
            trail = user.getTrail()
            if trail:
                for pagename in trail:
                    try:
                        interwiki, page = wikiutil.split_interwiki(pagename)
                        if interwiki != request.cfg.interwikiname \
                            and interwiki != 'Self':
                            link = (
                                self.request.formatter.interwikilink(
                                    True, interwiki, page) +
                                self.shortenPagename(page) +
                                self.request.formatter.interwikilink(
                                    False, interwiki, page))
                            items.append(link)
                            continue
                        else:
                            pagename = page
                    except ValueError:
                        pass
                    page = Page(request, pagename)
                    title = page.split_title()
                    title = self.shortenPagename(title)
                    link = page.link_to(request, title)
                    items.append(link)

        val = """  <div class="navbar-collapse collapse breadcrumb">
    <ul class="breadcrumb pull-left">"""

        for item in items:
            val += '\n      <li>%s</li>' % item

        val += '\n    </ul>\n    <ul class="breadcrumb pull-right">'
        actions = getattr(request.cfg, 'bootstrap_actions',
                          BREADCRUMB_ACTIONS)
        for i, (act, text) in enumerate(actions.iteritems()):
            if act[0].isupper() and not act in self.available:
                continue
            span = (i != 0) and '' or ''
            val += '\n      <li><a href="?action=%s%s">%s</a>%s</li>' % (act, self.rev, text, span)

        val += """
      <li class="toggleCommentsButton" style="display:none;">
          <a href="#" class="nbcomment" onClick="toggleComments(); return false;">%s</a>
      </li>
    </ul>
  </div>""" % _('Comments')

        return val

    def linkedin(self):
        if not getattr(self.request.cfg, 'theme_linkedin', True):
            return ''
        _ = self.request.getText

        val = ''
        li = nodes(self.request, self.request.page.page_name, False)
        if not li:
            return val

        val = '<div id="message">\n<ul class="inline">\n<li>%s</li>\n' % \
              _("Linked in pages")
        for l in li:
            val += '<li>%s</li>' % (l)
        val += '</div>\n'
        return val

    def footer_string(self):
        if hasattr(self.cfg, 'footer_string'):
            footer_string = self.cfg.footer_string
        else:
            footer_string = '<p class="footertext"></p>'

        return footer_string

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
            self.endPage(),

            '<script src="' + self.cfg.url_prefix_static + \
            '/bootstrap/js/bootstrap.js"></script>',

            # Pre footer custom html (not recommended!)
            self.emit_custom_html(self.cfg.page_footer1),

            self.linkedin(),

            # Footer
            self.breadcrumbs(),
            u'<div id="footer">',
            self.pageinfo(page),
            self.footer_string(),
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

