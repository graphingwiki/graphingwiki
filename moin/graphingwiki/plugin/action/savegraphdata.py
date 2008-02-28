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
import cPickle
import shelve
from codecs import getencoder
from urllib import quote as url_quote
from urllib import unquote as url_unquote
from time import time

# MoinMoin imports
from MoinMoin import config
from MoinMoin.parser.text_moin_wiki import Parser
from MoinMoin.wikiutil import importPlugin
from MoinMoin.util.lock import WriteLock
from MoinMoin.Page import Page

# graphlib imports
from graphingwiki import graph
from graphingwiki.patterns import special_attrs

# Page names cannot contain '//'
url_re = re.compile(u'^(%s)%%3A//' % (Parser.url_rule))

# We only want to save linkage data releted to pages in this wiki
# Interwiki links will have ':' in their names (this will not affect
# pages as their names are url quoted at this stage)
def local_page(pagename):
    if url_re.search(pagename) or ':' in pagename:
        return False

    return True

# Add in-links from current node to local nodes
def shelve_add_in(shelve, (frm, to), linktype):
    if not linktype:
        linktype = '_notype'
    if local_page(to):
         temp = shelve.get(to, {})

         if not temp.has_key('in'):
             temp['in'] = {linktype: [frm]}
         elif not temp['in'].has_key(linktype):
             temp['in'][linktype] = [frm]
         else:
             temp['in'][linktype].append(frm)

         # Notification that the destination has changed
         temp['mtime'] = time()
         
         shelve[to] = temp

# Add out-links from local nodes to current node
def shelve_add_out(shelve, (frm, to), linktype, hit):
    if not linktype:
        linktype = '_notype'
    if local_page(frm):
         temp = shelve.get(frm, {})

         # Also add literal text (hit) for each link
         # eg, if out it SomePage, lit can be ["SomePage"]
         if not temp.has_key('out'):
             temp['out'] = {linktype: [to]}
             temp['lit'] = {linktype: [hit]}
         elif not temp['out'].has_key(linktype):
             temp['out'][linktype] = [to]
             temp['lit'][linktype] = [hit]
         else:
             temp['out'][linktype].append(to)
             temp['lit'][linktype].append(hit)

         shelve[frm] = temp

# Respectively, remove in-links
def shelve_remove_in(shelve, (frm, to), linktype):
    import sys
#    sys.stderr.write('Starting to remove in\n')
    to = encode(to)
    temp = shelve.get(to, {})
    if local_page(to) and temp.has_key('in'):
        for type in linktype:
#            sys.stderr.write("Removing %s %s %s\n" % (frm, to, linktype))
            # eg. when the shelve is just started, it's empty
            if not temp['in'].has_key(type):
#                sys.stderr.write("No such type: %s\n" % type)
                continue
            if frm in temp['in'][type]:
                temp['in'][type].remove(frm)
                if not temp['in'][type]:
                    del temp['in'][type]
                    
                # Notification that the destination has changed
                temp['mtime'] = time()
                
#                sys.stderr.write("Hey man, I think I did it!\n")
        shelve[to] = temp

# Respectively, remove out-links
def shelve_remove_out(shelve, (frm, to), linktype):
#    print 'Starting to remove out'
    temp = shelve.get(frm, {})
    if local_page(frm) and temp.has_key('out'):
        for type in linktype:
#            print "Removing %s %s %s" % (frm, to, linktype)
            # eg. when the shelve is just started, it's empty
            if not temp['out'].has_key(type):
#                print "No such type: %s" % type
                continue
            while to in temp['out'][type]:
                # As the literal text values for the links
                # are added at the same time, they have the
                # same index value
                i = temp['out'][type].index(to)
                temp['out'][type].remove(to)
                del temp['lit'][type][i]

#                print "removed %s" % (repr(to))

            if not temp['out'][type]:
                del temp['out'][type]
                del temp['lit'][type]
#                print "%s empty" % (type)
#            print "Hey man, I think I did it!"

        shelve[frm] = temp

def quotemeta(key, val):
    # Keys may be pages -> url-quoted
    key = url_quote(key.strip())
    if key != 'label':
        val = val.strip()

    # Values are just quoted strings
    val = quotedstring(val)
    return key, val

def node_set_attribute(pagenode, key, val):
    key, val = quotemeta(key, val)
    vars = getattr(pagenode, key, None)
    if not vars:
        setattr(pagenode, key, set([val]))
    else:
        vars.add(val)
        setattr(pagenode, key, vars)

def shelve_unset_attributes(shelve, node):
    if shelve.get(node, {}).has_key('meta'):

        temp = shelve[node]
        temp['meta'] = {}
        shelve[node] = temp

