# -*- coding: utf-8 -*-"
"""
    Include macro to MoinMoin/Graphingwiki
     - Extends the original Include macro

    New features:
     * Including nonexisting pages with an editlink
     * Specifying a template for editing, eg.
     <<Include(Case183/nonexisting,,,editlink,template="HelpTemplate")>>
     * Specifying a revision for included pages, eg.
     <<Include(FrontPage,,,editlink,rev=1)>>

    @copyright: 2009 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import re

from MoinMoin import wikiutil
from MoinMoin.Page import Page

import MoinMoin.macro.Include as Include

from graphingwiki import actionname
from graphingwiki.util import form_writer as wr

Dependencies = ["time"]
generates_headings = True

# Extend the _args_re_pattern with template and revision

_arg_rev = r'(,\s*rev=(?P<rev>\d+))?'
_arg_template = r'(,\s*template=(?P<tequot>[\'"])(?P<template>.+?)(?P=tequot))?'

_args_re_pattern = Include._args_re_pattern[:-3] + _arg_rev + _arg_template + ')?$'

_orig_execute = Include.execute

def execute(macro, text):
    _ = macro.request.getText

    # Retain original values
    orig_request_page = macro.request.page
    orig_exists = Page.exists
    orig_link_to = Page.link_to
    orig__init__ = Page.__init__

    # Try-finally construct over override functions so that modified
    # copies of Page are not littered with persistent req types
    try:
        args_re=re.compile(_args_re_pattern)
        args = text and args_re.match(text)

        # Start overrides if args match
        if text and args:
            inc_name = wikiutil.AbsPageName(macro.formatter.page.page_name, 
                                            args.group('name'))

            # Additions that only account for includes of specific pages
            if not inc_name.startswith('^'):
                rev = args.group('rev')
                try:
                    rev = int(rev)
                except:
                    rev = None

                # Remove from/to regexes from nonexisting pages, so
                # that nasty error messages are suppressed
                if not Page(macro.request, inc_name).exists():
                    text = re.sub(Include._arg_to, '', text)
                    text = re.sub(Include._arg_from, '', text)

                # Override exists to support including revisions and
                # the editing of nonexisting pages
                def new_exists(self, **kw):
                    exists = orig_exists(self, **kw)
                    if self.formatter:
                        # Fix a Moin bug in handling attachments: If
                        # the formatter has page defined, it will
                        # handle attachment links relative to the
                        # including page, not the included page. For
                        # some reason, the formatter has not always
                        # been initialised, leading to crashes, so
                        # check its existence first.
                        self.formatter.request.page = self

                    if self.page_name == inc_name:
                        if rev:
                            self.rev = rev

                        # Mark pages that do not really exist
                        if not exists:
                            self._macro_Include_nonexisting = True
                            exists = True

                    return exists

                Page.exists = new_exists

                if rev:
                    def new__init__(self, request, page_name, **kw):
                        kw['rev'] = rev
                        return orig__init__(self, request, page_name, **kw)

                    Page.__init__ = new__init__

                # Override link_to to support added templates
                template = args.group('template')
                def new_link_to(self, request, text=None, 
                                querystr=dict(), anchor=None, **kw):
                    
                    if self.page_name == inc_name:
                        # Let's see if we've a link to nonexisting page
                        if getattr(self, '_macro_Include_nonexisting', False):
                            # Modify editlinks with template selection
                            if kw.get('css_class', '') == "include-edit-link":
                                if template:
                                    querystr['template'] = template
                                    text = '[%s]' % _('create') 
                                else:
                                    orig_page = macro.request.page.page_name
                                    msg = wr('<form method="GET" action="%s">', 
                                             actionname(request, orig_page))
                                    msg += wr('<select name="template">')
                                    msg += wr('<option value="">%s</option>', 
                                              _("No template"))

                                    # Get list of template pages readable by current user
                                    filterfn = request.cfg.cache.page_template_regexact.search
                                    templates = request.rootpage.getPageList(filter=filterfn)
                                    for i in templates:
                                        msg += wr('<option value="%s">%s</option>', i, i)

                                    msg += '<input type="hidden" name="action" value="newpage"'
                                    msg += wr('<input type="hidden" name="pagename" value="%s"', inc_name)
                                    msg += wr('<input type="hidden" name="backto" value="%s"', querystr['backto'])
                                    msg += wr('<input type="submit" value="%s">', _('create'))
                                    msg += wr('</select></form>')

                                    return msg

                            # Do not give pagelinks to nonexisting pages
                            if kw.get('css_class', '') == "include-page-link":
                                return text

                        # Add revision information to rev links
                        elif rev:
                            if kw.get('css_class', '') == "include-page-link":
                                querystr['action'] = 'recall'
                                querystr['rev'] = str(rev)
                                text = "%s revision %d]" % (text[:-1], rev)
                            elif kw.get('css_class', '') == "include-edit-link":
                                text = '[%s]' % _("edit current version")

                    return orig_link_to(self, request, text, 
                                        querystr, anchor, **kw)

                Page.link_to = new_link_to

        # Call the original Include-macro
        retval = _orig_execute(macro, text, args_re=args_re)
    finally:
        # Cleanup and return
        Page.exists = orig_exists
        Page.link_to = orig_link_to
        Page.__init__ = orig__init__

    # request.page might have been changed in page.new_exists, so it
    # needs to be returned to its original value
    macro.request.page = orig_request_page

    return retval
