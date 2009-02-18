# -*- coding: utf-8 -*-"
"""
    savegraphdata class for saving the semantic data of pages

    @copyright: 2006 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""

import re
import os

from time import time
from copy import copy

# MoinMoin imports
from MoinMoin.parser.text_moin_wiki import Parser
from MoinMoin.wikiutil import importPlugin
from MoinMoin.Page import Page 

# graphlib imports
import graphingwiki.util, graphingwiki.editing

def add_meta(graphdata, pagename, (key, val)):
    # Do not handle empty metadata, except empty labels
    if key != 'gwikilabel':
        val = val.strip()
    if not val:
        return

    # Values to be handled in graphs
    if key in graphingwiki.util.SPECIAL_ATTRS:
        graphdata.set_attribute(pagename, key, val)
        # If color defined, set page as filled
        if key == 'fillcolor':
            graphdata.set_attribute(pagename, 'style', 'filled')
        return

    # Save in pagemeta's unlinks list
    graphdata.set_attribute(pagename, key, val)

def parse_text(request, page, text):
    pagename = page.page_name
    
    from copy import copy
    newreq = copy(request)
    newreq.cfg = copy(request.cfg)
    newreq.page = lcpage = LinkCollectingPage(newreq, pagename, text)
    newreq.theme = copy(request.theme)
    newreq.theme.request = newreq
    newreq.theme.cfg = newreq.cfg
    parserclass = importPlugin(request.cfg, "parser",
                                   'link_collect', "Parser")
    import MoinMoin.wikiutil as wikiutil
    myformatter = wikiutil.importPlugin(request.cfg, "formatter",
                                      'nullformatter', "Formatter")
    lcpage.formatter = myformatter(newreq)
    lcpage.formatter.page = lcpage
    p = parserclass(lcpage.get_raw_body(), newreq, formatter=lcpage.formatter)
    lcpage.parser = p
    lcpage.format(p)
    
    # These are the match types that really should be noted
    linktypes = ["wikiname_bracket", "word",                  
                 "interwiki", "url", "url_bracket"]
    
    # Add the page categories as links too
    categories, _, _ = graphingwiki.editing.parse_categories(request, text)
    
    for metakey, value in p.definitions.iteritems():
        for type, item in value:
            # print metakey, type, item
            dnode=None

            if  type in ['url', 'wikilink', 'interwiki', 'email']:
                dnode = item[1]
                hit = item[0]
            elif type == 'category':
                # print "adding cat", item, repr(categories)
                dnode = item
                hit = item
                if item in categories:
                    request.graphdata.add_link(pagename, dnode,
                                               u"gwikicategory", item)
            elif type == 'meta':
                add_meta(request.graphdata, pagename, (metakey, item))

            if dnode:
                request.graphdata.add_link(pagename, dnode, metakey, hit)


def execute(pagename, request, text, pagedir, page):
    # Skip MoinEditorBackups
    if pagename.endswith('/MoinEditorBackup'):
        return

    pageitem = page
    
    # clear page metas from indexes
    request.graphdata.clearpagemeta(pagename)
    # Parse the page and update graphdata
    parse_text(request, page, text)
    # re-add index
    request.graphdata.index_pagename(pagename)

    ## Remove deleted pages from the shelve
    # 1. Removing data at the moment of deletion
    # Deleting == saving a revision with the text 'deletec/n', then 
    # removing the revision. This seems to be the only way to notice.
    if text == 'deleted\n':
        request.graphdata.delpagemeta(pagename)
    else:
        # 2. Removing data when rehashing. 
        # New pages do not exist, but return a revision of 99999999 ->
        # Check these both to avoid deleting new pages.
        pf, rev, exists = pageitem.get_rev() 
        if rev != 99999999:
            if not exists:
                request.graphdata.delpagemeta(pagename)

    graphingwiki.util.delete_moin_caches(request, pageitem)

# - Code below lifted from MetaFormEdit -

# Override Page.py to change the parser. This method has the advantage
# that it works regardless of any processing instructions written on
# page, including the use of other parsers
class LinkCollectingPage(Page):

    def __init__(self, request, page_name, content, **keywords):
        # Cannot use super as the Moin classes are old-style
        apply(Page.__init__, (self, request, page_name), keywords)
        self.set_raw_body(content)

    # It's important not to cache this, as the wiki thinks we are
    # using the default parser
    def send_page_content(self, request, notparser, body, format_args='',
                          do_cache=0, **kw):
        self.parser = wikiutil.importPlugin(request.cfg, "parser",
                                       'link_collect', "Parser")

        kw['format_args'] = format_args
        kw['do_cache'] = 0
        apply(Page.send_page_content, (self, request, self.parser, body), kw)