def shelve_set_attribute(shelve, node, key, val):
    key, val = quotemeta(key, val)

    temp = shelve.get(node, {})

    if not temp.has_key('meta'):
        temp['meta'] = {key: set([val])}
    elif not temp['meta'].has_key(key):
        temp['meta'][key] = set([val])
    # a page can not have more than one label, shapefile etc
    elif key in special_attrs:
        temp['meta'][key] = set([val])
    else:
        temp['meta'][key].add(val)

    shelve[node] = temp

def encode(s):
    return s.encode(config.charset, 'replace')

def wiki_unquote(str):
    return url_unquote(str).replace('_', ' ')

# Escape quotes in str, remove existing quotes, add outer quotes.
def quotedstring(str):
    escq = re.compile(r'(?<!\\)"')
    str = str.strip("\"'")
    str = escq.subn('\\"', str)[0]
    return '"' + str + '"'

# Quote names with namespace/interwiki (for rdf/n3 use)
def quotens(str):
    return ':'.join([url_quote(encode(x)) for x in str.split(':')])

def getlinktype(augdata):
    linktype = ''
    if len(augdata) > 1:
        if ':' in augdata[0]:
            # links with namespace!
            linktype = quotens(augdata[0])
        else:
            # quote all link types
            linktype = url_quote(augdata[0])
    return linktype

def add_meta(globaldata, pagenode, quotedname, hit):
    # decode to target charset, grab comma-separated key,val
    hit = encode(hit[11:-3])
    args = hit.split(',')

    # If no data, continue
    if len(args) < 2:
        return

    key = args[0]
    val = ','.join(args[1:])

    # Do not handle empty metadata, except empty labels
    if key != 'label':
        val = val.strip()
    if not val:
        return

    # Values to be handed to dot
    if key in special_attrs:
        setattr(pagenode, key, val)
        shelve_set_attribute(globaldata, quotedname, key, val)
        # If color defined, set page as filled
        if key == 'fillcolor':
            setattr(pagenode, 'style', 'filled')
            shelve_set_attribute(globaldata, quotedname,
                                 'style', 'filled')
        return

    # Save to pagegraph and shelve's metadata list
    node_set_attribute(pagenode, key, val)
    shelve_set_attribute(globaldata, quotedname, key, val)

def add_category(globaldata, pagegraph, node, category):
    pagenode = pagegraph.nodes.get(node)
    node_set_attribute(pagenode, 'WikiCategory', category)
    shelve_set_attribute(globaldata, node, 'WikiCategory', category)

def set_node_params(globaldata, pagegraph, node, url, label):
    shelve_set_attribute(globaldata, node, 'URL', url)
    if not pagegraph.nodes.get(node):
        n = pagegraph.nodes.add(node)
        n.URL = url
        if label and not getattr(n, 'label', ''):
            n.label = label
            meta = globaldata.get(nodename, {}).get('meta', {})
            if not meta.get('label', ''):
                shelve_set_attribute(globaldata, node, 'label', nodelabel)

def add_link(globaldata, pagegraph, snode, dnode, linktype):
    # Add node w/ URL, label if not already added
    if not pagegraph.nodes.get(snode):
        pagegraph.nodes.add(snode)
    if not pagegraph.nodes.get(dnode):
        pagegraph.nodes.add(dnode)

    edge = [snode, dnode]

    shelve_add_in(globaldata, edge, linktype)
    shelve_add_out(globaldata, edge, linktype, dnode)

    # Add edge if not already added
    e = pagegraph.edges.get(*edge)
    if not e:
        e = pagegraph.edges.add(*edge)

    if not linktype:
        linktype = '_notype'

    if hasattr(e, 'linktype'):
        e.linktype.add(linktype)
    else:
        e.linktype = set([linktype])

def parse_text(request, globaldata, page, text):
    pagename = page.page_name
    quotedname = url_quote(encode(pagename))
    
    from copy import copy
    newreq = copy(request)
    newreq.cfg = copy(request.cfg)
    newreq.page = lcpage = LinkCollectingPage(newreq, pagename)
    newreq.theme = copy(request.theme)
    newreq.theme.request = newreq
    newreq.theme.cfg = newreq.cfg
    parserclass = importPlugin(request.cfg, "parser",
                                   'link_collect', "Parser")
    p = parserclass(lcpage.get_raw_body(), newreq)
    import MoinMoin.wikiutil as wikiutil
    myformatter = wikiutil.importPlugin(request.cfg, "formatter",
                                      'nullformatter', "Formatter")
    lcpage.formatter = myformatter(newreq)
    lcpage.formatter.page = lcpage
    lcpage.format(p)

    # These are the match types that really should be noted
    linktypes = ["wikiname_bracket", "word",                  "interwiki", "url", "url_bracket"]
    
    pagegraph = graph.Graph()
    pagegraph.charset = config.charset

    # add a node for current page
    pagenode = pagegraph.nodes.add(quotedname)
    # add a nicer-looking label, also
    pagelabel = encode(pagename)
    shelve_set_attribute(globaldata, quotedname, 'label', pagelabel)

