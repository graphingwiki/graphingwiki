# -*- coding: utf-8 -*-
"""
    graph class
     - a data structure to represent graphs

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
from sync import Sync

class Graph(Sync):
    def __init__(self):
        Sync.__init__(self,
                      (
                         ("edges",
                          ("parent", "child"),
                          ()
                         ),
                         ("nodes",
                          ("node",),
                          ((("gwikilabel", ""),))
                         ) # nodes
                      ) #tables
                     ) #self

        self.connections = {}
        self.edges.addhandler += self.__addedge
        self.edges.delhandler += self.__deledge
        self.nodes.addhandler += self.__addnode
        self.nodes.delhandler += self.__delnode

    def __iter__(self):
        import re
        # grab local variables not from sync or __init__
        for key in filter(lambda x: not
                          re.match(r'addhandler|delhandler|commithandler|' + \
                                   r'listeners|listened|tablenames|order|' + \
                                   r'connections|nodes|edges|_Sync.+', x),
                          self.__dict__.keys()):
            yield key, self.__dict__[key]

    def __disconnect(self, node1, node2):
 	if node1 not in self.connections:
 	    return
 	if node2 not in self.connections:
 	    return        

 	current = set()
 	current.add(node1)

        total = set()
 	while current:
 	    next = set()
 	    for node in current:
                for parent, child in self.edges.getall(parent = node):
 		    next.add(child)
 		for parent, child in self.edges.getall(child = node):
 		    next.add(parent)
            total.update(current)
            current = next - total

        if len(total) == len(self.connections[node1]):
            return

        for node in total:
            self.connections[node] = total

        total = self.connections[node2] - total
        for node in total:
            self.connections[node] = total

    def __connect(self, parent, child):
        children = self.connections[child]
        parents = self.connections[parent]

        if children is parents:
            return

        children.update(parents)
        for node in parents:
            self.connections[node] = children

    def __addnode(self, table, attributes, node):
        self.connections[node] = set()
        self.connections[node].add(node)
        
    def __delnode(self, table, attributes, node):
        self.edges.deleteall(parent = node)
        self.edges.deleteall(child = node)	
        del self.connections[node]

    def __addedge(self, table, attributes, parent, child):
        if not self.nodes.has(parent) or not self.nodes.has(child):
            self.edges.delete(parent, child)
            raise Exception, "Can't add an edge for a node not in the graph"
        self.__connect(parent, child)

    def __deledge(self, table, attributes, parent, child):
        self.__disconnect(parent, child)

if __name__ == '__main__':
    g = Graph()
    g.nodes.add(1).label = "blah"
    g.nodes.add(2)
    g.nodes.add(3)
    g.nodes.add(4)    
    g.edges.add(1, 2)
    g.edges.add(3, 4)

    g.edges.add(2, 3)

    g.edges.delete(3, 4)

    print "X"
    print g.nodes.getall(label = "blah")
