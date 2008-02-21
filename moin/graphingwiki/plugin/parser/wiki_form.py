# -*- coding: utf-8 -*-"
"""
    wiki form parser to MoinMoin
     - Modifies definition list behaviour to make them form inputs.
       Tries to leave other behaviour intact as much as possible.

    @copyright: 2008 by Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import cgi
 
from MoinMoin.parser.wiki import Parser as wikiParser

def htmlquote(s):
    return cgi.escape(s, 1)

Dependencies = []

class Parser(wikiParser):
    def __init__(self, raw, request, **kw):
        self.pagename = request.page.page_name

        apply(wikiParser.__init__, (self, raw, request), kw)
    
    def _line_anchordef(self):
        if self.in_dd:
            return ''

        return wikiParser._line_anchordef(self)

    def replace(self, match):
        if self.in_dd:
            # We probably don't want new paragraphs in dd:s as
            # paragraph html code might litter forms
            self.inhibit_p = 1

        result = apply(wikiParser.replace, (self, match))

        if self.in_dd:
            # Some matches disable inhibit_p, and if there are multiple
            # matches in one row, pre-matches might emit <p class=862
            self.inhibit_p = 1

        return result

    def _close_item(self, result):
        if self.in_dd:
            # When closing dd:s, start again with the paragraphs
            self.inhibit_p = 0
            result.append('">\n')
            apply(wikiParser._close_item, (self, result))

        apply(wikiParser._close_item, (self, result))
        
    def _dl_repl(self, match):
        dt = match[1:-3].lstrip(' ')

        return apply(wikiParser._dl_repl, (self, match)) + \
               '\n<input class="metavalue" type="text" name="' + \
               htmlquote('%s!%s' % (self.pagename, dt)) + '" value="'

    def _url_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._url_repl, (self, word))

    def _word_repl(self, word, text=None):
        if self.in_dd:
            return word

        return apply(wikiParser._word_repl, (self, word, text))

    def _notword_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._notword_repl, (self, word))

    def _interwiki_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._interwiki_repl, (self, word))

    def _macro_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._macro_repl, (self, word))

    def attachment(self, url_and_text, **kw):
        if self.in_dd:
            return word

        return apply(wikiParser.attachment, (self, url_and_text), kw)

    def _wikiname_bracket_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._wikiname_bracket_repl, (self, word))

    def _url_bracket_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._url_bracket_repl, (self, word))

    def _email_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._email_repl, (self, word))

    def _u_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._u_repl, (self, word))

    def _strike_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._strike_repl, (self, word))

    def _small_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._small_repl, (self, word))

    def _big_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._big_repl, (self, word))

    def _pre_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._pre_repl, (self, word))

    def _smiley_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._smiley_repl, (self, word))

    def _emph_ibb_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._emph_ibb_repl, (self, word))

    def _emph_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._emph_repl, (self, word))

    def _emph_ibi_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._emph_ibi_repl, (self, word))

    def _emph_ib_or_bi_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._emph_ib_or_bi_repl, (self, word))

    def _sup_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._sup_repl, (self, word))

    def _sub_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._sub_repl, (self, word))

    def _processor_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser.processor_repl, (self, word))

    def _ent_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._ent_repl, (self, word))

    def _ent_numeric_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._ent_numeric_repl, (self, word))

    def _ent_symbolic_repl(self, word):
        if self.in_dd:
            return word

        return apply(wikiParser._ent_symbolic_repl, (self, word))
