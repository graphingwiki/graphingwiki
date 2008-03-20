# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - pagelinks Formatter

    @copyright: 2005 Nir Soffer <nirs@freeshell.org>
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.formatter import FormatterBase

class Formatter(FormatterBase):
    """ Collect pagelinks and format nothing :-) """
    def __init__(self, request, **kw):
        self.linkstorage = None
        self.textstorage = None
        self.definitions = [] 
        self.curdef = None
        FormatterBase.__init__(self, request, **kw)
    
    def pagelink(self, on, pagename='', page=None, **kw):
        print repr(pagename)
        if on and not self.curdef:
            self.pagelinks.append(pagename)
        self.linkstorage = pagename
        return self.null()

    def definition_desc(self, *args, **kw):
        if self.curdef:
            if self.linkstorage:
                self.definitions.append((self.curdef, "link", self.linkstorage.strip()))
            elif self.textstorage:
                self.definitions.append((self.curdef, "text", self.textstorage.strip()))
        print repr(self.definitions)
        return self.null()

    def text(self, *args, **kw):
        self.textstorage = args[0]
        return self.null()
        
    def null(self, *args, **kw):
        return ''

    def definition_term(self, *args, **kw):
        print "DT:",repr(args), kw
        return self.null()

    def definition_list(self, *args, **kw):
        print "DL:",repr(args), kw
        return self.null()
                
    # All these must be overriden here because they raise
    # NotImplementedError!@#! or return html?! in the base class.
    set_highlight_re = rawHTML = url = image = smiley = null
    strong = emphasis = underline = highlight = sup = sub = strike = null
    code = preformatted = small = big = code_area = code_line = null
    code_token = linebreak = paragraph = rule = icon = null
    number_list = bullet_list = listitem = null
    heading = table = null
    table_row = table_cell = attachment_link = attachment_image = attachment_drawing = null
    transclusion = transclusion_param = null
#    definition_term = definition_list = null

