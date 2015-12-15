# -*- coding: utf-8 -*-"
"""
    wiki form parser to MoinMoin
     - Modifies definition list behaviour to make them HTML form
       inputs on the output page. Tries to leave other behaviour
       intact as much as possible.

    @copyright: 2008-2010 by Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from string import rsplit

from MoinMoin import wikiutil
from MoinMoin.parser.text_moin_wiki import Parser as wikiParser

from graphingwiki.util import category_regex, form_escape
from graphingwiki import SEPARATOR

Dependencies = []

class Parser(wikiParser):
    def __init__(self, raw, request, **kw):
        self.pagename = request.page.page_name
        self.curdef = ''
        self.prevdef = ''
        self.ddline = 0

        # Cannot use super as the Moin classes are old-style
        apply(wikiParser.__init__, (self, raw, request), kw)
        self.cat_re=category_regex(request)

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

    ## FIXME? for now, only accept entries on the same line for 
    ## meta value to minimise surprise
    #
    # Modified indent_repl to exclude dd, because we do not want to
    # include indents to dd:s. In the example cases
    #
    #  a:: i
    #  unrelated line
    # 
    #  * list
    #  unrelated line
    #
    # the unrelated line would be interpreted by moin as being a part
    # of the list (dd, ul) above them, i.e. the form value for the key
    # 'a' would be "i unrelated line" instead of "i". This is not what
    # we currently want.
    def _indent_repl(self, match, groups):
        result = []
        if not (self.in_li):
            self._close_item(result)
            self.in_li = 1
            css_class = None
            if self.line_was_empty and not self.first_list_item:
                css_class = 'gap'
            result.append(self.formatter.listitem(1, css_class=css_class, 
                                                  style="list-style-type:none"))
        return ''.join(result)

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
        self.ddline = self.lineno

        return apply(wikiParser._dl_repl, (self, match, groups)) + \
               '\n<input class="metavalue" type="text" name="' + \
               form_escape('%s%s%s' % (self.pagename, SEPARATOR, dt)) + \
               '" value="'

    def __real_val(self, word):
        if not word.strip():
            return ''

        if self.in_dd:
        ## FIXME? for now, only accept entries on the same line for 
        ## meta value to minimise surprise
            if not self.ddline == self.lineno:
                return ''

        return word

    def _url_repl(self, word, groups):
        if self.in_dd:
            target = groups.get('url_target', '')
            return self.__real_val(target)

        return apply(wikiParser._url_repl, (self, word, groups))

    _url_target_repl = _url_repl
    _url_scheme_repl = _url_repl

    def _word_repl(self, word, groups):
        if self.in_dd:
            name = groups.get('word_name')
            current_page = self.formatter.page.page_name
            abs_name = wikiutil.AbsPageName(current_page, name)
            if abs_name == current_page:
                return self.__real_val(abs_name)
            else:
                # handle anchors
                try:
                    abs_name, anchor = rsplit(abs_name, "#", 1)
                except ValueError:
                    anchor = ""
                if self.cat_re.match(abs_name):
                    return self.__real_val(abs_name)

                else:
                    if not anchor:
                        wholename = abs_name
                    else:
                        wholename = "%s#%s" % (abs_name, anchor)

                    return self.__real_val(wholename)

        return apply(wikiParser._word_repl, (self, word, groups))

    _word_bang_repl = _word_repl
    _word_name_repl = _word_repl
    _word_anchor_repl = _word_repl

    def _link_repl(self, word, groups):
        if self.in_dd:
            raw = groups.get('link', '')
            return self.__real_val(raw)

        return apply(wikiParser._link_repl, (self, word, groups))
        
    _link_target_repl = _link_repl
    _link_desc_repl = _link_repl
    _link_params_repl = _link_repl

    def _transclude_repl(self, word, groups):
        if self.in_dd:
            raw = groups.get('transclude', '')
            return self.__real_val(raw)

        return apply(wikiParser._transclude_repl, (self, word, groups))
    _transclude_target_repl = _transclude_repl
    _transclude_desc_repl = _transclude_repl
    _transclude_params_repl = _transclude_repl

    def _interwiki_repl(self, word, groups):
        if self.in_dd:
            wiki = groups.get('interwiki_wiki')
            page = groups.get('interwiki_page')
            wikipage = "%s:%s" % (wiki, page)
            return self.__real_val(wikipage)

        return apply(wikiParser._interwiki_repl, (self, word, groups))
    _interwiki_wiki_repl = _interwiki_repl
    _interwiki_page_repl = _interwiki_repl

    def _macro_repl(self, word, groups):
        if self.in_dd:
            macro = groups.get('macro')
            return self.__real_val(macro)

        return apply(wikiParser._macro_repl, (self, word, groups))
    _macro_name_repl = _macro_repl
    _macro_args_repl = _macro_repl

    def attachment(self, url_and_text, **kw):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser.attachment, (self, url_and_text), kw)

    def _email_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._email_repl, (self, word, groups))

    def _u_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._u_repl, (self, word, groups))

    def _strike_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._strike_repl, (self, word, groups))
    _strike_on_repl = _strike_repl
    _strike_off_repl = _strike_repl

    def _small_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._small_repl, (self, word, groups))
    _small_on_repl = _small_repl
    _small_off_repl = _small_repl

    def _big_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._big_repl, (self, word, groups))
    _big_on_repl = _big_repl
    _big_off_repl = _big_repl

    def _smiley_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._smiley_repl, (self, word, groups))

    def _tt_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._tt_repl, (self, word, groups))
    _tt_text_repl = _tt_repl

    def _tt_bt_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._tt_bt_repl, (self, word, groups))
    _tt_bt_text_repl = _tt_bt_repl

    def _emph_ibb_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._emph_ibb_repl, (self, word, groups))

    def _emph_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._emph_repl, (self, word, groups))

    def _emph_ibi_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._emph_ibi_repl, (self, word, groups))

    def _emph_ib_or_bi_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._emph_ib_or_bi_repl, (self, word, groups))

    def _sup_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._sup_repl, (self, word, groups))
    _sup_text_repl = _sup_repl

    def _sub_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._sub_repl, (self, word, groups))
    _sub_text_repl = _sup_repl

    def _entity_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._entity_repl, (self, word, groups))

    def _sgml_entity_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._sgml_entity_repl, (self, word, groups))

    def _remark_repl(self, word, groups):
        if self.in_dd:
            return self.__real_val(word)

        return apply(wikiParser._remark_repl, (self, word, groups))
    _remark_on_repl = _remark_repl
    _remark_off_repl = _remark_repl

    def _parser_repl(self, word, groups):
        parser_name = groups.get('parser_name', None)
        parser_line = word = groups.get('parser_line', u'')
        self.parser_lines = []

        self.in_pre = 'search_parser'

        # If there's a parser on the begin of the parser line, stop
        # searching for parsers. If wiki parser, register this class
        # as the handler instead of text_moin_wiki
        if parser_name:
            if parser_name == 'wiki':
                self.in_pre = 'found_parser'
                self.parser_name = 'wiki_form'
                if word:
                    self.parser_lines.append(word)
                    return ''

        return apply(wikiParser._parser_repl, (self, word, groups))

    _parser_unique_repl = _parser_repl
    _parser_line_repl = _parser_repl
    _parser_name_repl = _parser_repl
    _parser_args_repl = _parser_repl
    _parser_nothing_repl = _parser_repl

    # Catch the wiki parser within the parsed content, register this
    # class as its handler instead of text_moin_wiki
    def _parser_content(self, line):
        if self.in_pre == 'search_parser' and line.strip():
            if line.strip().startswith("#!"):
                parser_name = line.strip()[2:].split()[0]
                if parser_name == 'wiki':
                    self.in_pre = 'found_parser'
                    self.parser_name = 'wiki_form'

        return apply(wikiParser._parser_content, (self, line))
