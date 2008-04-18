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
import cPickle
import os
import shelve
from codecs import getencoder
from urllib import quote as url_quote
from urllib import unquote as url_unquote

from MoinMoin.Page import Page
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
                 'gwikiURL', 'gwikishapefile', "gwikishape", "gwikistyle",
                 'belongs_to_patterns']

nonguaranteeds_p = lambda node: filter(lambda y: y not in
                                       special_attrs, dict(node))

# For stripping lists of quoted strings
qstrip_p = lambda lst: ('"' +
                        ', '.join([x.strip('"') for x in lst]) +
                        '"')
qpirts_p = lambda txt: ['"' + x + '"' for x in
                        txt.strip('"').split(', ')]

class GraphData(object):
    def __init__(self, request):
        self.request = request

        # Category, Template matching regexps
        self.cat_re = re.compile(request.cfg.page_category_regex)
        self.temp_re = re.compile(request.cfg.page_template_regex)

        self.graphshelve = os.path.join(request.cfg.data_dir,
                                        'graphdata.shelve')

        self.opened = False
        self.opendb()

    def __iter__(self):
        return iter(self.db)

    # Functions to open and close the the graph shelve for
    # current thread, creating and removing locks at the same.
    # NB: You must use closedb() before exiting to avoid littering
    #     read locks around!
    def opendb(self):
        # The timeout parameter in ReadLock is most probably moot...
        self.lock = ReadLock(self.request.cfg.data_dir, timeout=10.0)
        self.lock.acquire()
        
        self.opened = True
        self.db = shelve.open(self.graphshelve)

    def closedb(self):
        self.opened = False
        self.lock.release()

    def getpage(self, pagename):
        # Always read data here regardless of user rights -
        # they're handled in load_graph. This way the cache avoids
        # tough decisions on whether to cache content for a
        # certain user or not

        return self.db.get(pagename, dict())

    def reverse_meta(self):
        self.keys_on_pages = {}
        self.vals_on_pages = {}
        self.vals_on_keys = {}

        globaldata = dict(self.db)

        for page in globaldata:
            if page.endswith('Template'):
                continue
            for key in globaldata[page].get('meta', {}):
                self.keys_on_pages.setdefault(key, set()).add(page)
                for val in globaldata[page]['meta'][key]:
                    val = unicode(val, config.charset).strip('"')
                    val = val.replace('\\"', '"')
                    self.vals_on_pages.setdefault(val, set()).add(page)
                    self.vals_on_keys.setdefault(key, set()).add(val)

            for key in globaldata[page].get('lit', {}):
                self.keys_on_pages.setdefault(key, set()).add(page)
                for val in globaldata[page]['lit'][key]:
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
            setattr(node, key, ''.join(x.strip('"') for x in val))

        # Shapefile is an extra special case
        for shape in page.get('lit', {}).get('gwikishapefile', []):
            node.gwikishapefile = encode(shape)

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
        if not self.request.user.may.read(unicode(url_unquote(pagename),
                                                  config.charset)):
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
        if isinstance(pagename, unicode):
            pagename = url_quote(encode(pagename))
        # No urladd
        return self.load_graph(pagename, '')

class LazyItem(object):
    def __init__(self):
        pass

    def __eq__(self, obj):
        return Equal(self, obj)

    def __ne__(self, obj):
        return Not(Equal(self, obj))

    def __and__(self, obj):
        return And(self, obj)

    def __or__(self, obj):
        return Or(self, obj)

    def __invert__(self):
        return Not(self)

    def __getattr__(self, key):
        if len(key) > 4 and key.startswith("__") and key.endswith("__"):
            return object.__getattr__(self, key)
        return LazyAttribute(self, key)

    def __wrap__(self, obj):
        if isinstance(obj, LazyItem):
            return obj
        else:
            return LazyConstant(obj)

    def __call__(self, *args, **keys):        
        args = tuple(map(self.__wrap__, args))
        keys = dict(keys)
        for key in keys:
            keys[key] = self.__wrap__(keys[key])
        return LazyApply(self, args, keys)
        
    def value(self, obj, bindings):
        return obj

