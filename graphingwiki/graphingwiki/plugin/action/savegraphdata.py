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
import shelve

from time import time
from copy import copy

# MoinMoin imports
from MoinMoin.parser.text_moin_wiki import Parser
from MoinMoin.wikiutil import importPlugin
from MoinMoin.Page import Page 

# graphlib imports
import graphingwiki.util, graphingwiki.editing

# Add in-links from current node to local nodes
def shelve_add_in(graphdata, (frm, to), linktype):
    if not linktype:
        linktype = graphingwiki.util.NO_TYPE

    temp = graphdata.getpagemeta(to)

    temp.inlinks.add(linktype, frm)
        
    # Notification that the destination has changed
    temp.mtime = time()

# Add out-links from local nodes to current node
def shelve_add_out(graphdata, (frm, to), linktype, hit):
    if not linktype:
        linktype = graphingwiki.util.NO_TYPE

    temp = graphdata.getpagemeta(frm)
    temp.outlinks.add(linktype, to)
    # Also add literal text (hit) for each link
    # eg, if out it SomePage, lit can be ["SomePage"]
    temp.litlinks.add(linktype, hit)

def strip_meta(key, val):
    key = key.strip()
    if key != 'gwikilabel':
        val = val.strip()
    return key, val

def shelve_set_attribute(graphdata, node, key, val):
    key, val = strip_meta(key, val)

    temp = graphdata.getpagemeta(node)

    if key in graphingwiki.util.SPECIAL_ATTRS:
        temp.unlinks.set_single(key, val)
    else:
        temp.unlinks.add(key, val)

def add_meta(graphdata, pagename, (key, val)):

    # Do not handle empty metadata, except empty labels
    if key != 'gwikilabel':
        val = val.strip()
    if not val:
        return

    # Values to be handled in graphs
    if key in graphingwiki.util.SPECIAL_ATTRS:
        shelve_set_attribute(graphdata, pagename, key, val)
        # If color defined, set page as filled
        if key == 'fillcolor':
            shelve_set_attribute(graphdata, pagename, 'style', 'filled')
        return

    # Save to shelve's metadata list
    shelve_set_attribute(graphdata, pagename, key, val)

def add_include(new_data, pagename, hit):
    hit = hit[11:-3]
    pagearg = hit.split(',')[0]

    # If no data, continue
    if not pagearg:
        return

    temp = new_data.get(pagename, {})
    temp.setdefault(u'include', list()).append(pagearg)
    new_data[pagename] = temp

def add_link(graphdata, pagename, nodename, linktype, hit):
    edge = [pagename, nodename]

    shelve_add_in(graphdata, edge, linktype)
    shelve_add_out(graphdata, edge, linktype, hit)

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
                    add_link(request.graphdata, pagename, dnode, 
                             u"gwikicategory", item)
            elif type == 'meta':
                add_meta(request.graphdata, pagename, (metakey, item))

            if dnode:
                add_link(request.graphdata, pagename, dnode, metakey, hit)



def save_triplet(e, a, v):
    print e, a, v

def execute(pagename, request, text, pagedir, page):
    # Skip MoinEditorBackups
    if pagename.endswith('/MoinEditorBackup'):
        return

    pageitem = page

    # Parse the page and update graphdata
    parse_text(request, page, text)

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
