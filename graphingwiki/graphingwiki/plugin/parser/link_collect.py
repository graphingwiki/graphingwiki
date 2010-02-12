# -*- coding: utf-8 -*-"
"""
     Link harvesting "parser"
"""
import cgi, re
 
from MoinMoin.parser.text_moin_wiki import Parser as WikiParser
from MoinMoin import macro, wikiutil
from string import rsplit

from graphingwiki.util import resolve_iw_url, category_regex
from wiki_form import Parser as listParser

Dependencies = []

class Parser(WikiParser):
    def __init__(self, raw, request, **kw):
        self.pagename = request.page.page_name
        self.definitions = {} 
        self.curdef = ''
        self.prevdef = ''
        self.ddline = 0
        
        # Cannot use super as the Moin classes are old-style
        apply(WikiParser.__init__, (self, raw, request), kw)
        
        self.currentitems = []
        self.in_dd = 0
        self.cat_re=category_regex(request)

    def __add_textmeta(self, word, groups):
        val = ''

        if self.in_dd:
            for type, value in self.__nonempty_groups(groups):
                val += self.__add_meta(value, groups)

        return val

    def __add_meta(self, word, groups):
        if not word.strip():
            return ''
        
        if self.in_dd:
        ## FIXME? for now, only accept entries on the same line for 
        ## meta value to minimise surprise
            if not self.ddline == self.lineno:
                return ''
                
            self.formatter.textstorage.append(word)

        return ''

    def _interwiki_repl(self, word, groups):
        """Handle InterWiki links."""
        wiki = groups.get('interwiki_wiki')
        page = groups.get('interwiki_page')
        wikipage = "%s:%s" % (wiki, page)
        self.__add_meta(wikipage, groups)

        iw_url = resolve_iw_url(self.request, wiki, page)

        self.currentitems.append(('interwiki', (wikipage, wikipage)))
        self.new_item = False
        return u''

    _interwiki_wiki_repl = _interwiki_repl
    _interwiki_page_repl = _interwiki_repl

    def _word_repl(self, word, groups):
        """Handle WikiNames."""
        bang_present = groups.get('word_bang')
        if bang_present:
            if self.cfg.bang_meta:
                return self.formatter.nowikiword("!%s" % word)
            else:
                self.formatter.text('!')

        name = groups.get('word_name')
        current_page = self.formatter.page.page_name
        abs_name = wikiutil.AbsPageName(current_page, name)
        if abs_name == current_page:
            self.currentitems.append(('wikilink', (abs_name, abs_name)))
            self.__add_meta(abs_name, groups)
            return u''
        else:
            # handle anchors
            try:
                abs_name, anchor = rsplit(abs_name, "#", 1)
            except ValueError:
                anchor = ""
            if self.cat_re.match(abs_name):
                self.currentitems.append(('category', (abs_name)))
                self.__add_meta(abs_name, groups)

            else:
                if not anchor:
                    wholename = abs_name
                else:
                    wholename = "%s#%s" % (abs_name, anchor)

                self.currentitems.append(('wikilink', (wholename, abs_name)))
                self.__add_meta(wholename, groups)
            return u''

    _word_bang_repl = _word_repl
    _word_name_repl = _word_repl
    _word_anchor_repl = _word_repl

    def _url_repl(self, word, groups):
        """Handle literal URLs."""
        scheme = groups.get('url_scheme', 'http')
        target = groups.get('url_target', '')

        self.__add_meta(target, groups)

        self.currentitems.append(('url', (target, target)))
        return u''

    _url_target_repl = _url_repl
    _url_scheme_repl = _url_repl

    def _macro_repl(self, word, groups):
        """Handle macros.
        All that really seems to be needed is to pass the raw markup. """
        macro_name = groups.get('macro_name')
        macro_args = groups.get('macro_args')
        macro = groups.get('macro')

        if macro_name == 'Include':
            # Add includes
            page_args = word.split(',')[0]
            self.currentitems.append(('include', (page_args, word)))

        return self.__add_meta(macro, {})

    _macro_name_repl = _macro_repl
    _macro_args_repl = _macro_repl

    def __nonempty_groups(self, groups):
        return [(x, y) for x, y in groups.iteritems() if y]

    def _fix_attach_uri(self, target):
        split = target.split(":", 1)
        if len(split) != 2:
            return target

        scheme, att = split
        if scheme in ('attachment', 'inline', 'drawing'):
            if len(att.split('/')) == 1:
                target = "%s:%s/%s" % (scheme, self.pagename, att)

        return target

    def _link_repl(self, word, groups):
        raw = groups.get('link', '')
        target = groups.get('link_target', '')
        desc = groups.get('link_desc', '')

        self.__add_meta(raw, groups)

        target = self._fix_attach_uri(target)

        # Add extended links, where applicable
        if desc and ': ' in desc and not self.in_dd:
            key = desc.split(': ')[0]
            self.definitions.setdefault(key, list()).append(('wikilink',
                                                             (raw, target)))
        else:
            self.currentitems.append(('wikilink', (raw, target)))
        return u''
    _link_target_repl = _link_repl
    _link_desc_repl = _link_repl
    _link_params_repl = _link_repl

    def _transclude_repl(self, word, groups):
        raw = groups.get('transclude', '')
        target = groups.get('transclude_target', '')
        self.__add_meta(raw, groups)

        target = self._fix_attach_uri(target)

        self.currentitems.append(('wikilink', (raw, target)))
        return u''
    _transclude_target_repl = _transclude_repl
    _transclude_desc_repl = _transclude_repl
    _transclude_params_repl = _transclude_repl

    def _email_repl(self, word, groups):
        self.__add_meta(word, groups)

        self.currentitems.append(('wikilink', (word, 'mailto:%s' % word)))
        return u''

    _big_repl = __add_textmeta
    _big_on_repl = __add_textmeta
    _big_off_repl = __add_textmeta
    _emph_ibb_repl = __add_textmeta
    _emph_ibi_repl = __add_textmeta
    _emph_ib_or_bi_repl = __add_textmeta
    _emph_repl = __add_textmeta
    _small_repl = __add_textmeta
    _small_on_repl = __add_textmeta
    _small_off_repl = __add_textmeta
    _smiley_repl = __add_textmeta
    _strike_repl = __add_textmeta
    _strike_on_repl = __add_textmeta
    _strike_off_repl = __add_textmeta

    _entity_repl = __add_meta
    _remark_repl = __add_meta
    _remark_on_repl = __add_meta
    _remark_off_repl = __add_meta
    _sgml_entity_repl = __add_meta
    _sub_repl = __add_meta
    _sub_text_repl = __add_meta
    _sup_repl = __add_meta
    _sup_text_repl = __add_meta
    _tt_bt_repl = __add_meta
    _tt_bt_text_repl = __add_meta
    _tt_repl = __add_meta
    _tt_text_repl = __add_meta
    _u_repl = __add_meta

    def _dl_repl(self, match, groups):
        """Handle definition lists."""
        if self.in_pre:
            return u''

        # Flush pre-dd links and previous dd:s not undented
        if self.currentitems and not self.curdef:
            self.definitions.setdefault('_notype', 
                                        list()).extend(self.currentitems)
        elif self.currentitems:
            self.definitions.setdefault(self.curdef, 
                                        list()).extend(self.currentitems)

        self.currentitems=[]
        self.ddline = self.lineno

        result = []
        self._close_item(result)
        self.in_dd = 1
        
        self.formatter.textstorage = list()

        definition = match[1:-3].strip(' ')
        if definition != "":
            self.curdef=definition
        else:
            self.curdef=self.prevdef

        return u''

    def _undent(self):
        if self.in_dd:
            curkey = self.definitions.setdefault(self.curdef, list())

            # Only account for non-empty text
            if ''.join(self.formatter.textstorage).strip():
                # Add the metas, prepare to populate next key
                curkey.append(('meta', ''.join(self.formatter.textstorage)))
                self.formatter.textstorage = list()
            if self.currentitems:
                curkey.extend(self.currentitems)
        else:
            self.definitions.setdefault('_notype', 
                                        list()).extend(self.currentitems)

        # self.ddline is not reset here, as the last 
        # items on line may be added after the undent
        self.in_dd = 0
        self.prevdef = self.curdef
        self.curdef = '_notype'
        self.currentitems = []

        return u''

    def _close_item(self, result):
        if self.in_dd:
            self._undent()

    def _parser_repl(self, word, groups):
        parser_name = groups.get('parser_name', None)

        self.in_pre = 'search_parser'

        # If there's a parser on the begin of the parser line, stop
        # searching for parsers. If wiki parser, process metas.
        if parser_name:
            if parser_name == 'wiki':
                self.in_pre = False
            elif parser_name.strip():
                self.in_pre = True

        return self.__add_meta(word, groups)

    # Catch the wiki parser within the parsed content
    def _parser_content(self, line):
        if self.in_pre == 'search_parser' and line.strip():
            if line.strip().startswith("#!"):
                parser_name = line.strip()[2:].split()[0]
                if parser_name == 'wiki':
                    self.in_pre = False
                    return ''

            # If the first line with content is not a parser spec -> no parser
            self.in_pre = True

        return ''

    _parser_unique_repl = _parser_repl
    _parser_line_repl = _parser_repl
    _parser_name_repl = _parser_repl
    _parser_args_repl = _parser_repl
    _parser_nothing_repl = _parser_repl
        
    def _parser_end_repl(self, word, groups):
        self.in_pre = False
        
        return self.__add_meta(word, groups)