class LazyConstant(LazyItem):
    def __init__(self, val):
        self.val = val

    def value(self, obj, bindings):
        return self.val

    def __repr__(self):
        return " Constant "+repr(self.val)

class LazyApply(LazyItem):
    def __init__(self, func, args, keys):
        self.func = func
        self.args = args
        self.keys = keys

    def value(self, obj, bindings):
        func = self.func.value(obj, bindings)
        args = tuple(map(lambda x: x.value(obj, bindings), self.args))
        keys = dict()
        for key, value in self.keys.iteritems():
            keys[key] = value.value(obj, bindings)
        return func(*args, **keys)

class And(LazyItem):
    def __init__(self, obj1, obj2):
        self.obj1 = obj1
        self.obj2 = obj2

    def value(self, obj, bindings):
        val1 = self.obj1.value(obj, bindings)
        if not val1:
            return False
        val2 = self.obj2.value(obj, bindings)
        return val2    

Equal = LazyConstant(lambda x, y: x == y)
Not = LazyConstant(lambda x: not x)
Or = lambda x, y: Not(And(Not(x), Not(y)))
LazyAttribute = LazyConstant(lambda x, y: getattr(x, y, None))

class Fixed(LazyItem):
    def __init__(self, inner):
        self.inner = inner

    def value(self, obj, bindings):
        return bindings[self]

    def match(self, data, bindings):
        for obj, result, data, bindings in self.inner.match(data, bindings):
            if self in bindings and bindings[self] != obj:
                continue
            bindings = bindings.copy()
            bindings[self] = obj
            yield obj, result, data, bindings

class Cond:
    def __init__(self, obj, cond):
        self.obj = obj
        self.cond = cond

    def match(self, data, bindings):
        for obj, result, data, bindings in self.obj.match(data, bindings):
            value = self.cond.value(obj, bindings)
            if value:
                yield obj, result, data, bindings

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

class Epsilon:
    def __init__(self):
        pass

    def match(self, data, bindings):
        yield (), (), data, bindings

class Kleene:
    def __init__(self, obj):
        self.obj = obj
        self.eps = Epsilon()

    def match(self, data, bindings):
        def recurse(data, bindings, visited):
            for hobj, head, data, bindings in self.obj.match(data, bindings):
                if head in visited:
                    continue
                newvisited = visited.copy()
                newvisited.add(head)
                for tobj, tail, newdata, newbindings in recurse(data, bindings, newvisited):
                    yield head+tail, head+tail, newdata, newbindings
            for result in self.eps.match(data, bindings):
                yield result
        for result in recurse(data, bindings, set()):
            yield result

class Union:
    def __init__(self, *objs):
        self.objs = objs

    def match(self, data, bindings):
        for obj in self.objs:
            return obj.match(data, bindings)

class Node:
    def match(self, data, bindings):
        nodes, graph = data
        for node in nodes:
            children = set(child for parent, child in graph.edges.getall(parent = node))
            node = graph.nodes.get(*node)
            yield node, (node,), (children, graph), bindings

class Edge:
    def match(self, data, bindings):
        edges, graph = data
        for parent, child in edges:
            children = graph.edges.getall(parent = child)
            edge = graph.edges.get(parent, child)
            yield edge, (edge,), (children, graph), bindings

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
            WikiNode.graphdata = GraphData(WikiNode.request)

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

if __name__ == '__main__':
    import graph

    g = graph.Graph()
    g.nodes.add(1)
    g.nodes.add(2)
    g.nodes.add(3)
    g.edges.add(1, 2)
    g.edges.add(2, 3)
    g.edges.add(3, 1)

    nodes = set(node for node, in g.nodes.getall())

    pattern = Kleene(Node())

    for result in match(pattern, (nodes, g)):
        print result
