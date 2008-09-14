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

from codecs import getencoder

from MoinMoin import config
from MoinMoin.util.lock import ReadLock

from graphingwiki.graph import Graph

# Get action name
def actionname(request, pagename):
    return '%s/%s' % (request.getScriptname(), pagename)

# Encoder from unicode to charset selected in config
encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]

# Default node attributes that should not be shown
special_attrs = ["gwikilabel", "gwikisides", "gwikitooltip", "gwikiskew",
                 "gwikiorientation", "gwikifillcolor", 'gwikiperipheries',
                 'gwikishapefile', "gwikishape", "gwikistyle"]
nonguaranteeds_p = lambda node: filter(lambda y: y not in
                                       special_attrs, dict(node))

def encode_page(page):
    return encode(page)

def decode_page(page):
    return unicode(page, config.charset)

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
        
        # The timeout parameter in ReadLock is most probably moot...
        self.request.lock = ReadLock(self.request.cfg.data_dir, timeout=10.0)
        self.request.lock.acquire()

        self.opened = True
        self.db = shelve.open(self.graphshelve)

    def closedb(self):
        if not self.opened:
            return

        self.opened = False
        if self.request.lock.isLocked():
            self.request.lock.release()
        self.db.close()

    def getpage(self, pagename):
        # Always read data here regardless of user rights -
        # they're handled in load_graph. This way the cache avoids
        # tough decisions on whether to cache content for a
        # certain user or not
        return self.db.get(encode_page(pagename), dict())

    def reverse_meta(self):
        self.keys_on_pages = {}
        self.vals_on_pages = {}
        self.vals_on_keys = {}

        for page in self:
            if page.endswith('Template'):
                continue

            value = self[page]

            for key in value.get('meta', {}):
                self.keys_on_pages.setdefault(key, set()).add(page)
                for val in value['meta'][key]:
                    val = val.strip('"')
                    val = val.replace('\\"', '"')
                    self.vals_on_pages.setdefault(val, set()).add(page)
                    self.vals_on_keys.setdefault(key, set()).add(val)

            for key in value.get('lit', {}):
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
        for key, val in page.get('meta', {}).iteritems():
            if key in special_attrs:
                setattr(node, key, ''.join(x.strip('"') for x in val))
            else:
                setattr(node, key, val)

        # Shapefile is an extra special case
        for shape in page.get('lit', {}).get('gwikishapefile', []):
            node.gwikishapefile = shape

        # Local nonexistent pages must get URL-attribute
        if not hasattr(node, 'gwikiURL'):
            node.gwikiURL = './' + pagename

        # Nodes representing existing local nodes may be traversed
        if page.has_key('saved'):
            node.gwikiURL += urladd

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
        links = page.get('in', {})
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
        links = page.get('out', {})
        for type in links:
            for dst in links[type]:
                # Filter Category, Template pages
                if self.cat_re.search(dst) or \
                       self.temp_re.search(dst):
                    continue
                # Add page and its metadata
                adata = self._add_node(dst, adata, urladd)
                adata = self._add_link(adata, (pagename, dst), type)

        return adata

    def load_with_links(self, pagename):
        return self.load_graph(pagename, '')

class Sequence:
    def __init__(self, *objs):
        self.objs = objs

    def match(self, data, bindings):
        objs = self.objs
        if not objs:
            yield (), (), data, bindings
            return

        for hobj, head, data, bindings in objs[0].match(data, bindings):
            seq = Sequence(*objs[1:])
            for tobj, tail, newdata, newbindings in seq.match(data, bindings):
                yield head+tail, head+tail, newdata, newbindings

class WikiNode(object):
    # List of startpages -> pages to which gather in-links from global
    startpages = []
    # request associated with the page
    request = None
    # url addition from action
    urladd = ""
    # globaldata
    graphdata = None

    def __init__(self, request=None, urladd=None, startpages=None):
#        print "Wiki"
        if request is not None: 
            WikiNode.request = request
        if urladd is not None:
            WikiNode.urladd = urladd
        if startpages is not None:
            WikiNode.startpages = startpages

        if request:
            WikiNode.graphdata = WikiNode.request.graphdata

    def _load(self, graph, node):
        nodeitem = graph.nodes.get(node)
        k = getattr(nodeitem, 'gwikiURL', '')

        if isinstance(k, set):
            k = ''.join(k)
            if k[0] in ['.', '/']:
                k += WikiNode.urladd
            nodeitem.gwikiURL = k

        adata = WikiNode.graphdata.load_graph(node, WikiNode.urladd)

        return adata

class HeadNode(WikiNode):
    def __init__(self, request=None, urladd=None, startpages=None):
#        print "Head"
        super(HeadNode, self).__init__(request, urladd, startpages)

    def loadpage(self, graph, node):
        # Get new data for current node
        adata = self._load(graph, node)
        if not adata:
#            print "No adata head", node
            return
        if not adata.nodes.get(node):
#            print "Wrong adata head", node
            return
        nodeitem = graph.nodes.get(node)
        nodeitem.update(adata.nodes.get(node))

        # Add new nodes, edges that link to/from the current node
        for parent, child in adata.edges.getall():
            # Only add links from amongst nodes already traversed
            if not graph.nodes.get(parent):
                continue

            newnode = graph.nodes.get(child)
            if not newnode:
                newnode = graph.nodes.add(child)
            newnode.update(adata.nodes.get(child))

            newedge = graph.edges.add(parent, child)
            edgedata = adata.edges.get(parent, child)
            newedge.update(edgedata)
            
    def match(self, data, bindings):
        nodes, graph = data
        for node in nodes:
            self.loadpage(graph, node)
            children = set(child for parent, child
                           in graph.edges.getall(parent=node))
            node = graph.nodes.get(node)
            yield node, (node,), (children, graph), bindings

class TailNode(WikiNode):
    def __init__(self, request=None, urladd=None, startpages=None):
#        print "Tail"
        super(TailNode, self).__init__(request, urladd, startpages)

    def loadpage(self, graph, node):
        # Get new data for current node
        adata = self._load(graph, node)
        if not adata:
#            print "No adata tail", node
            return
        if not adata.nodes.get(node):
#            print "Wrong adata tail", node
            return
        nodeitem = graph.nodes.get(node)
        nodeitem.update(adata.nodes.get(node))

        # Add new nodes, edges that are the parents of either the
        # current node, or the start nodes
        for parent, child in adata.edges.getall():
            if child not in [node] + WikiNode.startpages:
                continue

            newnode = graph.nodes.get(parent)
            if not newnode:
                newnode = graph.nodes.add(parent)
            newnode.update(adata.nodes.get(parent))

            newedge = graph.edges.get(parent, child)
            if not newedge:
                newedge = graph.edges.add(parent, child)
            edgedata = adata.edges.get(parent, child)
            newedge.update(edgedata)
    
    def match(self, data, bindings):
        nodes, graph = data
        for node in nodes:
            self.loadpage(graph, node)
            parents = set(parent for parent, child
                          in graph.edges.getall(child=node))
            node = graph.nodes.get(node)
            yield node, (node,), (parents, graph), bindings

def match(pattern, data):
    empty = {}
    for obj, result, data, bindings in pattern.match(data, empty):
        yield obj
