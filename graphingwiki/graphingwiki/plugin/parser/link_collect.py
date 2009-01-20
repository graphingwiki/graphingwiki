# -*- coding: utf-8 -*-"
"""
     Link harvesting "parser"
"""
import cgi, re
 
from MoinMoin.parser.text_moin_wiki import Parser as WikiParser
from MoinMoin import macro, wikiutil
from string import rsplit

from graphingwiki.patterns import resolve_iw_url
from wiki_form import Parser as listParser

Dependencies = []

class Parser(WikiParser):
    def __init__(self, raw, request, **kw):
        self.pagename = request.page.page_name
        self.new_item = True
        self.definitions = {} 
        self.curdef = ''
        self.prevdef = ''
        self.ddline = 0

        # Cannot use super as the Moin classes are old-style
        apply(WikiParser.__init__, (self, raw, request), kw)
        
        self.currentitems = []
        self.in_dd = 0
        self.cat_re=re.compile(request.cfg.page_category_regex)

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

            # If there were eg. links before the text currently being
            # added, they have been gathered in self.formatter.currentitems.
            # Add them now before the text currently being processed.
            while self.currentitems:
                _, items = self.currentitems.pop()
                # The item zero contains the raw form of the item,
                # further ones contain parsed stuff for saevgraphdata
                self.formatter.textstorage.append(items[0])
                # Add space after link, they're omitted
                self.formatter.textstorage.append(' ')
                
            self.formatter.textstorage.append(word)
            self.new_item = False

        return ''

    def __add_link(self, word, groups):
        if self.in_dd:
            if not self.new_item:
                self.__add_meta(word, groups)
                return True
            else:
                self.new_item = False
    
        return False

    def _interwiki_repl(self, word, groups):
        """Handle InterWiki links."""
        wiki = groups.get('interwiki_wiki')
        page = groups.get('interwiki_page')
        wikipage = "%s:%s" % (wiki, page)
        if self.__add_link(wikipage, groups):
            return u""

        iw_url = resolve_iw_url(self.request, wiki, page)

        self.currentitems.append(('interwiki', (wikipage, iw_url)))
        self.new_item = False
        return u''

    _interwiki_wiki_repl = _interwiki_repl
    _interwiki_page_repl = _interwiki_repl

    def _word_repl(self, word, groups):
        """Handle WikiNames."""
        if self.__add_link(word, groups):
            return u""

        bang = ''
        bang_present = groups.get('word_bang')
        if bang_present:
            if self.cfg.bang_meta:
                return u''
        name = groups.get('word_name')
        current_page = self.formatter.page.page_name
        abs_name = wikiutil.AbsPageName(current_page, name)
        if abs_name == current_page:
            return u''
        else:
            # handle anchors
            try:
                abs_name, anchor = rsplit(abs_name, "#", 1)
            except ValueError:
                anchor = ""
            if self.cat_re.match(abs_name):
                self.currentitems.append(('category', (abs_name)))
            else:
                if not anchor:
                    wholename = abs_name
                else:
                    wholename = "%s#%s" % (abs_name, anchor)

                self.currentitems.append(('wikilink', (wholename, abs_name)))
            return u''

    _word_bang_repl = _word_repl
    _word_name_repl = _word_repl
    _word_anchor_repl = _word_repl

    def _url_repl(self, word, groups):
        """Handle literal URLs."""
        scheme = groups.get('url_scheme', 'http')
        target = groups.get('url_target', '')

        if self.__add_link(target, groups):
            return u""

        self.currentitems.append(('url', (target, target)))
        return u''

    _url_target_repl = _url_repl
    _url_scheme_repl = _url_repl

    def _macro_repl(self, word, groups):
        """Handle macros.
        All that really seems to be needed is to pass the raw markup. """
        return self.__add_meta(groups.get('macro'), {})

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

        # If we're in dd and there has been prior text, do not go forward
        if self.__add_link(raw, groups):
            return u""

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
        if self.__add_link(raw, groups):
            return u""

        target = self._fix_attach_uri(target)

        self.currentitems.append(('wikilink', (raw, target)))
        return u''
    _transclude_target_repl = _transclude_repl
    _transclude_desc_repl = _transclude_repl
    _transclude_params_repl = _transclude_repl

    def _email_repl(self, word, groups):
        self.__add_link(word, groups)
        self.currentitems.append(('wikilink', (word, 'mailto:%s' % word)))
        return u''

    _big_repl = __add_textmeta
    _emph_ibb_repl = __add_textmeta
    _emph_ibi_repl = __add_textmeta
    _emph_ib_or_bi_repl = __add_textmeta
    _emph_repl = __add_textmeta
    _small_repl = __add_textmeta
    _smiley_repl = __add_textmeta
    _strike_repl = __add_textmeta

    _comment_repl = __add_meta
    _entity_repl = __add_meta
    _heading_repl = __add_meta
    _remark_repl = __add_meta
    _sgml_entity_repl = __add_meta
    _sub_repl = __add_meta
    _sup_repl = __add_meta
    _tt_bt_repl = __add_meta
    _tt_repl = __add_meta
    _u_repl = __add_meta

    def __single_link_before_text(self):
        """ 
        Corner case: If we have a dd with non-empty text after a
        single link, it will not be added as text automatically, and
        has to be dealt with separately.
        """
        type, content = self.currentitems[0]
        raw = content[0]
        # The item came before the text
        self.formatter.textstorage.insert(0, raw)

    def _dl_repl(self, match, groups):
        """Handle definition lists."""
        if self.in_pre:
            return u''

        # Flush pre-dd links and previous dd:s not undented
        if self.currentitems and not self.curdef:
            self.definitions.setdefault('_notype', 
                                        []).extend(self.currentitems)
        elif self.currentitems:
            curkey = self.definitions.setdefault(self.curdef, [])

            # Only account for non-empty text
            if ''.join(self.formatter.textstorage).strip():
                self.__single_link_before_text()
                # Only add this to stored text, not self.definitions -
                # undent will handle the insertion of this meta later
            else:
                curkey.extend(self.currentitems)

        self.currentitems=[]
        self.new_item = True
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
            curkey = self.definitions.setdefault(self.curdef, [])

            # Only account for non-empty text
            if ''.join(self.formatter.textstorage).strip():
                if self.currentitems:
                    self.__single_link_before_text()
                # Add the metas, prepare to populate next key
                curkey.append(('meta', ''.join(self.formatter.textstorage)))
                self.formatter.textstorage = list()
            elif self.currentitems:
                curkey.extend(self.currentitems)
        else:
            self.definitions.setdefault('_notype', 
                                        []).extend(self.currentitems)

        # self.ddline is not reset here, as the last 
        # items on line may be added after the undent
        self.in_dd = 0
        self.new_item = True
        self.prevdef = self.curdef
        self.curdef = '_notype'
        self.currentitems = []

        return u''

    def _close_item(self, result):
        if self.in_dd:
            self._undent()

    def _parser_repl(self, word, groups):
        self.in_pre = True
        
        return self.__add_meta(word, groups)
        
    def _parser_end_repl(self, word, groups):
        self.in_pre = False
        
        return self.__add_meta(word, groups)