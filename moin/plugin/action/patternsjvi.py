import cPickle, os, shelve
from urllib import unquote

from MoinMoin.wikiutil import quoteWikinameFS
from MoinMoin.Page import Page

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
            #node = graph.nodes.get(node)
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

    def __init__(self, request=None, urladd=None, startpages=None):
        if request is not None: 
            WikiNode.request = request
        if urladd is not None:
            WikiNode.urladd = urladd
        if startpages is not None:
            WikiNode.startpages = startpages

    def _loadpickle(self, graph, node):
        nodeitem = graph.nodes.get(node)
        k = getattr(nodeitem, 'URL', '')
        # If local link
        if not (k.startswith('./') or k.startswith('/')):
            return None
#        WikiNode.request.write("Ldata " + node + "\n")
        # and we're allowed to read it
        if not WikiNode.request.user.may.read(node):
            return None
        node = quoteWikinameFS(unquote(node))
        inc_page = Page(WikiNode.request, node)
        afn = os.path.join(inc_page.getPagePath(), 'graphdata.pickle')
        if os.path.exists(afn):
            af = file(afn)
            adata = cPickle.load(af)
            # Add navigation aids to urls of nodes with graphdata
            if not '?' in nodeitem.URL:
                nodeitem.URL += WikiNode.urladd
            return adata
        return None

    def _addinlinks(self, graph, dst):
        if dst not in WikiNode.startpages:
            return
        dstdir = unquote(dst)
        inc_page = Page(WikiNode.request, dstdir)
        graphshelve = os.path.join(inc_page.getPagePath(), '../',
                                   'graphdata.shelve')
        globaldata = shelve.open(graphshelve, 'r')
        if not globaldata['inlinks'].has_key(dst):
            # should not happen if page has graphdata
            return
        for src in globaldata['inlinks'][dst]:
            dstnode = graph.nodes.get(dst)
            if not dstnode:
                # should not happen if page has graphdata
                return
            srcnode = graph.nodes.get(src)
            if not srcnode:
                srcnode = graph.nodes.add(src)
                srcnode.URL = './' + quoteWikinameFS(unquote(src))
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
        nodeitem = graph.nodes.get(node)
        nodeitem.update(adata.nodes.get(node))

        # Add new nodes, edges that are the children of da node
#        WikiNode.request.write("Child " + node + "\n")
        for parent, child in adata.edges.getall(parent=node):
            # filter out category pages
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
        nodeitem = graph.nodes.get(node)
        nodeitem.update(adata.nodes.get(node))

        # Add new nodes, edges that are the parents of either the
        # current node, or the start nodes
        for parent, child in adata.edges.getall():
            if child in [node] + WikiNode.startpages:
                # filter out category pages
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
            # get in-links from the global shelve
            self._addinlinks(graph, node)
            # Add detailed graphdata to the search graph
            if node + "tail" not in WikiNode.loaded:
                self.loadpage(graph, node)
                WikiNode.loaded.append(node + "tail")
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
