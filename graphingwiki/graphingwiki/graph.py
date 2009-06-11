# -*- coding: utf-8 -*-
"""
    Graph class - a data structure to represent graphs
    * 2008-09-19 Written to emulate the old weird sync.py based contraption
                 with 10^5 times less code.

    @copyright: 2008 by Joachim Viide and
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

from codecs import getencoder

## HACK
from MoinMoin import config
# Encoder from unicode to charset selected in config
encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]

def encode_page(page):
    return encode(page)

class AttrBag(object):
    def __init__(self, **keys):
        object.__init__(self)

        self._ignored = set()
        self._ignored.update(self.__dict__)

        self.__dict__.update(keys)

    def __iter__(self):
        variables = set(self.__dict__)
        
        for key in variables:
            if key in self._ignored:
                continue
            yield key, self.__dict__[key]

    def __setattr__(self, key, value):
        # HACK
        if isinstance(key, unicode):
            key = encode_page(key)
        self.__dict__[key] = value

    def update(self, other):
        for name, value in other:
            self.__setattr__(name, value)

class Node(AttrBag):
    def __init__(self, identity, **keys):
        # Set the _identity attribute before calling the __init__ of
        # the super class, because we don't want it returned when
        # e.g. iterating.
        self._identity = identity
        AttrBag.__init__(self, **keys)

    def __unicode__(self):
        return self._identity

class Nodes(object):
    def __init__(self, graph):
        object.__init__(self)

        self.graph = graph
        self.nodes = dict()

    def add(self, identity, **keys):
        if identity not in self.nodes:
            self.nodes[identity] = Node(identity, **keys)
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
        """
        >>> edges = Edges()
        >>> e1 = edges.add(1, 2)
        >>> e2 = edges.add(1, 3)
        >>> sorted(edges)
        [(1, 2), (1, 3)]

        Adding an already existing edge just returns the already existing
        edge item:

        >>> edges.add(1, 2) is e1
        True
        >>> sorted(edges)
        [(1, 2), (1, 3)]
        """
        identity = parent, child
        if identity not in self.edges:
            self.edges[identity] = AttrBag(**keys)
            self.childDict.setdefault(parent, set()).add(child)
            self.parentDict.setdefault(child, set()).add(parent)
        return self.edges[identity]

    def delete(self, parent, child):
        """
        >>> edges = Edges()
        >>> _ = edges.add(1, 2)
        >>> _ = edges.add(1, 3)

        >>> edges.delete(1, 2)
        >>> sorted(edges)
        [(1, 3)]

        Deleting a non-existing edge does nothing:

        >>> edges.delete(7, 8)
        >>> sorted(edges)
        [(1, 3)]
        """
        identity = parent, child
        
        if identity in self.edges:
            del self.edges[identity]

            self.childDict[parent].discard(child)
            if not self.childDict[parent]:
                del self.childDict[parent]

            self.parentDict[child].discard(parent)
            if not self.parentDict[child]:
                del self.parentDict[child]

    def get(self, parent, child):
        """
        >>> edges = Edges()

        Getting a non-existing edge returns None:

        >>> edges.get(1, 2)
     
        Getting an edge naturally returns the same edge item as when adding:

        >>> e1 = edges.add(1, 2)
        >>> edges.get(1, 2) is e1
        True

        Deleting an edge also deletes the edge item. Re-adding the edge
        creates a new edge item:

        >>> edges.delete(1, 2)
        >>> _ = edges.add(1, 2)
        >>> edges.get(1, 2) is e1
        False
        """

        identity = parent, child
        return self.edges.get(identity, None)

    def children(self, parent):
        """
        >>> edges = Edges()
        >>> _ = edges.add(1, 2)
        >>> _ = edges.add(1, 3)
        >>> sorted(edges.children(1))
        [2, 3]

        >>> edges.delete(1, 2)
        >>> sorted(edges.children(1))
        [3]
        """

        return self.childDict.get(parent, set())

    def parents(self, child):
        """
        >>> edges = Edges()
        >>> _ = edges.add(1, 2)
        >>> _ = edges.add(1, 3)

        >>> sorted(edges.parents(2))
        [1]

        >>> edges.delete(1, 2)
        >>> sorted(edges.parents(2))
        []
        """

        return self.parentDict.get(child, set())

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

class Graph(Node):
    """
    >>> graph = Graph()

    >>> _ = graph.nodes.add(1)
    >>> _ = graph.nodes.add(2)
    >>> sorted(graph.nodes)
    [1, 2]
    >>> _ = graph.edges.add(1, 2)
    >>> sorted(graph.edges)
    [(1, 2)]

    Deleting a node also deletes the related edges:

    >>> graph.nodes.delete(2)
    >>> sorted(graph.nodes)
    [1]
    >>> sorted(graph.edges)
    []
    """
    def __init__(self):
        self.nodes = Nodes(self)
        self.edges = Edges()
        Node.__init__(self, '')

    def __nonzero__(self):
        return len(self.nodes) > 0

    def __repr__(self):
        out = ''

        for node in sorted(self.nodes):
            out += node
            n = self.nodes.get(node)
            out += repr(sorted(n))

        for edge in sorted(self.edges):
            out += repr(edge)
            e = self.edges.get(*edge)
            out += repr(sorted(e))

        return out

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
