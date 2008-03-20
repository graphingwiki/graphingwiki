# -*- coding: utf-8 -*-"
"""
     Link harvesting "parser"
"""
import cgi, re
 
from MoinMoin.parser.text_moin_wiki import Parser as WikiParser
from MoinMoin import macro, wikiutil
from string import rsplit

Dependencies = []

class Parser(WikiParser):
    def __init__(self, raw, request, **kw):
        self.pagename = request.page.page_name

        # Cannot use super as the Moin classes are old-style
        apply(WikiParser.__init__, (self, raw, request), kw)
        
        self.interesting = []
        self.in_dd = 0
        self.cat_re=re.compile(request.cfg.page_category_regex)
    
    def _interwiki_repl(self, word, groups):
        """Handle InterWiki links."""
        print '*', repr(word)
        wiki = groups.get('interwiki_wiki')
        page = groups.get('interwiki_page')
        
        self.interesting.append(('interwiki', (wiki, page)))
        return u''

    _interwiki_wiki_repl = _interwiki_repl
    _interwiki_page_repl = _interwiki_repl

    def _word_repl(self, word, groups):
        """Handle WikiNames."""
        print '*', repr(word)
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
                self.interesting.append(('category', abs_name))
            else:
                self.interesting.append(('wikilink', (abs_name, anchor)))
            return u''

    _word_bang_repl = _word_repl
    _word_name_repl = _word_repl
    _word_anchor_repl = _word_repl

    def _url_repl(self, word, groups):
        """Handle literal URLs."""
        print '*', repr(word)
        scheme = groups.get('url_scheme', 'http')
        target = groups.get('url_target', '')
        self.interesting.append(('url', (scheme, target)))
        return u''

    _url_target_repl = _url_repl
    _url_scheme_repl = _url_repl

    def _macro_repl(self, word, groups):
        """Handle macros."""
        macro_name = groups.get('macro_name')
        macro_args = groups.get('macro_args')
        self.inhibit_p = 0 # 1 fixes UserPreferences, 0 fixes paragraph formatting for macros

        # create macro instance
        if self.macro is None:
            self.macro = macro.Macro(self)
        self.interesting.append(('macro', (macro_name, macro_args, groups.get('macro'))))
        return u''

    _macro_name_repl = _macro_repl
    _macro_args_repl = _macro_repl

    def _dl_repl(self, match, groups):
        """Handle definition lists."""
        result = []
        self._close_item(result)
        self.in_dd = 1
        self.formatter.textstorage=None
        self.formatter.linkstorage=None
        
        definition = match[1:-3].strip(' ')
        if definition != "":
            self.formatter.curdef=definition

        return u''
