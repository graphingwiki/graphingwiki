# -*- coding: utf-8 -*-

from MoinMoin.formatter import FormatterBase

class Formatter(FormatterBase):
    """ Collect text (metadata text values) and format nothing :-) """
    def __init__(self, request, **kw):
        self.textstorage = list()
        FormatterBase.__init__(self, request, **kw)
    
    # Whenever collecting text, remind the parser about having done so
    def text(self, *args, **kw):
        ## FIXME? for now, only accept entries on the same line for 
        ## meta value to minimise surprise
        if self.request.page.parser.lineno == self.request.page.parser.ddline:
            self.request.page.parser.new_item = False
            self.textstorage.append(args[0])

        return self.null()
        
    nowikiword = text

    def null(self, *args, **kw):
        return ''

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
    definition_term = definition_list = definition_desc = null
    pagelink = macro = null

