# -*- coding: utf-8 -*-
"""
    MoinMoin - Bootstrap theme.

    @copyright: 2014 by Lauri Pokka <larpo@codenomicon.com>
    @copyright: 2013 by Juhani Eronen <exec@iki.fi>

    @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""
import re

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.theme.modernized import Theme as ThemeParent
from MoinMoin.theme import get_available_actions

from graphingwiki.plugin.macro.LinkedIn import nodes

# FIXME: Caching of relevant portions

EDIT_ACTIONS = [
    'CopyPage',
    'RenamePage',
    'DeletePage',
    'MetaFormEdit',
    'MetaEdit',
]

ACTION_NAMES = {
    'info': 'Info',
    'edit': 'Edit',
    'AttachFile': 'Attachments',
    'raw': 'Raw Text',
    'print': 'Print View',
    'refresh': 'Delete Cache',
    'SpellCheck': 'Check Spelling',
    'RenamePage': 'Rename Page',
    'CopyPage': 'Copy Page',
    'DeletePage': 'Delete Page',
    'LikePages': 'Like Pages',
    'LocalSiteMap': 'Local Site Map',
    'MyPages': 'My Pages',
    'SubscribeUser': 'Subscribe User',
    'Despam': 'Remove Spam',
    'revert': 'Revert to this revision',
    'PackagePages': 'Package Pages',
    'RenderAsDocbook': 'Render as Docbook',
    'SyncPages': 'Sync Pages',
    'Invite': 'Invite',
}

BOOTSTRAP_THEME_CSS = [
    ("all", "bootstrap.min")
]

QUICKLINKS_RE = re.compile('<li class="userlink">.+?</li>', re.M)

NAME = "opencollab"
THEME_PATH = "../../" + NAME


class Theme(ThemeParent):
    name = NAME
    rev = ''
    available = ''

    css_files = []

    GLYPHICONS = {
        'FrontPage': 'glyphicon glyphicon-home',
        'CollabList': 'glyphicon glyphicon-list',
        'edit': 'glyphicon glyphicon-edit',
        'RecentChanges': 'glyphicon glyphicon-time',
        'Collab': 'glyphicon glyphicon-comment',
    }

    BREADCRUMB_ACTIONS = [
        'print',
        'raw',
        'info',
        'AttachFile',
        'Invite',
    ]

    EXCLUDED_ACTIONS = [
        'MetaSearch',
        'Despam',
        'SpellCheck',
        'LikePages',
        'LocalSiteMap',
        'RenderAsDocbook',
        'MyPages',
        'SubscribeUser',
        'N3Dump',
        'RdfInfer',
        'PackagePages',
        'Load',
        'Save',
        'SyncPages',
        'CheckTranslation',
        'RecommendPage',
        'SvgEditor',
        'SlideShow',
        'revert',
    ]

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
            link = (sheet[0], "../../bootstrap/css/" + sheet[1])
            self.stylesheets = (link,) + self.stylesheets

        actions = get_available_actions(request.cfg,
                                        request.page,
                                        request.user)

        excluded = self.EXCLUDED_ACTIONS + getattr(request.cfg, 'actions_excluded', [])
        included = getattr(request.cfg, 'actions_included', [])
        self.available_actions = [action for action in actions
                                  if action in included or action not in excluded]

    def title(self, d):
        """
        Title only gets called from ThemeBase.send_title in print
        mode, where it emits html that is not rendered in
        opencollab-based themes. Overloading to send an empty string.
        """
        return u''

    def logo(self):
        mylogo = ThemeParent.logo(self)
        if not mylogo:
            mylogo = u'''<span>%s</span>''' % \
                     wikiutil.escape(self.cfg.sitename, True)

        return mylogo

    def _actiontitle(self, action):
        _ = self.request.getText
        name = ACTION_NAMES.get(action, action)
        return _(name)

    def _can_edit(self):
        request = self.request
        page = self.request.page

        if 'edit' in request.cfg.actions_excluded or \
                not page.isWritable() or \
                not request.user.may.write(page.page_name):
            return False
        else:
            return True

    def editmenu(self, d):
        request = self.request
        page = self.request.page
        _ = request.getText

        if self.rev:
            li = u'<li><a href="?action=revert%s">%s</a></li>' %\
                 (self.rev, self._actiontitle('revert'))
        else:
            editor = request.user.editor_default
            editurl = u"?action=edit"
            if self.guiworks(page) and editor == 'gui':
                editurl += u"&amp;editor=gui"

            li = u'<li><a href="%s">%s</a></li>' % (editurl, _('Edit'))

        if not self._can_edit():
            li = ""

        return u"""
    <ul class="nav navbar-nav editmenu">
        %s
    </ul>""" % li

    def actionsmenu(self, d, is_footer):
        request = self.request
        page = self.request.page
        _ = request.getText

        ignored = EDIT_ACTIONS + self.BREADCRUMB_ACTIONS

        links = []

        links.append(u'<li>%s</li>\n' % (self.quicklinkLink(page)))

        if self.subscribeLink(page):
            links.append(u'<li>%s</li>\n' % (self.subscribeLink(page)))

        actions = [item for item in self.available_actions if item not in ignored]
        actions.sort()

        if self._can_edit() and not self.rev:
            for action in EDIT_ACTIONS:
                link = u'<li><a href="?action=%s">%s</a></li>' % \
                       (action, self._actiontitle(action))
                links.append(link)

            links.append(u'<li class="divider"></li>')

        for action in actions:
            link = u'<li><a href="?action=%s%s">%s</a></li>' % \
                   (action, self.rev, self._actiontitle(action))
            links.append(link)

        dropup = ""
        if is_footer:
            dropup = "dropup"

        return u"""
        <li class="%s">
            <a title="%s" class="dropdown-toggle" data-toggle="dropdown">
                <i class="glyphicon glyphicon-wrench"></i>
            </a>
            <ul class="dropdown-menu">
                %s
            </ul>
        </li>""" % (dropup, _("More Actions"), (u"\n" + u" " * 10).join(links))

    def navibar(self, d, *items):
        """ Assemble the navibar

        @param d: parameter dictionary
        @rtype: unicode
        @return: navibar html
        """
        request = self.request
        found = {}  # pages we found. prevent duplicates
        links = []  # navibar items
        item = u'<li class="%s">%s</li>'
        item_icon = u' title="%s"><i class="%s"></i><'
        current = d['page_name']

        default_items = [
            u'CollabList',
            getattr(request.cfg, 'page_front_page', u"FrontPage"),
            u'RecentChanges',
        ]

        logolink = self.logo()
        nav_items = getattr(request.cfg, 'navi_bar_new', default_items)

        if nav_items[0] == "CollabList" and request.user.valid:
            collablist = "collab-list"
        else:
            collablist = ""

        for i, text in enumerate(nav_items):
            pagename, link = self.splitNavilink(text)
            if i == 0:
                if text:
                    link = link.replace(">%s<" % pagename, '>' + self.logo() + '<')
                    logolink = link
                continue
            if pagename in self.GLYPHICONS:
                icon = item_icon % (pagename, self.GLYPHICONS[pagename])
                link = link.replace(">%s<" % pagename, icon)

            if pagename == current:
                cls = 'wikilink current'
            else:
                cls = 'wikilink'
            links.append(item % (cls, link))
            found[pagename] = 1

        # Add user links to wiki links, eliminating duplicates.
        #userlinks = request.user.getQuickLinks()
        #for text in userlinks:
        #    # Split text without localization, user knows what he wants
        #    pagename, link = self.splitNavilink(text, localize=0)
        #    if not pagename in found:
        #        if pagename == current:
        #            cls = 'userlink current'
        #        else:
        #            cls = 'userlink'
        #        items.append(item % (cls, link))
        #        found[pagename] = 1

        return u"""
    <nav class="navbar navbar-inverse navbar-fixed-top">
        <div class="navbar-header">
            <button type="button" class="navbar-toggle" data-toggle="collapse"
                    data-target="#main-nav">
              <span class="icon-bar"></span>
              <span class="icon-bar"></span>
              <span class="icon-bar"></span>
            </button>
            <div id="logo" class="navbar-brand %s">
                    %s
            </div>
        </div>
        <div class="collapse navbar-collapse" id="main-nav">
            <ul class="nav navbar-nav">
                %s
            </ul>
            %s
        </div>
    </nav>""" % (collablist, logolink, u'\n'.join(links), u'\n'.join(items))

    def username(self, d):
        request = self.request
        _ = request.getText

        urls = []

        # Add username/homepage link for registered users. We don't care
        # if it exists, the user can create it.
        if request.user.valid and request.user.name:
            interwiki = wikiutil.getInterwikiHomePage(request)
            linkpage = '#'
            if interwiki[0] == 'Self':
                wikitail = wikiutil.url_unquote(interwiki[1])
                linkpage = request.script_root + '/' + wikitail

            name = wikiutil.escape(request.user.name)
            urls.append('<li class="nav-header"><a href="%s">%s</a></li>'
                    % (linkpage, name))

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
                urls.append('<li><a href="%s">%s</a></li>' % (url, obj.title))

        if request.user.valid:
            if request.user.auth_method in request.cfg.auth_can_logout:
                query = {'action': 'logout', 'logout': 'logout'}
                url = request.page.url(request, query)
                urls.append('<li><a href="%s">%s</a></li>' % (url, _('Logout')))
        elif request.cfg.auth_have_login:
            query = {'action': 'login'}
            # special direct-login link if the auth methods want no input
            if request.cfg.auth_login_inputs == ['special_no_input']:
                query['login'] = '1'
            url = request.page.url(request, query)
            urls.append('<li><a href="%s">%s</a></li>' % (url, _('Login')))

        formadd = getattr(request.cfg, 'user_form_add', ())
        # Please note that you need to have a function of the form
        # lambda self, req: ... to the config as the function is
        # defined within a class.
        formcond = getattr(request.cfg, 'user_form_addcondition',
                           lambda req: True)
        if formcond(request):
            for url, text in formadd:
                urls.append('<li><a href="%s">%s</a></li>' % (url, _(text)))

        out = ""

        if urls:
            out = u"""
        <ul class="nav navbar-nav navbar-right">
            <li>
            <a class="dropdown-toggle" data-toggle="dropdown" title="%s">
              <i class="glyphicon glyphicon-user"></i>
            </a>
            <ul class="dropdown-menu navbar-right">
                %s
            </ul>
            </li>
        </ul>""" % (_('User Preferences'), ("\n" + " " * 16).join(urls))

        return out

    def search_form(self, d):
        _ = self.request.getText
        url = self.request.href(d['page'].page_name)

        return u"""
  <form method="get" class="navbar-right navbar-form" action="%s">
    <div class="form-group">
      <div class="input-group">
        <input type="hidden" name="action" value="fullsearch">
        <input type="hidden" name="context" value="180">
        <input type="text" autocomplete="off" class="form-control search" placeholder="Search" name="value">
        <span class="dropdown-toggle searchmenu-toggle" data-toggle="dropdown">
            <span class="caret"></span>
        </span>
        <ul class="dropdown-menu searchmenu">
            <li class="active"><a href="#" data-value="title">Title Search</a></li>
            <li class=""><a href="#" data-value="full">Fulltext Search</a></li>
            <li class=""><a href="#" data-value="meta">Meta Search</a></li>
        </ul>
        <div class="input-group-btn">
            <button class="btn btn-primary" name="titlesearch" type="submit">
                <i class="glyphicon glyphicon-search"></i>
            </button>
        </div>
      </div>
    </div>
  </form>""" % url

    def header(self, d, **kw):
        """ Assemble wiki header

        @param d: parameter dictionary
        @rtype: unicode
        @return: page header html
        """
        if self.request.rev:
            if self.request.page.current_rev() != self.request.rev:
                self.rev = '&amp;rev=%d' % self.request.rev
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


            self.navibar(
                d,
                self.username(d),
                self.search_form(d),
                self.editmenu(d)
            ),
            self.breadcrumbs(d),
            self.msg(d),
            u'</div> <!-- /header -->',

            # Post header custom html (not recommended)
            self.emit_custom_html(self.cfg.page_header2),

            # Start of page
            self.startPage(),
        ]
        return u'\n'.join(html)

    def breadcrumbs(self, d, is_footer=False):
        request = self.request
        _ = request.getText
        user = request.user

        if not user.valid:
            return ""

        items = []

        if user.show_page_trail:
            trail = user.getTrail()
            if trail:
                for pagename in trail[::-1]:
                    try:
                        interwiki, page = wikiutil.split_interwiki(pagename)
                        if interwiki != request.cfg.interwikiname and interwiki != 'Self':
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

        val = """  <div class="navbar breadcrumb">
    <ul class="breadcrumb navbar-left">"""
        for i, item in enumerate(items):
            if i == 0:
                val += '\n      <li class="active">%s</li>' % item
            else:
                val += '\n      <li>%s</li>' % item

        val += '\n    </ul>\n    <ul class="breadcrumb navbar-right">'
        actions = getattr(request.cfg, 'bootstrap_actions',
                          self.BREADCRUMB_ACTIONS)
        for i, act in enumerate(actions):
            if act[0].isupper() and not act in self.available_actions:
                continue
            val += '\n      <li><a href="?action=%s%s">%s</a></li>' % (act, self.rev, self._actiontitle(act))

        val += u"""
      <li class="toggleCommentsButton" style="display:none;">
          <a href="#" class="nbcomment" onClick="toggleComments(); return false;">%s</a>
      </li>
        %s
    </ul>
  </div>""" % (_('Comments'), self.actionsmenu(d, is_footer))

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
            val += '<li>%s</li>' % l
        val += '</ul></div>\n'
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

            # Pre footer custom html (not recommended!)
            self.emit_custom_html(self.cfg.page_footer1),

            self.linkedin(),

            # Footer
            u'<div id="footer">',
            self.breadcrumbs(d, True),
            self.pageinfo(page),
            self.footer_string(),
            self.credits(d),
            self.showversion(d, **keywords),
            u'</div>',

            # Post footer custom html
            self.emit_custom_html(self.cfg.page_footer2),

            u'<script src="' + self.cfg.url_prefix_static +
            u'/bootstrap/js/bootstrap.js" type="text/javascript"></script>',
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
