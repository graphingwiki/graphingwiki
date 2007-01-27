# -*- coding: iso-8859-1 -*-
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

import cPickle
import os
import shelve
from codecs import getencoder
from urllib import quote as url_quote
from urllib import unquote as url_unquote

from MoinMoin.Page import Page
from MoinMoin import config

from graphingwiki.graph import Graph

encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]

class GraphData(object):
    def __init__(self, request):
        self.request = request
        self.globaldata = self.get_shelve()
        self.loaded = {}
        
    def get_shelve(self):
        datapath = Page(self.request, u'', is_rootpage=1).getPagePath()
        graphshelve = os.path.join(datapath, 'pages/graphdata.shelve')

        # Make sure nobody is writing to graphshelve, as concurrent
        # reading and writing can result in erroneous data
        graphlock = graphshelve + '.lock'
        os.spawnlp(os.P_WAIT, 'lockfile', 'lockfile', graphlock)
        os.unlink(graphlock)

        temp_shelve = shelve.open(graphshelve, 'r')
        globaldata =  {}
        globaldata['in'] = temp_shelve['in']
        globaldata['out'] = temp_shelve['out']
        globaldata['meta'] = temp_shelve['meta']
        temp_shelve.close()

        return globaldata

    def reverse_meta(self):
        self.keys_on_pages = {}
        self.vals_on_pages = {}
        
        for page in self.globaldata['meta']:
            if page.endswith('Template'):
                continue
            for key in self.globaldata['meta'][page]:
                self.keys_on_pages.setdefault(key, set()).add(page)
                for val in self.globaldata['meta'][page][key]:
                    self.vals_on_pages.setdefault(val, set()).add(page)
        
    def load_graph(self, pagename):
        if pagename in self.loaded:
            return self.loaded[pagename]
        self.loaded[pagename] = None
#        self.request.write('load-graph:')
#        self.request.write(repr(self.request.user).replace('<', ' ').replace('>', ' ') + '<br>')        
        if not self.request.user.may.read(pagename):
            return None
        inc_page = Page(self.request, pagename)
        afn = os.path.join(inc_page.getPagePath(), 'graphdata.pickle')
        if os.path.exists(afn):
            af = file(afn)
            adata = cPickle.load(af)
            self.loaded[pagename] = adata
            return adata
        return None

    def add_global_links(self, pagename, pagegraph):
        if not pagegraph:
            pagegraph = Graph()
        if not pagegraph.nodes.get(pagename):
            pagegraph.nodes.add(pagename)

        if self.globaldata['in'].has_key(pagename):
            for src in self.globaldata['in'][pagename]:
                if not pagegraph.edges.get(src, pagename):
                    srcgraph = self.load_graph(src)
                    if srcgraph:
                        pagegraph.nodes.add(src)
                        newedge = pagegraph.edges.add(src, pagename)
                        oldedge = srcgraph.edges.get(src, pagename)
                        if oldedge:
                            newedge.update(oldedge)
        if self.globaldata['out'].has_key(pagename):
            for dst in self.globaldata['out'][pagename]:
                if not pagegraph.edges.get(pagename, dst):
                    dstgraph = self.load_graph(dst)
                    if dstgraph:
                        pagegraph.nodes.add(dst)
                        newedge = pagegraph.edges.add(pagename, dst)
                        oldedge = dstgraph.edges.get(pagename, dst)
                        if oldedge:
                            newedge.update(oldedge)
        return pagegraph

    def load_with_links(self, pagename):
        pagegraph = self.load_graph(pagename)
        if isinstance(pagename, unicode):
            pagename = url_quote(encode(pagename))
        return self.add_global_links(pagename, pagegraph)

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
    # Pages that have been loaded
    loaded = []
    # request associated with the page
    request = None
    # url addition from action
    urladd = ""
    # globaldata
    graphdata = None
    globaldata = None

    def __init__(self, request=None, urladd=None, startpages=None):
        # Zis iz not da global cache, just a tab on what's
        # been loaded in the current session
        WikiNode.loaded = []

        if request is not None: 
            WikiNode.request = request
        if urladd is not None:
            WikiNode.urladd = urladd
        if startpages is not None:
            WikiNode.startpages = startpages

        if request:
            # Start cache-like stuff
            if not WikiNode.globaldata:
                WikiNode.graphdata = GraphData(WikiNode.request)
                WikiNode.globaldata = WikiNode.graphdata.globaldata
