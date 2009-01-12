# -*- coding: utf-8 -*-
"""
    patterns class

    @copyright: 2006 by Joachim Viide and
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
import UserDict
import StringIO
import cgi

from codecs import getencoder

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.util.lock import ReadLock, WriteLock
from MoinMoin.parser.wiki import Parser
from MoinMoin.action import AttachFile
from MoinMoin.Page import Page

from graphingwiki.graph import Graph

SEPARATOR = '-gwikiseparator-'

# Get action name
def actionname(request, pagename):
    return '%s/%s' % (request.getScriptname(), url_escape(pagename))

# Encoder from unicode to charset selected in config
encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]

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

# Ripped off from Parser
url_pattern = u'|'.join(config.url_schemas)

url_rule = ur'%(url_guard)s(%(url)s)\:([^\s\<%(punct)s]|([%(punct)s][^\s\<%(punct)s]))+' % {
    'url_guard': u'(^|(?<!\w))',
    'url': url_pattern,
    'punct': Parser.punct_pattern,
}

url_re = re.compile(url_rule)

def encode_page(page):
    return encode(page)

def decode_page(page):
    return unicode(page, config.charset)

def node_type(request, nodename):
    if ':' in nodename:
        if url_re.search(nodename):
            return 'url'

        start = nodename.split(':')[0]
        if start in Parser.attachment_schemas:
            return 'attachment'

        get_interwikilist(request)
        if request.iwlist.has_key(start):
            return 'interwiki'

    return 'page'

def filter_categories(request, candidates):
    # Let through only the candidates that are both valid category
    # names and WikiWords
    wordRex = re.compile("^" + Parser.word_rule + "$", re.UNICODE)

    candidates = wikiutil.filterCategoryPages(request, candidates)
    candidates = filter(wordRex.match, candidates)

    return candidates

def get_url_ns(request, pagename, link):
    # Find out subpage level to adjust URL:s accordingly
    subrank = pagename.count('/')
    # Namespaced names
    if ':' in link:
        if not hasattr(request, 'iwlist'):
            get_interwikilist(request)
        iwname = link.split(':')
        if request.iwlist.has_key(iwname[0]):
            return request.iwlist[iwname[0]] + iwname[1]
        else:
            return '../' * subrank + './InterWiki'
    # handle categories as ordernodes different
    # so that they would point to the corresponding categories
    if filter_categories(request, [link]):
        return '../' * subrank + './' + link
    else:
        return '../' * subrank + './Property' + link

def format_wikitext(request, data):
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

    if abs_method in Parser.attachment_schemas and not '/' in target:
        target = target.replace(':', ':%s/' % (name.replace(' ', '_')), 1)

    return target 

def get_interwikilist(request):
    # request.cfg._interwiki_list is gathered by wikiutil
    # the first time resolve_wiki is called
    wikiutil.resolve_wiki(request, 'Dummy:Testing')

    iwlist = dict()
    selfname = get_selfname(request)

    # Add interwikinames to namespaces
    for iw in request.cfg._interwiki_list:
        iw_url = request.cfg._interwiki_list[iw]
        if iw_url.startswith('/'):
            if iw != selfname:
                continue
            iw_url = get_wikiurl(request)
        iwlist[iw] = iw_url

    request.iwlist = iwlist

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

class GraphData(UserDict.DictMixin):
    def __init__(self, request):
        self.request = request

        # Category, Template matching regexps
        self.cat_re = re.compile(request.cfg.page_category_regex)
        self.temp_re = re.compile(request.cfg.page_template_regex)

        self.graphshelve = os.path.join(request.cfg.data_dir,
                                        'graphdata.shelve')

        if not os.path.exists(self.graphshelve):
            self.db = shelve.open(self.graphshelve, 'c')
            self.db.close()

        self.db = None
        self.opened = False
        self.writing = False
        self.lock = None
        
        self.readlock()

        self.cache = dict()

    def __getitem__(self, item):
        page = encode_page(item)

        if page not in self.cache:
            self.cache[page] = self.db[page]

        return self.cache[page]

    def __setitem__(self, item, value):
        page = encode_page(item)

        self.db[page] = value
        self.cache[page] = value

    def cacheset(self, item, value):
        page = encode_page(item)

        self.cache[page] = value

    def __delitem__(self, item):
        page = encode_page(item)

        del self.db[page]
        self.cache.pop(page, None)

    def keys(self):
        return map(decode_page, self.db.keys())

    def __iter__(self):
        return itertools.imap(decode_page, self.db)

    def __contains__(self, item):
        page = encode_page(item)
        return page in self.cache or page in self.db

    def readlock(self):
        if self.lock is None or not self.lock.isLocked():
            self.lock = ReadLock(self.request.cfg.data_dir, timeout=60.0)
            self.lock.acquire()

        if not self.opened:
            self.db = shelve.open(self.graphshelve, "r")
            self.opened = True
            self.writing = False

    def writelock(self):
        if self.opened and not self.writing:
            self.db.close()
            self.opened = False
        
        if self.lock is not None and self.lock.isLocked() \
                and isinstance(self.lock, ReadLock):
            self.lock.release()
        if self.lock is None or not self.lock.isLocked():
            self.lock = WriteLock(self.request.cfg.data_dir, 
                                  readlocktimeout=10.0)
            self.lock.acquire()

        if not self.opened or not self.writing:
            self.db = shelve.open(self.graphshelve, "c")
            self.writing = True
            self.opened = True

    def closedb(self):
        self.opened = False
        if self.lock and self.lock.isLocked():
            self.lock.release()
        self.db.close()

    def getpage(self, pagename):
        # Always read data here regardless of user rights,
        # they should be handled elsewhere.
        return self.get(pagename, dict())

    def reverse_meta(self):
        self.keys_on_pages = dict()
        self.vals_on_pages = dict()
        self.vals_on_keys = dict()

        for page in self:
            if page.endswith('Template'):
                continue

            value = self[page]

            for key in value.get('meta', dict()):
                self.keys_on_pages.setdefault(key, set()).add(page)
                for val in value['meta'][key]:
                    self.vals_on_pages.setdefault(val, set()).add(page)
                    self.vals_on_keys.setdefault(key, set()).add(val)

            for key in value.get('lit', dict()):
                self.keys_on_pages.setdefault(key, set()).add(page)
                for val in value['lit'][key]:
                    self.vals_on_pages.setdefault(val, set()).add(page)
                    self.vals_on_keys.setdefault(key, set()).add(val)

    def _add_node(self, pagename, graph, urladd="", nodetype=""):
        # Don't bother if the node has already been added
        if graph.nodes.get(pagename):
            return graph

        page = self.getpage(pagename)

        node = graph.nodes.add(pagename)
        # Add metadata
        for key, val in page.get('meta', dict()).iteritems():
            if key in SPECIAL_ATTRS:
                node.__setattr__(key, ''.join(val))
            else:
                node.__setattr__(key, val)

        # Add links as metadata
        for key, val in page.get('out', dict()).iteritems():
            if key == NO_TYPE:
                continue
            if key in SPECIAL_ATTRS:
                node.__setattr__(key, ''.join(val))
            else:
                node.__setattr__(key, val)

        # Shapefile is an extra special case
        for shape in page.get('lit', dict()).get('gwikishapefile', list()):
            node.gwikishapefile = shape
        # so is category
        node.gwikicategory = \
            page.get('out', dict()).get('gwikicategory', list())

        # Configuration for local pages next, 
        # return known to be something else
        if not nodetype == 'page':
            return graph

        # Local nonexistent pages must get URL-attribute
        if not hasattr(node, 'gwikiURL'):
            node.gwikiURL = './' + pagename

        if page.has_key('saved'):
            node.gwikiURL += urladd
        # try to be helpful and add editlinks to non-underlay pages
        elif Page(self.request, pagename).isStandardPage():
            node.gwikiURL += u"?action=edit"
            node.gwikitooltip = self.request.getText('Add page')

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

        page = self.getpage(pagename)
        if not page:
            return None

        # Make graph, initialise head node
        adata = Graph()
        if load_origin:
            adata = self._add_node(pagename, adata, urladd, 'page')
        else:
            adata.nodes.add(pagename)

        # Add links to page
        links = page.get('in', dict())
        for type in links:
            for src in links[type]:
                # Filter Category, Template pages
                if self.cat_re.search(src) or \
                       self.temp_re.search(src):
                    continue
                # Add page and its metadata
                # Currently pages can have links in them only
                # from local pages, thus nodetype == page
                adata = self._add_node(src, adata, urladd, 'page')
                adata = self._add_link(adata, (src, pagename), type)

        # Add links from page
        links = page.get('out', dict())
        lit_links = page.get('lit', dict())
        for type in links:
            for i, dst in enumerate(links[type]):
                # Filter Category, Template pages
                if self.cat_re.search(dst) or \
                       self.temp_re.search(dst):
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
                    gwikiurl = self.request.iwlist[iwname[0]] + iwname[1]
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
