# -*- coding: utf-8 -*-
"""
    patterns class
     - a forwards chaining inference engine for finding graph patterns

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

from codecs import getencoder

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.util.lock import ReadLock, WriteLock
from MoinMoin.parser.wiki import Parser
from MoinMoin.action import AttachFile

from graphingwiki.graph import Graph

# Get action name
def actionname(request, pagename):
    return '%s/%s' % (request.getScriptname(), pagename)

# Encoder from unicode to charset selected in config
encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]

# Default node attributes that should not be shown
SPECIAL_ATTRS = ["gwikilabel", "gwikisides", "gwikitooltip", "gwikiskew",
                 "gwikiorientation", "gwikifillcolor", 'gwikiperipheries',
                 'gwikishapefile', "gwikishape", "gwikistyle", 'gwikiURL']
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

def format_wikitext(request, data):
    request.page.formatter = request.formatter
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

        self.opened = False
        self.opendb()

    def __getitem__(self, item):
        return self.db[encode_page(item)]

    def __setitem__(self, item, value):
        self.db[encode_page(item)] = value

    def __delitem__(self, item, value):
        del self.db[encode_page(item)]

    def keys(self):
        return map(decode_page, self.db.keys())

    def __iter__(self):
        return itertools.imap(decode_page, self.db)

    def __contains__(self, item):
        return encode_page(item) in self.db

    # Functions to open and close the the graph shelve for
    # current thread, creating and removing locks at the same.
    # Do not use directly
    def opendb(self):
        if self.opened:
            return
        
        self.readlock()

        self.opened = True
        self.db = shelve.open(self.graphshelve)

    # Locking functions centralised from various places
    def readlock(self):
        if hasattr(self.request, 'lock') and self.request.lock.isLocked():
            self.request.lock.release()
        # The timeout parameter in ReadLock is most probably moot...
        self.request.lock = ReadLock(self.request.cfg.data_dir, timeout=10.0)
        self.request.lock.acquire()

    def writelock(self):
        if self.request.lock.isLocked():
            self.request.lock.release()
        self.request.lock = WriteLock(self.request.cfg.data_dir, timeout=10.0)
        self.request.lock.acquire()

    def closedb(self):
        if not self.opened:
            return

        self.opened = False
        if self.request.lock.isLocked():
            self.request.lock.release()
        self.db.close()

    def getpage(self, pagename):
        # Always read data here regardless of user rights - they're
        # handled in load_graph and other functions using this. This
        # way the cache avoids tough decisions on whether to cache
        # content for a certain user or not
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
                    val = val.strip('"')
                    val = val.replace('\\"', '"')
                    self.vals_on_pages.setdefault(val, set()).add(page)
                    self.vals_on_keys.setdefault(key, set()).add(val)

            for key in value.get('lit', dict()):
                self.keys_on_pages.setdefault(key, set()).add(page)
                for val in value['lit'][key]:
                    val = val.strip('"')
                    self.vals_on_pages.setdefault(val, set()).add(page)
                    self.vals_on_keys.setdefault(key, set()).add(val)

    def _add_node(self, pagename, graph, urladd=""):
        # Don't bother if the node has already been added
        if graph.nodes.get(pagename):
            return graph

        page = self.getpage(pagename)

        node = graph.nodes.add(pagename)
        # Add metadata
        for key, val in page.get('meta', dict()).iteritems():
            if key in SPECIAL_ATTRS:
                setattr(node, key, ''.join(x.strip('"') for x in val))
            else:
                setattr(node, key, val)

        # Shapefile is an extra special case
        for shape in page.get('lit', dict()).get('gwikishapefile', list()):
            node.gwikishapefile = shape
        # so is category
        node.gwikicategory = page.get('out', dict()).get('gwikicategory', list())

        # Local nonexistent pages must get URL-attribute
        if not hasattr(node, 'gwikiURL'):
            node.gwikiURL = './' + pagename

        # Nodes representing existing local nodes may be traversed
        if page.has_key('saved'):
            node.gwikiURL += urladd
        # Try to be helpful and add editlinks
        else:
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

    def load_graph(self, pagename, urladd):
        if not self.request.user.may.read(pagename):
            return None

        page = self.getpage(pagename)
        if not page:
            return None

        # Make graph, initialise head node
        adata = Graph()
        adata = self._add_node(pagename, adata, urladd)

        # Add links to page
        links = page.get('in', dict())
        for type in links:
            for src in links[type]:
                # Filter Category, Template pages
                if self.cat_re.search(src) or \
                       self.temp_re.search(src):
                    continue
                # Add page and its metadata
                adata = self._add_node(src, adata, urladd)
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
                    att_page, att_file = gwikiurl.split(':')[1].split('/')

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
                adata = self._add_node(dst, adata, urladd)
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

    def load_with_links(self, pagename):
        return self.load_graph(pagename, '')

def load_children(request, graph, node, urladd):
    # Get new data for current node
    adata = request.graphdata.load_graph(node, urladd)
    if not adata:
        return list()
    if not adata.nodes.get(node):
        return list()
    nodeitem = graph.nodes.get(node)
    nodeitem.update(adata.nodes.get(node))

    children = set()

    # Add new nodes, edges that link to/from the current node
    for parent, child in adata.edges.getall(parent=node):
        newnode = graph.nodes.get(child)
        if not newnode:
            newnode = graph.nodes.add(child)
        newnode.update(adata.nodes.get(child))

        newedge = graph.edges.get(parent, child)
        if not newedge:
            newedge = graph.edges.add(parent, child)
        edgedata = adata.edges.get(parent, child)
        newedge.update(edgedata)

        children.add(child)

    return children

def load_parents(request, graph, node, urladd):
    adata = request.graphdata.load_graph(node, urladd)
    if not adata:
        return list()
    if not adata.nodes.get(node):
        return list()
    nodeitem = graph.nodes.get(node)
    nodeitem.update(adata.nodes.get(node))

    parents = set()

    # Add new nodes, edges that are the parents of either the
    # current node, or the start nodes
    for parent, child in adata.edges.getall(child=node):
        newnode = graph.nodes.get(parent)
        if not newnode:
            newnode = graph.nodes.add(parent)
        newnode.update(adata.nodes.get(parent))

        newedge = graph.edges.get(parent, child)
        if not newedge:
            newedge = graph.edges.add(parent, child)
        edgedata = adata.edges.get(parent, child)
        newedge.update(edgedata)

        parents.add(parent)

    return parents
