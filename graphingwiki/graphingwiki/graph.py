# -*- coding: utf-8 -*-
"""
    Graph class - a data structure to represent graphs
    * 2008-09-19 Written to emulate the old weird sync.py based contraption
                 with 10^5 times less code.

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

class AttrBag(object):
    def __init__(self, **keys):
        object.__init__(self)

        self._ignore = None
        self._ignore = set(self.__dict__)

        self.__dict__.update(keys)

    def __iter__(self):
        variables = set(self.__dict__)
        variables.difference_update(self._ignore)
        
        for key in variables:
            yield key, self.__dict__[key]

    def update(self, other):
        for name, value in other:
            setattr(self, name, value)

class Nodes(object):
    def __init__(self, graph):
        object.__init__(self)

        self.graph = graph
        self.nodes = dict()

    def add(self, identity, **keys):
        if identity not in self.nodes:
            self.nodes[identity] = AttrBag(**keys)
            # FIXME: get rid of these
            self.nodes[identity].node = identity
            self.nodes[identity].gwikilabel = ""
        return self.nodes[identity]

    def delete(self, identity):
        self.nodes.pop(identity, None)
        self.graph.edges._delete(identity)

    def get(self, identity):
        return self.nodes.get(identity, None)

    def __iter__(self):
        return iter(self.nodes)

    def __len__(self):
        return len(self.nodes)

class Edges(object):
    def __init__(self):
        object.__init__(self)

        self.edges = dict()
        self.childDict = dict()
        self.parentDict = dict()

    def add(self, parent, child, **keys):
        identity = parent, child
        if identity not in self.edges:
            self.edges[identity] = AttrBag(**keys)
            self.childDict.setdefault(parent, set()).add(child)
            self.parentDict.setdefault(child, set()).add(parent)
        return self.edges[identity]

    def get(self, parent, child):
        identity = parent, child
        return self.edges.get(identity, None)

    def getall(self):
        return list(self.edges)

    def children(self, parent):
        return self.childDict.get(parent, set())

    def parents(self, child):
        return self.parentDict.get(child, set())

    def delete(self, parent, child):
        identity = parent, child
        self.edges.pop(identity, None)

    def _delete(self, node):
        for child in self.childDict.pop(node, set()):
            identity = node, child
            del self.edges[identity]
        for parent in self.parentDict.pop(node, set()):
            identity = parent, node
            del self.edges[identity]

    def __iter__(self):
        return iter(self.edges)

    def __len__(self):
        return len(self.edges)

class Graph(AttrBag):
    def __init__(self):
        self.nodes = Nodes(self)
        self.edges = Edges()

        AttrBag.__init__(self)

    def __nonzero__(self):
        return len(self.nodes) > 0
