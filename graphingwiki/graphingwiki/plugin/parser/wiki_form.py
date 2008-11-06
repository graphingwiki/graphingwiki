# -*- coding: utf-8 -*-"
"""
    wiki form parser to MoinMoin
     - Modifies definition list behaviour to make them form inputs.
       Tries to leave other behaviour intact as much as possible.

    @copyright: 2008 by Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import cgi
 
from MoinMoin.parser.text_moin_wiki import Parser as wikiParser
from graphingwiki.patterns import form_escape

Dependencies = []

class Parser(wikiParser):
    def __init__(self, raw, request, **kw):
        self.pagename = request.page.page_name
        self.curdef = ''
        self.prevdef = ''

        # Cannot use super as the Moin classes are old-style
        apply(wikiParser.__init__, (self, raw, request), kw)

    def __nonempty_groups(self, groups):
        return [(x, y) for x, y in groups.iteritems() if y]
    
    def _line_anchordef(self):
        if self.in_dd:
            return ''

        return wikiParser._line_anchordef(self)

    def replace(self, match, inhibit_p=False):
        if self.in_dd:
            # We probably don't want new paragraphs in dd:s as
            # paragraph html code might litter forms
            self.inhibit_p = True

        result = apply(wikiParser.replace, (self, match, self.inhibit_p))

        if self.in_dd:
            # Some matches disable inhibit_p, and if there are multiple
            # matches in one row, pre-matches might emit <p class=862
            self.inhibit_p = True

        return result

    def _close_item(self, result):
        if self.in_dd:
            # When closing dd:s, start again with the paragraphs
            self.inhibit_p = 0
            result.append('">\n')
            apply(wikiParser._close_item, (self, result))
            self.prevdef = self.curdef
            self.curdef = ''

        apply(wikiParser._close_item, (self, result))
        
    def _dl_repl(self, match, groups):
        dt = match[1:-3].lstrip(' ')
        if dt != "":
            self.curdef=dt
        else:
            self.curdef=self.prevdef
        dt = self.curdef

        return apply(wikiParser._dl_repl, (self, match, groups)) + \
               '\n<input class="metavalue" type="text" name="' + \
               form_escape('%s?%s' % (self.pagename, dt)) + '" value="'

    def _url_repl(self, word, groups):
        if self.in_dd:
            target = groups.get('url_target', '')
            return target

        return apply(wikiParser._url_repl, (self, word, groups))

    _url_target_repl = _url_repl
    _url_scheme_repl = _url_repl

    def _word_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._word_repl, (self, word, groups))

    def _link_repl(self, word, groups):
        if self.in_dd:
            raw = groups.get('link', '')
            return raw

        return apply(wikiParser._link_repl, (self, word, groups))
        
    _link_target_repl = _link_repl
    _link_desc_repl = _link_repl
    _link_params_repl = _link_repl

    def _transclude_repl(self, word, groups):
        if self.in_dd:
            raw = groups.get('transclude', '')
            return raw

        return apply(wikiParser._transclude_repl, (self, word, groups))
    _transclude_target_repl = _transclude_repl
    _transclude_desc_repl = _transclude_repl
    _transclude_params_repl = _transclude_repl

    def _notword_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._notword_repl, (self, word, groups))

    def _interwiki_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._interwiki_repl, (self, word, groups))

    def _macro_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._macro_repl, (self, word, groups))

    def attachment(self, url_and_text, **kw):
        if self.in_dd:
            return word

        return apply(wikiParser.attachment, (self, url_and_text), kw)

    def _wikiname_bracket_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._wikiname_bracket_repl, (self, word, groups))

    def _url_bracket_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._url_bracket_repl, (self, word, groups))

    def _email_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._email_repl, (self, word, groups))

    def _u_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._u_repl, (self, word, groups))

    def _strike_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._strike_repl, (self, word, groups))

    def _small_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._small_repl, (self, word, groups))

    def _big_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._big_repl, (self, word, groups))

    def _pre_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._pre_repl, (self, word, groups))

    def _smiley_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._smiley_repl, (self, word, groups))

    def _emph_ibb_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._emph_ibb_repl, (self, word, groups))

    def _emph_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._emph_repl, (self, word, groups))

    def _emph_ibi_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._emph_ibi_repl, (self, word, groups))

    def _emph_ib_or_bi_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._emph_ib_or_bi_repl, (self, word, groups))

    def _sup_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._sup_repl, (self, word, groups))

    def _sub_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._sub_repl, (self, word, groups))

    def _processor_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._processor_repl, (self, word, groups))

    def _ent_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._ent_repl, (self, word, groups))

    def _ent_numeric_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._ent_numeric_repl, (self, word, groups))

    def _ent_symbolic_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._ent_symbolic_repl, (self, word, groups))

    def _remark_repl(self, word, groups):
        if self.in_dd:
            return word

        return apply(wikiParser._remark_repl, (self, word, groups))

