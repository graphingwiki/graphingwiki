 # -*- coding: utf-8 -*-
"""
    Utils for graph generation, compatibility between MoinMoin versions
    etc.

    @copyright: 2006-2009 by Joachim Viide and
                             Juhani Eronen <exec@iki.fi>
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
import itertools
import StringIO
import cgi
import durus.client_storage, durus.connection
from durus.persistent_dict import PersistentDict
from durus.persistent_list import PersistentList
from durus.btree import BTree as DurusBTree
from durus.persistent import Persistent

import MoinMoin.version

from MoinMoin import caching
from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.util.lock import ReadLock, WriteLock
from MoinMoin.action import AttachFile
from MoinMoin.Page import Page

from graphingwiki.graph import Graph

MOIN_VERSION = float('.'.join(MoinMoin.version.release.split('.')[:2]))

SEPARATOR = '-gwikiseparator-'

# Get action name
def actionname(request, pagename):
    return '%s/%s' % (request.getScriptname(), url_escape(pagename))

def toutf8(unistr):
    return unistr.encode(config.charset, 'replace')

def fromutf8(bytestr):
    return unicode(bytestr, config.charset)

# compat names
encode_page, decode_page = toutf8, fromutf8


def url_escape(text):
    # Escape characters that break links in html values fields, 
    # macros and urls with parameters
    return re.sub('[\]"\?#&+]', lambda mo: '%%%02x' % ord(mo.group()), text)

def form_escape(text):
    # Escape characters that break value fields in html forms
    #return re.sub('["]', lambda mo: '&#x%02x;' % ord(mo.group()), text)
    return cgi.escape(text, quote=True)

def url_parameters(args):
    req_url = u'?'

    url_args = list()
    for key in args:
        for val in args[key]:
            url_args.append(u'='.join(map(url_escape, [key, val])))

    req_url += u'&'.join(url_args)

    return req_url

def url_construct(request, args):
    req_url = request.getScriptname() + u'/' + request.page.page_name 

    if args:
        req_url += url_parameters(args)

    return request.getQualifiedURL(req_url)

# Default node attributes that should not be shown
SPECIAL_ATTRS = ["gwikilabel", "gwikisides", "gwikitooltip", "gwikiskew",
                 "gwikiorientation", "gwikifillcolor", 'gwikiperipheries',
                 'gwikishapefile', "gwikishape", "gwikistyle", 
                 'gwikicategory', 'gwikiURL']
nonguaranteeds_p = lambda node: filter(lambda y: y not in
                                       SPECIAL_ATTRS, dict(node))

NO_TYPE = u'_notype'

# FIXME: Is this needed?
def resolve_iw_url(request, wiki, page): 
    res = wikiutil.resolve_interwiki(request, wiki, page) 
    if res[3] == False: 
        iw_url = res[1] + res[2] 
    else: 
        iw_url = './InterWiki' 
        
    return iw_url 

ATTACHMENT_SCHEMAS = ["attachment", "drawing"]

def node_type(request, nodename):
    if ':' in nodename:
        if request.graphdata.url_re.search(nodename):
            return 'url'

        start = nodename.split(':')[0]
        if start in ATTACHMENT_SCHEMAS:
            return 'attachment'

        iw_list = wikiutil.load_wikimap(request)
        if iw_list.has_key(start):
            return 'interwiki'

    return 'page'

def filter_categories(request, candidates):
    # Let through only the candidates that are both valid category
    # names and WikiWords

    # Nah, the word rules in 1.6 were not for the feint for heart,
    # just use the wikiutil function until further notice

    return wikiutil.filterCategoryPages(request, candidates)

def get_url_ns(request, pagename, link):
    # Find out subpage level to adjust URL:s accordingly
    subrank = pagename.count('/')
    # Namespaced names
    if ':' in link:
        iw_list = wikiutil.load_wikimap(request)
        iwname = link.split(':')
        if iw_list.has_key(iwname[0]):
            return iw_list[iwname[0]] + iwname[1]
        else:
            return '../' * subrank + './InterWiki'
    # handle categories as ordernodes different
    # so that they would point to the corresponding categories
    if filter_categories(request, [link]):
        return '../' * subrank + './' + link
    else:
        return '../' * subrank + './Property' + link

def format_wikitext(request, data):
    from MoinMoin.parser.text_moin_wiki import Parser

    request.page.formatter = request.formatter
    request.formatter.page = request.page
    parser = Parser(data, request)
    parser.request = request
    # No line anchors of any type to table cells
    request.page.formatter.in_p = 1
    parser._line_anchordef = lambda: ''

    # Do not parse macros from revision pages. For some reason,
    # it spawns multiple requests, which are not finished properly,
    # thus littering a number of readlocks. Besides, the macros do not
    # return anything useful anyway for pages they don't recognize
    if '?action=recall' in request.page.page_name:
        parser._macro_repl = lambda x: x

    # Using StringIO in order to strip the output
    data = StringIO.StringIO()
    request.redirect(data)
    # Produces output on a single table cell
    request.page.format(parser)
    request.redirect()

    return data.getvalue().strip()

def absolute_attach_name(name, target):
    abs_method = target.split(':')[0]

    # Pages from MetaRevisions may have ?action=recall, breaking attach links
    if '?' in name:
        name = name.split('?', 1)[0]

    if abs_method in ATTACHMENT_SCHEMAS and not '/' in target:
        target = target.replace(':', ':%s/' % (name.replace(' ', '_')), 1)

    return target 

def get_selfname(request):
    if request.cfg.interwikiname:
        return request.cfg.interwikiname
    else:
        return 'Self'

def get_wikiurl(request):
    return request.getBaseURL() + '/'

def attachment_file(request, page, file):
    att_file = AttachFile.getFilename(request, page, file)
                                                   
    return att_file, os.path.isfile(att_file)


class Metas(PersistentDict):
    def add(self, typ, val):
        try:
            l = self[typ]
        except KeyError:
            l = self[typ] = PersistentList()
        l.append(val)

    def set_single(self, typ, val):
        self[typ] = PersistentList([val])

    def get_single(self, typ, val, default=None):
        val = self[typ]
        if len(val) > 1:
            raise ValueError, typ, 'has multiple values'
        return val[0]


class PageMeta(Persistent):
    def __init__(self):
        self.outlinks = Metas()
        self.inlinks = Metas()
        self.unlinks = Metas()
        self.litlinks = Metas()
        self.mtime = 0
        self.saved = True

class GraphData:
    def __init__(self, request):
        self.request = request

        self.durus_storage = durus.client_storage.ClientStorage('localhost')
        self.durus_conn = durus.connection.Connection(self.durus_storage)
        self.dbroot = self.durus_conn.get_root()
        if not self.dbroot.has_key('pagemeta_by_pagename'):
            self.clear_db()
        from MoinMoin.parser.text_moin_wiki import Parser

        # Ripped off from Parser
        url_pattern = u'|'.join(config.url_schemas)

        url_rule = ur'%(url_guard)s(%(url)s)\:([^\s\<%(punct)s]|([%(punct)s][^\s\<%(punct)s]))+' % {
            'url_guard': u'(^|(?<!\w))',
            'url': url_pattern,
            'punct': Parser.punct_pattern,
        }

        self.url_re = re.compile(url_rule)

    pagemeta_by_pagename = property(lambda self: self.dbroot['pagemeta_by_pagename'])
    pagemeta_by_metakey = property(lambda self: self.dbroot['pagemeta_by_metakey'])
    pagemeta_by_metaval = property(lambda self: self.dbroot['pagemeta_by_metaval'])



    def pagenames(self):
         return self.pagemeta_by_pagename.iterkeys()

    def allpagemetas(self):
        return self.pagemeta_by_pagename.itervalues()

    def clear_db(self):
        self.dbroot.clear()
        indices = 'pagemeta_by_pagename', 'pagemeta_by_metakey', 'pagemeta_by_metaval'
        for i in indices:
            self.dbroot[i] = DurusBTree()

    def getpagemeta(self, pagename):
        # Always read data here regardless of user rights,
        # they should be handled elsewhere.
        return self.pagemeta_by_pagename.setdefault(pagename, PageMeta())
    
    def delpagemeta(self, pagename):
        try:
            pm = self.pagemeta_by_pagename[pagename]
        except KeyError:
            return
        
        ol, ul = pm.outlinks, pm.unlinks
        for metakey in ol.keys() + ul.keys():
            self.pagemeta_by_metakey.get(metakey, []).remove(pagename)

            for val in ol.get(metakey, []) + ul.get(metakey, []):
                self.pagemeta_by_metaval[val].remove(pagename)

        del self.pagemeta_by_pagename[pagename]

    def set_attribute(self, pagename, key, val):
        key = key.strip()
        if key in SPECIAL_ATTRS:
            pm.unlinks.set_single(key, val)
        else:
            pm.unlinks.add(key, val)

    def add_link(self, pagename, frompage, topage, key, lit):
        if not key:
            key = NO_TYPE
        # inlink
        self.getpagemeta(topage).inlinks.add(key, frompage)

        # outlink
        pm = self.getpagemeta(frompage)
        pm.outlinks.add(key, topage)

        # litlink, literal text (lit) for each link
        # eg, if out it SomePage, lit can be ["SomePage"]
        pm.litlinks.add(key, lit)
        
    def clearpagemeta(self, pagename):
        # savegraphdata uses this, first clear and then add metas
        pm = self.getpagemeta(pagename)
        ol, ul = pm.outlinks, pm.unlinks

        # set-ify to eliminate dups
        for metakey in set(pm.outlinks.keys() + pm.unlinks.keys()):
            # remove page from metakey index
            pl = self.pagemeta_by_metakey[metakey]
            pl.remove(pagename)

            # add page to metaval index
            for val in set(ol.get(metakey, []) + ul.get(metakey, [])):
                l = self.pagemeta_by_metaval[val]
                l.remove(pagename)

        # remove this page from other pages' inlinks
        for otherpm in map(self.getpagemeta, pm.outlinks.items()):
            otherpm.inlinks.remove(pagename)
        # finally empty this page's links
        pm.outlinks.clear()
        pm.unlinks.clear()
        # leave inlinks alone, as they're other pages' business

    def index_pagename(self, pagename):
        pm = self.getpagemeta(pagename)
        ol, ul = pm.outlinks, pm.unlinks

        # set-ify to eliminate dups
        for metakey in set(pm.outlinks.keys() + pm.unlinks.keys()):
            pl = self.pagemeta_by_metakey.setdefault(metakey, PersistentList())

            # add page to metakey index
            if pagename not in pl:
                pl.append(pagename)

            # add page to metaval index
            for val in set(ol.get(metakey, []) + ul.get(metakey, [])):
                self.pagemeta_by_metaval.setdefault(
                    val, PersistentList()).append(pagename)

    def _add_node(self, pagename, graph, urladd="", nodetype=""):
        # Don't bother if the node has already been added
        if graph.nodes.get(pagename):
            return graph

        page = self.getpagemeta(pagename)

        node = graph.nodes.add(pagename)
        # Add metadata
        for key, val in page.unlinks.items():
            if key in SPECIAL_ATTRS:
                node.__setattr__(key, u''.join(val))
            else:
                node.__setattr__(key, val)

        # Add links as metadata
        for key, val in page.outlinks.items():
            if key == NO_TYPE:
                continue
            if key in SPECIAL_ATTRS:
                node.__setattr__(key, u''.join(val))
            else:
                node.__setattr__(key, val)

        # Shapefile is an extra special case
        for shape in page.litlinks.get('gwikishapefile', list()):
            node.gwikishapefile = shape
        # so is category
        node.gwikicategory = \
            page.outlinks.get('gwikicategory', list())

        # Configuration for local pages next, 
        # return known to be something else
        if not nodetype == 'page':
            return graph

        # Local nonexistent pages must get URL-attribute
        if not hasattr(node, 'gwikiURL'):
            node.gwikiURL = './' + pagename

        if page.saved:
            node.gwikiURL += urladd
            # FIXME: Is this needed?
            # node.gwikiURL = './' + node.gwikiURL
        elif Page(self.request, pagename).isStandardPage():
            # try to be helpful and add editlinks to non-underlay pages
            node.gwikiURL += u"?action=edit"
            node.gwikitooltip = self.request.getText('Add page')

        if node.gwikiURL.startswith('attachment:'):
            pagefile = node.gwikiURL.split(':')[1]
            page, file = attachment_pagefile(pagefile, pagename)

            node.gwikilabel = toutf8(file)
            node.gwikiURL = toutf8(actionname(self.request, page) + \
                '?action=AttachFile&do=get&target=' + file)

        return graph

    def _add_link(self, adata, edge, type):
        # Add edge if it does not already exist
        e = adata.edges.get(*edge)
        if not e:
            e = adata.edges.add(*edge)
            e.linktype = set([type])
        else:
            e.linktype.add(type)
        return adata

    def load_graph(self, pagename, urladd, load_origin=True):
        if not self.request.user.may.read(pagename):
            return None

        cat_re = category_regex(self.request)
        temp_re = template_regex(self.request)

        page = self.getpagemeta(pagename)
        if not page:
            return None

        # Make graph, initialise head node
        adata = Graph()
        if load_origin:
            adata = self._add_node(pagename, adata, urladd, 'page')
        else:
            adata.nodes.add(pagename)

        # Add links to page

        for type in page.inlinks:
            for src in page.inlinks[type]:
                # Filter Category, Template pages
                if cat_re.search(src) or temp_re.search(src):
                    continue
                # Add page and its metadata
                # Currently pages can have links in them only
                # from local pages, thus nodetype == page
                adata = self._add_node(src, adata, urladd, 'page')
                adata = self._add_link(adata, (src, pagename), type)

        # Add links from page
        for type in page.outlinks:
            for i, dst in enumerate(page.outlinks[type]):
                # Filter Category, Template pages
                if cat_re.search(dst) or temp_re.search(dst):
                    continue

                # Fix links to everything but pages
                label = ''
                gwikiurl = ''
                tooltip = ''
                nodetype = node_type(self.request, dst)

                if nodetype == 'attachment':
                    # get the absolute name ie both page and filename
                    gwikiurl = absolute_attach_name(pagename, dst)
                    att_parts = gwikiurl.split(':')[1].split('/')
                    att_page = '/'.join(att_parts[:-1])
                    att_file = att_parts[-1]

                    if pagename == att_page:
                        label = "Attachment: %s" % (att_file)
                    else:
                        label = "Attachment: %s/%s" % (att_page, att_file)

                    _, exists = attachment_file(self.request, 
                                                att_page, att_file)

                    # For existing attachments, have link to view it
                    if exists:
                        gwikiurl = "./%s?action=AttachFile&do=get&target=%s" % \
                            (att_page, att_file)
                        tooltip = self.request.getText('View attachment')
                    # For non-existing, have a link to upload it
                    else:
                        gwikiurl = "./%s?action=AttachFile&rename=%s" % \
                            (att_page, att_file)
                        tooltip = self.request.getText('Add attachment')

                elif nodetype == 'interwiki':
                    # Get effective URL:s to interwiki URL:s
                    iwname = dst.split(':')
                    iw_list = wikiutil.load_wikimap(self.request)

                    gwikiurl = iw_list[iwname[0]] + iwname[1]
                    tooltip = iwname[1] + ' ' + \
                        self.request.getText('page on') + \
                        ' ' + iwname[0] + ' ' + \
                        self.request.getText('wiki')

                elif nodetype == 'url':
                    # URL:s have the url already, keep it
                    gwikiurl = dst
                    tooltip = dst

                # Add page and its metadata
                adata = self._add_node(dst, adata, urladd, nodetype)
                adata = self._add_link(adata, (pagename, dst), type)

                if label or gwikiurl or tooltip:
                    node = adata.nodes.get(dst)

                # Add labels, gwikiurls and tooltips
                if label:
                    node.gwikilabel = label
                if gwikiurl:
                    node.gwikiURL = gwikiurl
                if tooltip:
                    node.gwikitooltip = tooltip

        return adata

# The load_ -functions try to minimise unnecessary reloading and overloading

def load_node(request, graph, node, urladd):
    load_origin = False

    nodeitem = graph.nodes.get(node)
    if not nodeitem:
        nodeitem = graph.nodes.add(node)
        load_origin = True

    # Get new data for current node
    adata = request.graphdata.load_graph(node, urladd, load_origin)

    if adata:
        nodeitem.update(adata.nodes.get(node))

    return adata

def load_children(request, graph, parent, urladd):
    adata = load_node(request, graph, parent, urladd)

    # If no data
    if not adata:
        return list()
    if not adata.nodes.get(parent):
        return list()

    children = set()

    # Add new nodes, edges that link to/from the current node
    for child in adata.edges.children(parent):
        if not graph.nodes.get(child):
            newnode = graph.nodes.add(child)
            newnode.update(adata.nodes.get(child))

        newedge = graph.edges.add(parent, child)
        edgedata = adata.edges.get(parent, child)
        newedge.update(edgedata)

        children.add(child)

    return children

def load_parents(request, graph, child, urladd):
    adata = load_node(request, graph, child, urladd)

    # If no data
    if not adata:
        return list()
    if not adata.nodes.get(child):
        return list()

    parents = set()

    # Add new nodes, edges that are the parents of the current node
    for parent in adata.edges.parents(child):
        if not graph.nodes.get(parent):
            newnode = graph.nodes.add(parent)
            newnode.update(adata.nodes.get(parent))

        newedge = graph.edges.add(parent, child)
        edgedata = adata.edges.get(parent, child)
        newedge.update(edgedata)

        parents.add(parent)

    return parents

def delete_moin_caches(request, pageitem):
    # Clear cache

    # delete pagelinks
    if MOIN_VERSION > 1.6:
        arena = wikiutil.quoteWikinameFS(pageitem.page_name)
    else:
        arena = pageitem

    key = 'pagelinks'
    cache = caching.CacheEntry(request, arena, key)
    cache.remove()

    # forget in-memory page text
    pageitem.set_raw_body(None)

    # clean the in memory acl cache
    pageitem.clean_acl_cache()

    request.graphdata.cache = dict()

    # clean the cache
    for formatter_name in ['text_html']:
        key = formatter_name
        cache = caching.CacheEntry(request, arena, key)
        cache.remove()

def template_regex(request, act=False):
    if act and hasattr(request.cfg.cache, 'page_template_regexact'):
        return request.cfg.cache.page_template_regexact

    if hasattr(request.cfg.cache, 'page_template_regex'):
        return request.cfg.cache.page_template_regex

    if MOIN_VERSION > 1.6:
        if not hasattr(request.cfg, 'page_template_regex'):
            request.cfg.page_template_regex = ur'(?P<all>(?P<key>\S+)Template)'
        if act:
            request.cfg.page_template_regexact = \
                re.compile(u'^%s$' % request.cfg.page_template_regex, 
                           re.UNICODE)
            return re.compile(request.cfg.page_template_regexact, re.UNICODE)
    else:
        # For editing.py unittests
        if not hasattr(request.cfg, 'page_template_regex'):
            request.cfg.page_template_regex = u'[a-z]Template$'

    return re.compile(request.cfg.page_template_regex, re.UNICODE)

def category_regex(request, act=False):
    if act and hasattr(request.cfg.cache, 'page_category_regexact'):
        return request.cfg.cache.page_category_regexact

    if hasattr(request.cfg.cache, 'page_category_regex'):
        return request.cfg.cache.page_category_regex

    if MOIN_VERSION > 1.6:
        if not hasattr(request.cfg, 'page_category_regex'):
            request.cfg.page_category_regex = \
                ur'(?P<all>Category(?P<key>(?!Template)\S+))'
        if act:
            request.cfg.page_category_regexact = \
                re.compile(u'^%s$' % request.cfg.page_category_regex, 
                           re.UNICODE)
            return re.compile(request.cfg.page_category_regexact, re.UNICODE)
    else:
        # For editing.py unittests
        if not hasattr(request.cfg, 'page_category_regex'):
            request.cfg.page_category_regex = u'^Category[A-Z]'

    return re.compile(request.cfg.page_category_regex, re.UNICODE)
