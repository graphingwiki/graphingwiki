# -*- coding: utf-8 -*-
"""
    graphrepr class
     - visualises graphs with Graphviz, interfaces with the graph-class

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
#! /usr/bin/env python
# -*- coding: latin-1 -*-

import sys
import os

from graphingwiki.patterns import encode_page, decode_page, get_url_ns
from graphingwiki.editing import ordervalue

gv_found = True

# 32bit and 64bit versions
try:
    sys.path.append('/usr/lib/graphviz/python')
    sys.path.append('/usr/local/lib/graphviz/python') # OSX
    import gv
except ImportError:
    sys.path[-1] = '/usr/lib64/graphviz/python'
    try:
        import gv
    except ImportError:
        gv_found = False
        pass

if gv_found:
    # gv needs libag to be initialised before using any read methods,
    # making a graph here seems to ensure aginit() is called
    gv.graph(' ')

import graph

# Superclass for groups of items, found under every (sub)graph
class GraphvizItemGroup(object):
    def __init__(self, graph, parent, type):
        # This is where the methods are
        self.graph  = graph
        # These items are under this (sub)graph
        self.parent = parent
        # types in ['node', 'edge', 'subg']
        self.type   = type

    def add(self, item, **attrs):
        """ Adds an item by name.

        Calls Graphviz._add with the group type and item.
        Eg. Nodes.add('2', label='heya') calls
        self.graph._add(self.parent, node='2', label='heya').
        """
        # eg. node=item to attrs, telling item type to Graphviz._setattr
        attrs[self.type] = item
        return self.graph._add(self.parent.handle, **attrs)

    def get(self, item):
        """ Returns a Graphviz.<Type> item of the named item.

        For example, graph.subg.get('first') returns a
        Graphviz.GraphvizSubgraph object of the subgraph 'first'
        """
        return self.graph._get(self.parent.handle,
                               **{self.type: item})

    def set(self, item, **attrs):
        """ Sets item attributes by name.

        Basically calls Graphviz._setattr,
        muchly the same functionality as in add().
        """
        attrs[self.type] = item
        self.graph._setattrs(self.parent.handle, **attrs)

    def unset(self, item, *list):
        """ Unsets item attributes by name.

        Well, really only sets them to "".
        """
        attrs = dict().fromkeys(list, "")
        attrs[self.type] = item
        self.graph._setattrs(self.parent.handle, **attrs)

    def delete(self, item):
        """ Dels an item by name.

        Basically calls Graphviz._del with the group type and item.
        """
        # eg. node=item to attrs, telling item type to Graphviz._setattr
        self.graph._del(self.parent.handle, **{self.type: item})

    def __iter__(self):
        """ Iterate over all items, yielding Graphviz.<type> items
        """
        handle = self.parent.handle
        cur = getattr(gv, "first%s" % self.type)(handle)
        nextitem = getattr(gv, "next%s" % self.type)
        while gv.ok(cur):
            yield self.get(gv.nameof(cur))
            cur = nextitem(handle, cur)

    def __repr__(self):
        """ Returns a dictionary of all items and their attributes """
        return str(dict(self))

# Subclasses, some overloading
class GraphvizNodes(GraphvizItemGroup):
    def __init__(self, graph, parent):
        super(GraphvizNodes, self).__init__(graph, parent, "node")

class GraphvizEdges(GraphvizItemGroup):
    def __init__(self, graph, parent):
        super(GraphvizEdges, self).__init__(graph, parent, "edge")

    def __iter__(self):
        cur = gv.firstedge(self.parent.handle)
        while gv.ok(cur):
            yield (decode_page(gv.nameof(gv.tailof(cur))), 
                   decode_page(gv.nameof(gv.headof(cur)))), \
                   dict(self.graph._iterattrs(cur))
            cur = gv.nextedge(self.parent.handle, cur)

class GraphvizSubgraphs(GraphvizItemGroup):
    def __init__(self, graph, parent):
        super(GraphvizSubgraphs, self).__init__(graph, parent, "subg")

# Superclass for single items
class GraphvizItem(object):
    def __init__(self, graph, handle):
        # This is where the methods are
        object.__setattr__(self, 'graph', graph)
        # This is the current node
        object.__setattr__(self, 'handle', handle)

    def set(self, **attrs):
        """ Sets item attributes.

        Calls Graphviz._setattrs by item handle.
        """
        self.graph._setattrs(handle=self.handle, **attrs)

    def unset(self, *list):
        """ Unsets item attributes.

        Well, really only sets them to "". Calls Graphviz_setattrs by
        item handle.
        """
        attrs = dict().fromkeys(list, "")
        self.graph._setattrs(handle=self.handle, **attrs)

    def delete(self):
        """ Deletes the item.

        Calls Graphviz._del by item handle.
        """
        self.graph._del(handle=self.handle)

    def __iter__(self):
        """ Iterates over item attributes. """
        attr = gv.firstattr(self.handle)
        while gv.ok(attr):
            yield gv.nameof(attr), \
                decode_page(gv.getv(self.handle, attr))
            attr = gv.nextattr(self.handle, attr)

    def __str__(self):
        """ Returns item name. """
        return "u'" + decode_page(gv.nameof(self.handle)) + "'"

    def __repr__(self):
        """ Returns item name and attributes.

        The output is directly usable by graph.<type>.add().
        """
        return u"(" + str(self) + ", " + str(dict(self)) + u')'

    def __setattr__(self, name, value):
        """ Sets the attribute to item using self.set """
        self.set(**{name: value})

    def __delattr__(self, name):
        """ Deletes the attribute from item using self.unset """
        self.unset(name)

    def __getattr__(self, name):
        """ Finds the named attribute, returns its value """
        handle = self.__dict__['handle']

        name = encode_page(name)

        retval = gv.getv(handle, gv.findattr(handle, name))
        # Needed mainly for dict() for work, getattribute excepts
        # and so __iter__ is called. Non-gv attrs are not returned.
        if not retval:
            object.__getattribute__(self, name)

        return decode_page(retval)        

# Subclasses, some overloading
class GraphvizNode(GraphvizItem):
    def __init__(self, graph, handle):
        super(GraphvizNode, self).__init__(graph, handle)

class GraphvizEdge(GraphvizItem):
    def __init__(self, graph, handle):
        super(GraphvizEdge, self).__init__(graph, handle)

    def __str__(self):
        return "(u'" + decode_page(gv.nameof(gv.tailof(self.handle))) + \
               "', u'" + decode_page(gv.nameof(gv.headof(self.handle))) + "')"

    def __repr__(self):
        return "(" + str(self) + ", " + str(dict(self)) + ')'

class GraphvizSubgraph(GraphvizItem):
    def __init__(self, graph, handle):
        super(GraphvizSubgraph, self).__init__(graph, handle)

        object.__setattr__(self, 'nodes', GraphvizNodes(graph, self))
        object.__setattr__(self, 'edges', GraphvizEdges(graph, self))
        object.__setattr__(self, 'subg', GraphvizSubgraphs(graph, self))

class Graphviz:
    def __init__(self, name="",
                 type="digraph", strict="",
                 engine="dot",
                 file="", string="", **attrs):

        # Initialise root graph. First, handle
        if file:
            self._read(file=file)
        elif string:
            self._read(string=string)
        elif name:
            if strict in ["", "strict"] and type in ["graph", "digraph"]:
                self.name = encode_page(name)
                self.handle = getattr(gv, "%s%s" % (strict, type))(name)
                # print "g = gv.%s%s('%s')" % (strict, type, name)
            else:
                raise "Bad args: " + str(type) + str(value)
        else:
            raise "Bad args: No name for graph"

        # Next, attributes
        if attrs:
            self._setattrs(self.handle, **attrs)

        # Then, layout options
        self.engine = engine
        # Is relayout necessary? (Initially, yes!)
        self.changed = 1

        # Finally, group classes
        self.nodes = GraphvizNodes(self, self)
        self.edges = GraphvizEdges(self, self)
        self.subg  = GraphvizSubgraphs(self, self)

    def __str__(self):
        self.layout(format='dot')
        # Temporary kludge, FIXME when gv_python improves
        return ""

    def layout(self, format="", file=""):
        """ Relayouts if needed, writes output to file, stdout or attrs. """
        # Only do relayout if changed
        format, file = map(encode_page, [format, file])

        if self.changed:
            # print "gv.layout(g, '%s')" % (self.engine)
            gv.layout(self.handle, self.engine)
            self.changed = 0

        if file:
            if not format:
                format = 'dot'
            # print "gv.render(g, '%s', '%s')" % (format, file)
            gv.render(self.handle, format, file)
        elif format:
            # Render to stdout, FIXME when gv improves
            gv.render(self.handle, format)
        else:
            # Render to attrs
            gv.render(self.handle)

    def set(self, proto="", **attrs):
        """ Sets root graph attributes. """
        self._setattrs(handle=self.handle, proto=proto, **attrs)

    # The rest are internal functions, fat and ugly. Use at your own risk!
    def _read(self, string="", file=""):
        """ Reads a graph from string, file or stdin """
        if string:
            self.handle = gv.readstring(string)
        elif file == "stdin":
            data = sys.stdin.read()
            self.handle = gv.readstring(data)
        else:
            self.handle = gv.read(file)
            # gv returns None if eg. the input does not exist
            if not self.handle:
                raise "Error with file " + file

    def _setattrs(self, handle="",
                  edge="", node="", subg="", proto="",
                  **attrs):
        """ Sets attributes for item by handle or by name and type

        Finds the item handle by type, if necessary, and sets given
        attributes.
        """
        head, tail = '', ''
        if edge:
            head, tail = edge

        node, head, tail, subg = map(encode_page, [node, head, tail, subg])

        self.changed = 1

        if proto in ["node", "edge"]:
            # Gets handle when called from Subraphs.set()
            if subg:
                handle = gv.findsubg(self.handle, subg)
            # Called by self.set() and GraphvizSubgraph.set(), handle known
            item = getattr(gv, "proto%s" % proto)(handle)
            # print "item = gv.proto" + proto + "(g)"
        elif head and tail:
            item = gv.findedge(gv.findnode(handle, head),
                               gv.findnode(handle, tail))
            # print "item = gv.findedge(gv.findnode(g, '" + head + "')," + \
            #       "gv.findnode(g, '" + tail + "'))"
        elif node:
            item = gv.findnode(handle, node)
            # print "item = gv.findnode(g, '" + node + "')"
        elif subg:
            item = gv.findsubg(handle, subg)
            # print "item = gv.findsubg(g, '" + subg + "')"
        elif handle:
            item = handle
        else:
            raise "No graph element or element type specified"

        for key, elem in attrs.iteritems():
            if isinstance(elem, set):
                for e in elem:
                    key, e = map(encode_page, [key, e])
                    gv.setv(item, key, e)
            else:
                key, elem = map(encode_page, [key, elem])
                gv.setv(item, key, elem)
            # print "gv.setv(item, '" + key + "', '" + elem + "')"

    def _iterattrs(self, handle=""):
        """ Iterate over the attributes of a graph item.

        If no handle attribute is given, iterates over the attributes
        of the root graph
        """
        if not handle:
            handle = self.handle
        attr = gv.firstattr(handle)
        while gv.ok(attr):
            yield gv.nameof(attr), decode_page(gv.getv(handle, attr))
            attr = gv.nextattr(handle, attr)

    def _add(self, handle, node="", edge="", subg="", **attrs):
        """ Adds items to parent graph (given by handle).

        Adds the item to parent Graphviz-item graph handle, sets item
        attributes as necessary and returns a Graphviz.<Type> instance.
        """
        head, tail = '', ''
        if edge:
            head, tail = edge

        node, head, tail, subg = map(encode_page, [node, head, tail, subg])

        self.changed = 1
        if head and tail:
            item = gv.edge(handle, *(head, tail))
            # print "gv.edge(g, '" + "', '".join(edge) + "')"
            graphvizitem = GraphvizEdge(self, item)
        elif node:
            item = gv.node(handle, node)
            # print "gv.node(g, '" + node + "')"
            graphvizitem = GraphvizNode(self, item)
        elif subg:
            # print "item = gv.graph(g,  '%s')" % (subg)
            item = gv.graph(handle, subg)
            graphvizitem = GraphvizSubgraph(self, item)
        else:
            raise "No graph element type specified"
        self._setattrs(handle=item, **attrs)
        return graphvizitem

    def _get(self, handle, node="", edge="", subg=""):
        """ Gets Graphviz.<Type> items from parent graph (given by handle).
        """
        # Default return value if item is not found
        head, tail = '', ''
        if edge:
            head, tail = edge

        node, head, tail, subg = map(encode_page, [node, head, tail, subg])

        graphvizitem = None
        if head and tail:
            item = gv.findedge(gv.findnode(handle, head),
                               gv.findnode(handle, tail))
            if item:
                graphvizitem = GraphvizEdge(self, item)
        elif node:
            item = gv.findnode(handle, node)
            if item:
                graphvizitem = GraphvizNode(self, item)
        elif subg:
            item = gv.findsubg(handle, subg)
            if item:
                graphvizitem = GraphvizSubgraph(self, item)
        else:
            raise "No graph element type specified"
        return graphvizitem

    def _del(self, handle="", node="", edge="", subg=""):
        """ Deletes items.

        Finds the item handle by type, if necessary, and removes the
        item from graph
        """
        head, tail = '', ''
        if edge:
            head, tail = edge

        node, head, tail, subg = map(encode_page, [node, head, tail, subg])

        self.changed = 1
        if head and tail:
            item = gv.findedge(gv.findnode(handle, head),
                               gv.findnode(handle, tail))
        elif node:
            item = gv.findnode(handle, node)
        elif subg:
            item = gv.findsubg(handle, subg)
        elif handle:
            item = handle
        else:
            raise "No graph element or element type specified"
        if item:
            gv.rm(item)

class GraphRepr(object):
    def __init__(self, graph, engine):
        object.__init__(self)

        self.graph = graph
        self.engine = engine
        self.order = 'gwikiorder'

        self.build()

    def build(self):
        # get graph attributes
        self.graphattrs = dict(self.graph)

        # if graph has no name, make one 
        self.graphattrs.setdefault("name", str(id(self)))

        # add layout engine to graphattrs
        if self.engine:
            self.graphattrs["engine"] = self.engine

        # make graph with attrs
        self.graphviz = Graphviz(**self.graphattrs)

        nodes = list(self.graph.nodes)

        # Graphviz likes to have nodes added to graph in hierarchy order
        ordered = dict()
        unordered = list()

        for node in nodes:
            item = self.graph.nodes.get(node)
            if not hasattr(item, self.order):
                unordered.append(node)
                continue

            value = getattr(item, self.order)
            ordered.setdefault(value, list()).append(node)

        nodes = list()
        for key in sorted(ordered):
            nodes.extend(ordered[key])
        nodes.extend(unordered)

        for node in nodes:
            item = self.graph.nodes.get(node)
            self.graphviz.nodes.add(node)
            self.graphviz.nodes.set(node, **self._fixattrs(item))

        for edge in self.graph.edges:
            item = self.graph.edges.get(*edge)
            self.graphviz.edges.add(edge)
            self.graphviz.edges.set(edge, **dict(item))

    def _fixattrs(self, item):
        # return attrs with empty values filtered and style attrs renamed
        out = dict()
        for key, value in item:
            if value and isinstance(value, basestring):
                if key.startswith('gwiki'):
                    key = key.replace('gwiki', '', 1)                
                out[key] = value
        return out

    def order_graph(self, ordernodes, unordernodes, request, pagename, orderby):
        # Ordering the nodes into ranks. 
        orderkeys = ordernodes.keys()
        orderkeys.sort()

        if orderby != 'gwikicategory':
            orderURL = get_url_ns(request, pagename, orderby)

        prev_ordernode = ''
        # New subgraphs, nodes to help ranking
        for key in orderkeys:
            # Get accurate representation of the key
            label = unicode(ordervalue(key))

            cur_ordernode = 'orderkey: ' + label
            sg = self.graphviz.subg.add(cur_ordernode, rank='same')

            if orderby != 'gwikicategory':
                sg.nodes.add(cur_ordernode, label=label, URL=orderURL)
            else:
                sg.nodes.add(cur_ordernode, label=label, 
                             URL=get_url_ns(request, pagename, label))

            for node in ordernodes[key]:
                sg.nodes.add(node)

            if prev_ordernode:
                self.graphviz.edges.add((prev_ordernode, cur_ordernode),
                                 dir='none', style='invis',
                                 minlen='1', weight='10')
            prev_ordernode = cur_ordernode

        # Unordered nodes to their own rank
        sg = self.graphviz.subg.add('unordered nodes', rank='same')
        sg.nodes.add('unordered nodes', style='invis')
        for node in unordernodes:
            sg.nodes.add(node)
        if prev_ordernode:
            self.graphviz.edges.add((prev_ordernode, 'unordered nodes'),
                                  dir='none', style='invis',
                                  minlen='1', weight='10')

        # Edge minimum lengths
        for edge in self.graph.edges:
            tail, head = edge
            edge = self.graphviz.edges.get(edge)
            taily = getattr(self.graphviz.nodes.get(head), 'order', '')
            heady = getattr(self.graphviz.nodes.get(tail), 'order', '')

            # Some values get special treatment
            heady = ordervalue(heady)
            taily = ordervalue(taily)

            # The order attribute is owned by neither, one or
            # both of the end nodes of the edge
            if heady == '' and taily == '':
                minlen = 0
            elif heady == '':
                minlen = orderkeys.index(taily) - len(orderkeys)
            elif taily == '':
                minlen = len(orderkeys) - orderkeys.index(heady)
            else:
                minlen = orderkeys.index(taily) - orderkeys.index(heady)

            # Redraw edge if it goes reverse wrt hierarcy
            if minlen >= 0:
                edge.set(minlen=str(minlen))
            else:
                # If there already is an edge going reverse direction,
                # update it instead of drawing a new edge.
                backedge = self.graphviz.edges.get((head, tail))
                if backedge:
                    backedge.set(minlen=str(-minlen))
                    edge.set(constraint='false')
                else:
                    backedge = self.graphviz.edges.add((head, tail))
                    backedge.set(**dict(edge.__iter__()))
                    backedge.set(**{'dir': 'back', 'minlen': str(-minlen)})
                    edge.delete()

    def __str__(self):
        return str(self.graphviz)
