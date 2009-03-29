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

# Extend the _args_re_pattern with template and revision

_arg_rev = r'(,\s*rev=(?P<rev>\d+))?'
_arg_template = r'(,\s*template=(?P<tequot>[\'"])(?P<template>.+?)(?P=tequot))?'

_args_re_pattern = Include._args_re_pattern[:-3] + _arg_rev + _arg_template + ')?$'

_orig_execute = Include.execute

def execute(macro, text):
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

                # Override exists to support including revisions and
                # the editing of nonexisting pages
                def new_exists(self, *args):
                    if self.page_name == inc_name:
                        if rev:
                            self.rev = rev
                        return True

                    return orig_exists(self, *args)

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

                    # Add templates to Include editlinks
                    if (template and self.page_name == inc_name and
                        kw.get('css_class', '') == "include-edit-link"):
                        querystr['template'] = template

                    # Add version information to Include page links
                    elif (rev and self.page_name == inc_name and 
                          kw.get('css_class', '') == "include-page-link"):
                        querystr['action'] = 'recall'
                        querystr['rev'] = str(rev)

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

    return retval
