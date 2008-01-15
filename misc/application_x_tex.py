# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - Special formatting to show wiki markup as LaTeX

    @copyright: 2005 by Juhani Eronen <exec@ee.oulu.fi>
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.formatter.base import FormatterBase
from MoinMoin import wikiutil, i18n, config
from MoinMoin.Page import Page

class Formatter(FormatterBase):
    """
    Get url values, and nothing else
    """
    def __init__(self, request, **kw):
        apply(FormatterBase.__init__, (self, request), kw)
        self._did_para = 0
        self._url = None
        self._text = None
        self._in_heading = 0
        self._in_list = 0
        self._in_link = 0

    def null(self, *args, **kw):
        return ''

    # All these must be overriden here because they raise
    # NotImplementedError!@#! or return html?! in the base class.
    set_highlight_re = null
    url = null
    image = null
    smiley = null
    text = null
    strong = null
    emphasis = null
    underline = null
    highlight = null
    sup = null
    sub = null
    code = null
    preformatted = null
    small = null
    big = null
    code_area = null
    code_line = null
    code_token = null
    linebreak = null
    paragraph = null
    rule = null
    icon = null
    number_list = null
    bullet_list = null
    listitem = null
    definition_list = null
    definition_term = null
    definition_desc = null
    heading = null
    table = null
    table_row = null
    table_cell = null

    # These are private additions to formatter added by text_html, and
    # some code use or might use them.
    open = null
    close = null
    formatAttributes = null

    def startDocument(self, pagename):
        return u"\\documentclass[times, 10pt,twocolumn]{article}\n" + \
               u"\\usepackage{epsfig}\n\\usepackage{times}\n" +\
               u"\\usepackage{url}\n\\begin{document}\n"

    def endDocument(self):
        return u"\n\\end{document}\n"
    
    def text(self, text):
        self._did_para = 0

        # Text to headings etc.
        if self._text is not None:
            self._text.append(text)

        # Disable double printing of headings
        if self._in_heading:
            return ""

        # Remove unnecessary spaces from listitems
        # FIXME: a mess with links and such, better solution needed
        if self._in_list:
            if not self._in_link:
                return "x" + text.strip()

        # Default case
        return text

    def paragraph(self, on):
        FormatterBase.paragraph(self, on)
        if self._did_para:
            on = 0
        return [u'\n', u''][not on]

    # FIXME: this is obviously wrong, subsubsubsubsections hardly exist
    def heading(self, on, depth, **kw):
        if on:
            self._in_heading = 1
            self._text = []
            return '\n'
        else:
            self._in_heading = 0
            result = "\\" + u'sub' * (depth-1) + 'section{' + \
                     "".join(self._text) + "}\n\n"
            self._text = None
            return result

    # FIXME: just to make it work
    def pagelink(self, on, pagename='', page=None, **kw):
        if on:
            self._in_link = 1
        else:
            self._in_link = 0
        return str(self._in_link)

    def bullet_list(self, on):
        if on:
            # Slight cosmetic for nested lists
            if self._in_list:
                self._in_list = self._in_list + 1
                return u" " * (self._in_list - 1) + u"\\begin{itemize}\n"

            self._in_list = 1
            return [u'\n', u'\n\n'][not self._did_para] + \
                   u"\\begin{itemize}\n"
        else:
            self._in_list = self._in_list - 1
            if not self._did_para:
                self._did_para = 1
            return u" " * (self._in_list) + u"\\end{itemize}" + \
                   [u'', u'\n'][self._did_para]

    def listitem(self, on, **kw):
        if on:
            # No enter after this text, please
            self._did_para = 1
            return u" " * (self._in_list - 1) + u"\\item{"
        else:
            return u'}\n'