#                request.write("Initing graphdata...<br>")
            # Update the current request (user, etc) to cache-like stuff
            else:
                WikiNode.graphdata.request = WikiNode.request
#                request.write("yeah<br>")

# Late version
#         WikiNode.graphdata = GraphData(WikiNode.request)
#         WikiNode.globaldata = WikiNode.graphdata.globaldata
    
    def _loadpickle(self, graph, node):
        nodeitem = graph.nodes.get(node)
        k = getattr(nodeitem, 'URL', '')
        # If local link
        if not k.startswith('./'):
            return None
#        self.request.write("Ldata " + node + "\n")
        # and we're allowed to read it
        node = unicode(url_unquote(node), config.charset)
        adata = WikiNode.graphdata.load_graph(node)
        # Add navigation aids to urls of nodes with graphdata
        if adata:
            if not '?' in nodeitem.URL:
                nodeitem.URL += WikiNode.urladd
        return adata

    def _addinlinks(self, graph, dst):
        # Get datapath from root page, load shelve from there
        if not WikiNode.globaldata['in'].has_key(dst):
            # should not happen if page has graphdata
            return
        for src in WikiNode.globaldata['in'][dst]:
            # filter out category, template pages
            if src.startswith('Category') or src.endswith('Template'):
                continue
            dstnode = graph.nodes.get(dst)
            if not dstnode:
                # should not happen if page has graphdata
                return
            srcnode = graph.nodes.get(src)
            if not srcnode:
                srcnode = graph.nodes.add(src)
                srcnode.URL = './' + src
            if not graph.edges.get(src, dst):
                graph.edges.add(src, dst)

    def _addoutlinks(self, graph, src):
        if not WikiNode.globaldata['out'].has_key(src):
            # should not happen if page has graphdata
            return
        for dst in WikiNode.globaldata['out'][src]:
            # filter out category, template pages
            if dst.startswith('Category') or dst.endswith('Template'):
                continue
            srcnode = graph.nodes.get(src)
            if not srcnode:
                # should not happen if page has graphdata
                return
            dstnode = graph.nodes.get(dst)
            if not dstnode:
                dstnode = graph.nodes.add(dst)
                dstnode.URL = './' + dst
            if not graph.edges.get(src, dst):
                graph.edges.add(src, dst)

class HeadNode(WikiNode):
    def __init__(self, request=None, urladd=None, startpages=None):
        super(HeadNode, self).__init__(request, urladd, startpages)

    def loadpage(self, graph, node):
        # Get new data for current node
        adata = self._loadpickle(graph, node)
        if not adata:
            return
        if not adata.nodes.get(node):
            return
        nodeitem = graph.nodes.get(node)
        nodeitem.update(adata.nodes.get(node))

        # Add new nodes, edges that link to/from the current node
        for parent, child in adata.edges.getall():
            # Only add links from amongst nodes already traversed
            if not graph.nodes.get(parent):
                continue
            # filter out category, template pages
            if (child.startswith("Category") or
                child.endswith("Template")):
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
            # Add detailed graphdata to the search graph
            if node + "head" not in WikiNode.loaded:
                self.loadpage(graph, node)
                WikiNode.loaded.append(node + "head")
            # get out-links from the global shelve
            self._addoutlinks(graph, node)
            children = set(child for parent, child
                           in graph.edges.getall(parent=node))
            node = graph.nodes.get(node)
            yield node, (node,), (children, graph), bindings

class TailNode(WikiNode):
    def __init__(self, request=None, urladd=None, startpages=None):
        super(TailNode, self).__init__(request, urladd, startpages)

    def loadpage(self, graph, node):
        # Get new data for current node
        adata = self._loadpickle(graph, node)
        if not adata:
            return
        if not adata.nodes.get(node):
            return
        nodeitem = graph.nodes.get(node)
        nodeitem.update(adata.nodes.get(node))

        # Add new nodes, edges that are the parents of either the
        # current node, or the start nodes
        for parent, child in adata.edges.getall():
            if child not in [node] + WikiNode.startpages:
                continue
            # filter out category, template pages
            if (parent.startswith("Category") or
                parent.endswith("Template")):
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
            # Add detailed graphdata to the search graph
            if node + "tail" not in WikiNode.loaded:
                self.loadpage(graph, node)
                WikiNode.loaded.append(node + "tail")
            # get in-links from the global shelve
            self._addinlinks(graph, node)
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