#def add_link(globaldata, quotedname, pagegraph, cat_re,
#             nodename, nodelabel, nodeurl, linktype, hit):

    snode = encode(quotedname)
    for type, value in p.interesting:
        dnode = None
        url = None
        label = None
        if type == 'wikilink':
            dnode=encode(value[0])
        elif type == 'url':
            dnode=encode(value[1])
            url=encode(value[1])
        elif type == 'interwiki':
            dnode=encode("%s:%s" % (value[0],value[1]))
        elif type == 'category':
            add_category(globaldata, pagegraph, encode(snode), encode(value))
        if url or label:
            set_node_params(globaldata, pagegraph, dnode, url, label)
        if dnode:
            add_link(globaldata, pagegraph, snode, dnode, type)

    for definition, type, link in lcpage.formatter.definitions:
        if type == 'link':
            add_link(globaldata, pagegraph, snode, encode(link), encode(definition))

    return globaldata, pagegraph


def execute(pagename, request, text, pagedir, page):
    # Skip MoinEditorBackups
    if pagename.endswith('/MoinEditorBackup'):
        return

    graphshelve = os.path.join(request.cfg.data_dir,
                               'graphdata.shelve')

    # Expires old locks left by crashes etc.
    # Page locking mechanisms should prevent this code being
    # executed prematurely - thus expiring both read and
    # write locks
    lock = WriteLock(request.cfg.data_dir, timeout=10.0)
    lock.acquire()

    # Open file db for global graph data, creating it if needed
    globaldata = shelve.open(graphshelve, flag='c')
    
    # The global graph data contains all the links, even those that
    # are not immediately available in the page's graphdata pickle
    quotedname = url_quote(encode(pagename))

    # Page graph file to save detailed data in
    gfn = os.path.join(pagedir,'graphdata.pickle')
    # load graphdata if present and not trashed, remove it from index
    if os.path.isfile(gfn) and os.path.getsize(gfn):
        pagegraphfile = file(gfn)
        old_data = cPickle.load(pagegraphfile)
        
        for edge in old_data.edges.getall(parent=quotedname):
            e = old_data.edges.get(*edge)
            linktype = getattr(e, 'linktype', ['_notype'])
            shelve_remove_in(globaldata, edge, linktype)
            shelve_remove_out(globaldata, edge, linktype)

        for edge in old_data.edges.getall(child=quotedname):
            e = old_data.edges.get(*edge)
            linktype = getattr(e, 'linktype', ['_notype'])
            shelve_remove_in(globaldata, edge, linktype)
            shelve_remove_out(globaldata, edge, linktype)

        shelve_unset_attributes(globaldata, quotedname)

        pagegraphfile.close()

    # Include timestamp to current page
    if not globaldata.has_key(quotedname):
        globaldata[quotedname] = {'mtime': time(), 'saved': True}
    else:
        temp = globaldata[quotedname]
        temp['mtime'] = time()
        temp['saved'] = True
        globaldata[quotedname] = temp

    # Overwrite pagegraphfile with the new data
    pagegraphfile = file(gfn, 'wb')

    globaldata, pagegraph = parse_text(request, globaldata, page, text)

    # Save graph as pickle, close
    cPickle.dump(pagegraph, pagegraphfile)
    pagegraphfile.close()
    # Remove locks, close shelves
    globaldata.close()
    lock.release()


# - code below lifted from MetaFormEdit -

# Override Page.py to change the parser. This method has the advantage
# that it works regardless of any processing instructions written on
# page, including the use of other parsers
class LinkCollectingPage(Page):

    def __init__(self, request, page_name, **keywords):
        # Cannot use super as the Moin classes are old-style
        apply(Page.__init__, (self, request, page_name), keywords)

    # It's important not to cache this, as the wiki thinks we are
    # using the default parser
    def send_page_content(self, request, notparser, body, format_args='',
                          do_cache=0, **kw):
        parser = wikiutil.importPlugin(request.cfg, "parser",
                                       'link_collect', "Parser")

        kw['format_args'] = format_args
        kw['do_cache'] = 0
        apply(Page.send_page_content, (self, request, parser, body), kw)

