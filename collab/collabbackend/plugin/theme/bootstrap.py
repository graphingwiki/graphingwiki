# -*- coding: utf-8 -*-
"""
    MoinMoin - Bootstrap theme.

    Based on the Ficora theme (c) by Pasi Kemi 
    (Media Agency Bears: http://www.mediakarhut.fi)

    Modifications by Juhani Eronen <exec@iki.fi>

    @license: GNU GPL <http://www.gnu.org/licenses/gpl.html>
"""
import re

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.widget import html
from MoinMoin.Page import Page
from MoinMoin.theme import modernized as basetheme
from MoinMoin.theme import get_available_actions

from graphingwiki.plugin.macro.LinkedIn import nodes

# FIXME: Caching of relevant portions

BREADCRUMB_ACTIONS = {'print': 'Print View',
                      'raw': 'Raw Text',
                      'info': 'Info',
                      'AttachFile': 'Attachments',
                      'Invite': 'Invite'}

QUICKLINKS_RE = re.compile('<li class="userlink">.+?</li>', re.M)

class Theme(basetheme.Theme):
    name = "bootstrap"
    rev = ''
    available = ''

    def logo(self):
        mylogo = basetheme.Theme.logo(self)
        if not mylogo:
            mylogo = u'<div id="logo"><a href="' + \
                self.request.cfg.page_front_page + '"><img src="' + \
                self.cfg.url_prefix_static + \
                '/bootstrap/img2/cert-fi.png" alt="CERT-FI"></a></div>'
        return mylogo

    def _startnav(self):
        return u"""  <div class="navbar navbar-inverse">
    <div class="navbar-fixed-top navbar-inner">
      <div class="container">
        <button type="button" class="btn btn-navbar" data-toggle="collapse" 
                data-target=".nav-collapse">
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
        </button>
        <ul class="nav">"""

    def _endnav1(self):
        return u"""        </ul> <!-- /nav -->"""

    def _endnav2(self):
        return """        </div> <!-- /collapse -->
      </div> <!-- /container -->
    </div> <!-- /navbar-inner -->
  </div> <!-- /navbar -->"""

    def actionsMenu(self):
        request = self.request
        page = self.request.page
        _ = request.getText
        guiworks = self.guiworks(page)
        editor = request.user.editor_default
        editdisabled = False

        if not 'edit' in request.cfg.actions_excluded:
            if not (page.isWritable() and
                    request.user.may.write(page.page_name)):
                editdisabled = True
                val = """    <li>
          <a title="%s"><i class="icon-edit"></i> </a>""" % \
                    _('Immutable Page')
            elif guiworks and editor == 'gui':
                val = """          <li class="active">
          <a title="%s" href="?action=edit&editor=gui">""" % _('Edit (GUI)')
                val += '<i class="icon-edit"></i></a>'
            else:
                val = """          <li class="active">
          <a title="%s" href="?action=edit">""" % _('Edit')
                val += '<i class="icon-edit"></i> </a>'
        else:
            editdisabled = True

        val += '\n          <li class="active dropdown"><a href="#" '
        val += 'title="%s" class="dropdown-toggle" data-toggle="dropdown">' % \
            _("More Actions:")
        val += '<i class="icon-folder-open"></i></a>'
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
               <i class="icon-wrench" title="%s"></i></a>
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

        content = basetheme.Theme.navibar(self, d)
        content = '\n'.join(content.split('\n')[2:-2])
        content = content.replace('</li>', '</li>\n          ')
        content = '          ' + content.rstrip()

        content = content.replace('current">', 'current active">')
        content = content.replace('>%s<' % self.request.cfg.page_front_page,
                                  'title="%s">' % 
                                  self.request.cfg.page_front_page + 
                                  '<i class="icon-home icon-white"></i><')

        content = content.replace('>%s<' % _("CollabList"),
                                  'title="%s">' % _("CollabList") +
                                  '<i class="icon-globe icon-white"></i><')
        content = content.replace('>%s<' % _("Collab"),
                                  'title="%s">' % _("Collab") +
                                  '<i class="icon-comment icon-white"></i><')

        page_recentchanges = \
            wikiutil.getLocalizedPage(self.request, 'RecentChanges').page_name
        content = content.replace('>%s<' % (page_recentchanges),
                                  'title="%s">' % (page_recentchanges) +
                                  '<i class="icon-list-alt icon-white"></i><')
        page_findpage = \
            wikiutil.getLocalizedPage(self.request, 'FindPage').page_name
        content = content.replace('>%s<' % (page_findpage),
                                  'title="%s">' % (page_findpage) +
                                  '<i class="icon-search icon-white"></i><')
        page_help_contents = \
            wikiutil.getLocalizedPage(self.request, 'HelpContents').page_name
        content = content.replace('">' + page_help_contents,
                                  '" title="%s">' % page_help_contents +
                                  '<i class="icon-question-sign' +
                                  ' icon-white"></i>')

        quicklinks = QUICKLINKS_RE.findall(content)
        content = QUICKLINKS_RE.sub('', content)

        if quicklinks:
            val = """<li class="active dropdown">
            <a href="#" class="dropdown-toggle" data-toggle="dropdown">
               <i class="icon-star-empty" title="%s"></i></a>
            <ul class="dropdown-menu">\n""" % _("Quicklinks")

            for item in quicklinks:
                val += "               %s\n" % (item.replace(' icon-white', ''))

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
                linkpage = \
                    wikiutil.AbsPageName(request.page.page_name, 
                                         wikitail)

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
                out = """            <div class="input-append">
              <div class="btn-group">
                <a class="btn" href="%s"><i class="icon-user"></i> </a>
                <a class="btn dropdown-toggle" data-toggle="dropdown" href="#">
                  <span class="caret"></span></a>
                <ul class="dropdown-menu">
                  <li class="nav-header">%s</li>
"""  % (linkpage, name)
                for url in urls:
                    out += "                  <li>%s</li>\n" % (url)

                out += """                </ul>
              </div>
            </div>"""

            return out

    def search_user_form(self, d):
        _ = self.request.getText
        url = self.request.href(d['page'].page_name)
        return """          <form id="searchform" method="get" action="%s" 
                class="navbar-form pull-right">\n%s
            <input type="hidden" name="action" value="fullsearch">
            <input type="hidden" name="context" value="180">
            <div class="input-append">
              <input id="searchinput" type="text" name="value">
              <div class="btn-group">
                <button alt="title" id="titlesearch" class="btn btn-primary" 
                        value="Titles">%s</button>
                <button class="btn btn-primary dropdown-toggle" 
                        data-toggle="dropdown"><span class="caret"></span>
                </button>
                <ul class="dropdown-menu pull-left">
                  <li><input class="btn btn-link" id="fullsearch" 
                             name="fullsearch" type="submit" value="Text" 
                             alt="%s"></li>
                  <li><input class="btn btn-link" name="metasearch" 
                             type="submit" value="Meta" alt="%s"></li>
                </ul>
              </div>
            </div>""" % (url, self.username(d), _("Title"), 
                         _("Search Full Text"), _("Meta Search"))

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

        self.available = get_available_actions(self.request.cfg, 
                                               self.request.page, 
                                               self.request.user)

        html = [
            # Pre header custom html
            self.emit_custom_html(self.cfg.page_header1),

            # Header
            u'<div id="header">',
            self._startnav(),
            self._wraplink(self.logo()),
            self.navibar(d),
            self.actionsMenu(),
            self._endnav1(),
            '        <div class="nav-collapse collapse">',
            self.search_user_form(d),
            '          </form>',
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

        # Not present when there's no header
        if not self.available:
            self.available = get_available_actions(request.cfg, 
                                                   request.page, 
                                                   request.user)

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

        val = """  <div class="nav-collapse collapse">
    <ul class="breadcrumb">
"""
        if items:
            val += '<span class="divider">/</span></li>\n'.join(
                '      <li>%s' % (item) for item in items)
            val += '</li>'

        actions = getattr(request.cfg, 'bootstrap_actions', 
                          BREADCRUMB_ACTIONS)
        for i, (act, text) in enumerate(actions.iteritems()):
            if act[0].isupper() and not act in self.available:
                continue
            span = (i != 0) and '<span class="divider">/</span>' or ''
            val += '\n      <li style="float: right;">' + \
                '<a href="?action=%s%s">%s</a>%s</li>' % (act, self.rev,
                                                          text, span)
        val += '\n      <li class="toggleCommentsButton"' +\
            ' style="display:none; float: right;">' + \
            '<a href="#" class="nbcomment" onClick="toggleComments();' + \
            'return false;">%s</a><span class="divider">/</span></li>' % \
            _('Comments')
        val +="""
    </ul>
  </div>"""

        return val

    def linkedin(self):
        if not getattr(self.request.cfg, 'bootstrap_linkedin', True):
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
            footer_string = \
            u'  <p class="footertext">CERT-FI<br>PL 313<br>00181 Helsinki'+ \
                '<br>Tel. +358 (0)295 390 230</p>'

        page = d['page']
        html = [
            # End of page
            self.endPage(),

            '<script src="' + self.cfg.url_prefix_static + \
                '/bootstrap/js/jquery.js"></script>',
            '<script src="' + self.cfg.url_prefix_static + \
                '/bootstrap/js/bootstrap.min.js"></script>',

            # Pre footer custom html (not recommended!)
            self.emit_custom_html(self.cfg.page_footer1),

            self.linkedin(),

            # Footer
            self.breadcrumbs(),
            u'<div id="footer">',
            self.pageinfo(page),
            footer_string,
            u'</div>',

            # Post footer custom html
            self.emit_custom_html(self.cfg.page_footer2),
            ]
        return u'\n'.join(html)

    # I needed to copy this monstrosity of a function from theme, just
    # to change the doctype. Maybe do a Moin patch later? Some Moin
    # tests seem to rely on the doctype, though..
    def send_title(self, text, **keywords):
        """
        Output the page header (and title).

        @param text: the title text
        @keyword page: the page instance that called us - using this is more efficient than using pagename..
        @keyword pagename: 'PageName'
        @keyword print_mode: 1 (or 0)
        @keyword editor_mode: 1 (or 0)
        @keyword media: css media type, defaults to 'screen'
        @keyword allow_doubleclick: 1 (or 0)
        @keyword html_head: additional <head> code
        @keyword body_attr: additional <body> attributes
        @keyword body_onload: additional "onload" JavaScript code
        """
        request = self.request
        _ = request.getText
        rev = request.rev

        if keywords.has_key('page'):
            page = keywords['page']
            pagename = page.page_name
        else:
            pagename = keywords.get('pagename', '')
            page = Page(request, pagename)
        if keywords.get('msg', ''):
            raise DeprecationWarning("Using send_page(msg=) is deprecated! Use theme.add_msg() instead!")
        scriptname = request.script_root

        # get name of system pages
        page_front_page = wikiutil.getFrontPage(request).page_name
        page_help_contents = wikiutil.getLocalizedPage(request, 'HelpContents').page_name
        page_title_index = wikiutil.getLocalizedPage(request, 'TitleIndex').page_name
        page_site_navigation = wikiutil.getLocalizedPage(request, 'SiteNavigation').page_name
        page_word_index = wikiutil.getLocalizedPage(request, 'WordIndex').page_name
        page_help_formatting = wikiutil.getLocalizedPage(request, 'HelpOnFormatting').page_name
        page_find_page = wikiutil.getLocalizedPage(request, 'FindPage').page_name
        home_page = wikiutil.getInterwikiHomePage(request) # sorry theme API change!!! Either None or tuple (wikiname,pagename) now.
        page_parent_page = getattr(page.getParentPage(), 'page_name', None)

        # set content_type, including charset, so web server doesn't touch it:
        request.content_type = "text/html; charset=%s" % (config.charset, )

        # Prepare the HTML <head> element
        user_head = [request.cfg.html_head]

        # include charset information - needed for moin_dump or any other case
        # when reading the html without a web server
        user_head.append('''<meta http-equiv="Content-Type" content="%s;charset=%s">\n''' % (page.output_mimetype, page.output_charset))

        meta_keywords = request.getPragma('keywords')
        meta_desc = request.getPragma('description')
        if meta_keywords:
            user_head.append('<meta name="keywords" content="%s">\n' % wikiutil.escape(meta_keywords, 1))
        if meta_desc:
            user_head.append('<meta name="description" content="%s">\n' % wikiutil.escape(meta_desc, 1))

        #  add meta statement if user has doubleclick on edit turned on or it is default
        if (pagename and keywords.get('allow_doubleclick', 0) and
            not keywords.get('print_mode', 0) and
            request.user.edit_on_doubleclick):
            if request.user.may.write(pagename): # separating this gains speed
                user_head.append('<meta name="edit_on_doubleclick" content="%s">\n' % (request.script_root or '/'))

        # search engine precautions / optimization:
        # if it is an action or edit/search, send query headers (noindex,nofollow):
        if request.query_string:
            user_head.append(request.cfg.html_head_queries)
        elif request.method == 'POST':
            user_head.append(request.cfg.html_head_posts)
        # we don't want to have BadContent stuff indexed:
        elif pagename in ['BadContent', 'LocalBadContent', ]:
            user_head.append(request.cfg.html_head_posts)
        # if it is a special page, index it and follow the links - we do it
        # for the original, English pages as well as for (the possibly
        # modified) frontpage:
        elif pagename in [page_front_page, request.cfg.page_front_page,
                          page_title_index, 'TitleIndex',
                          page_find_page, 'FindPage',
                          page_site_navigation, 'SiteNavigation',
                          'RecentChanges', ]:
            user_head.append(request.cfg.html_head_index)
        # if it is a normal page, index it, but do not follow the links, because
        # there are a lot of illegal links (like actions) or duplicates:
        else:
            user_head.append(request.cfg.html_head_normal)

        if 'pi_refresh' in keywords and keywords['pi_refresh']:
            user_head.append('<meta http-equiv="refresh" content="%d;URL=%s">' % keywords['pi_refresh'])

        # output buffering increases latency but increases throughput as well
        output = []
        # later: <html xmlns=\"http://www.w3.org/1999/xhtml\">
        output.append("""\
<!DOCTYPE html>
<html>
<head>
%s
%s
%s
""" % (
            ''.join(user_head),
            self.html_head({
                'page': page,
                'title': text,
                'sitename': request.cfg.html_pagetitle or request.cfg.sitename,
                'print_mode': keywords.get('print_mode', False),
                'media': keywords.get('media', 'screen'),
            }),
            keywords.get('html_head', ''),
        ))

        # Links
        output.append('<link rel="Start" href="%s">\n' % request.href(page_front_page))
        if pagename:
            output.append('<link rel="Alternate" title="%s" href="%s">\n' % (
                    _('Wiki Markup'), request.href(pagename, action='raw')))
            output.append('<link rel="Alternate" media="print" title="%s" href="%s">\n' % (
                    _('Print View'), request.href(pagename, action='print')))

            # !!! currently disabled due to Mozilla link prefetching, see
            # http://www.mozilla.org/projects/netlib/Link_Prefetching_FAQ.html
            #~ all_pages = request.getPageList()
            #~ if all_pages:
            #~     try:
            #~         pos = all_pages.index(pagename)
            #~     except ValueError:
            #~         # this shopuld never happend in theory, but let's be sure
            #~         pass
            #~     else:
            #~         request.write('<link rel="First" href="%s/%s">\n' % (request.script_root, quoteWikinameURL(all_pages[0]))
            #~         if pos > 0:
            #~             request.write('<link rel="Previous" href="%s/%s">\n' % (request.script_root, quoteWikinameURL(all_pages[pos-1])))
            #~         if pos+1 < len(all_pages):
            #~             request.write('<link rel="Next" href="%s/%s">\n' % (request.script_root, quoteWikinameURL(all_pages[pos+1])))
            #~         request.write('<link rel="Last" href="%s/%s">\n' % (request.script_root, quoteWikinameURL(all_pages[-1])))

            if page_parent_page:
                output.append('<link rel="Up" href="%s">\n' % request.href(page_parent_page))

        # write buffer because we call AttachFile
        request.write(''.join(output))
        output = []

        # XXX maybe this should be removed completely. moin emits all attachments as <link rel="Appendix" ...>
        # and it is at least questionable if this fits into the original intent of rel="Appendix".
        if pagename and request.user.may.read(pagename):
            from MoinMoin.action import AttachFile
            AttachFile.send_link_rel(request, pagename)

        output.extend([
            '<link rel="Search" href="%s">\n' % request.href(page_find_page),
            '<link rel="Index" href="%s">\n' % request.href(page_title_index),
            '<link rel="Glossary" href="%s">\n' % request.href(page_word_index),
            '<link rel="Help" href="%s">\n' % request.href(page_help_formatting),
                      ])

        output.append("</head>\n")
        request.write(''.join(output))
        output = []

        # start the <body>
        bodyattr = []
        if keywords.has_key('body_attr'):
            bodyattr.append(' ')
            bodyattr.append(keywords['body_attr'])

        # Set body to the user interface language and direction
        bodyattr.append(' %s' % self.ui_lang_attr())

        body_onload = keywords.get('body_onload', '')
        if body_onload:
            bodyattr.append(''' onload="%s"''' % body_onload)
        output.append('\n<body%s>\n' % ''.join(bodyattr))

        # Output -----------------------------------------------------------

        # If in print mode, start page div and emit the title
        if keywords.get('print_mode', 0):
            d = {
                'title_text': text,
                'page': page,
                'page_name': pagename or '',
                'rev': rev,
            }
            request.themedict = d
            output.append(self.startPage())
            output.append(self.interwiki(d))
            output.append(self.title(d))

        # In standard mode, emit theme.header
        else:
            exists = pagename and page.exists(includeDeleted=True)
            # prepare dict for theme code:
            d = {
                'theme': self.name,
                'script_name': scriptname,
                'title_text': text,
                'logo_string': request.cfg.logo_string,
                'site_name': request.cfg.sitename,
                'page': page,
                'rev': rev,
                'pagesize': pagename and page.size() or 0,
                # exists checked to avoid creation of empty edit-log for non-existing pages
                'last_edit_info': exists and page.lastEditInfo() or '',
                'page_name': pagename or '',
                'page_find_page': page_find_page,
                'page_front_page': page_front_page,
                'home_page': home_page,
                'page_help_contents': page_help_contents,
                'page_help_formatting': page_help_formatting,
                'page_parent_page': page_parent_page,
                'page_title_index': page_title_index,
                'page_word_index': page_word_index,
                'user_name': request.user.name,
                'user_valid': request.user.valid,
                'msg': self._status,
                'trail': keywords.get('trail', None),
                # Discontinued keys, keep for a while for 3rd party theme developers
                'titlesearch': 'use self.searchform(d)',
                'textsearch': 'use self.searchform(d)',
                'navibar': ['use self.navibar(d)'],
                'available_actions': ['use self.request.availableActions(page)'],
            }

            # add quoted versions of pagenames
            newdict = {}
            for key in d:
                if key.startswith('page_'):
                    if not d[key] is None:
                        newdict['q_'+key] = wikiutil.quoteWikinameURL(d[key])
                    else:
                        newdict['q_'+key] = None
            d.update(newdict)
            request.themedict = d

            # now call the theming code to do the rendering
            if keywords.get('editor_mode', 0):
                output.append(self.editorheader(d))
            else:
                output.append(self.header(d))

        # emit it
        request.write(''.join(output))
        output = []
        self._send_title_called = True

def execute(request):
    """
    Generate and return a theme object

    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)

