# -*- coding: utf-8 -*-
"""
    ShowGraph action plugin to MoinMoin
     - Shows semantic data and linkage of pages in graph form

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

from ShowGraph import *

class ProcessGraphShower(GraphShower):
    def colorEdges(self, outgraph):
        # Add color to edges with linktype, gather legend data
        edges = outgraph.edges.getall()
        edge = Fixed(Edge())
        pattern = Cond(edge, edge.linktype)
        for obj in match(pattern, (edges, outgraph)):
            self.coloredges.add(obj.linktype)
            obj.label = obj.linktype
        return outgraph

    def addToGraphWithFilter(self, graphdata, outgraph, obj1, obj2):
        # If true, add the edge
        add_edge = True
        # Redo for category as metadata
        redo_node = []

        # Add categories as metadata
        if obj2.node.startswith('Category'):
            node = outgraph.nodes.get(obj1.node)
            if node:
                if hasattr(node, 'WikiCategory'):
                    node.WikiCategory.append(obj2.node)
                else:
                    node.WikiCategory = [obj2.node]
                obj1.WikiCategory = node.WikiCategory
            else:
                obj1.WikiCategory = [obj2.node]
            self.nodeattrs.add('WikiCategory')
            add_edge = False
            redo_node.append(obj1.node)

        # Get edge from match, skip if filtered
        olde = graphdata.edges.get(obj1.node, obj2.node)
        if getattr(olde, 'linktype', '_notype') in self.filteredges:
            return outgraph, False

        # Add nodes, data for ordering
        for obj in [obj1, obj2]:
            # Do not process categories here
            if obj.node.startswith('Category'):
                continue

            # If traverse limited to startpages
            if self.limit == 'start':
                if not obj.node in self.startpages:
                    continue
            # or to pages within the wiki
            elif self.limit == 'wiki':
                if not obj.URL[0] in ['.', '/']:
                    continue

            # If node already added, nothing to do
            if outgraph.nodes.get(obj.node) and obj.node not in redo_node:
                continue

            # Node filters
            for filt, doby in [(self.filterorder, self.orderby),
                               (self.filtercolor, self.colorby)]:
                # If no filters, continue
                if not doby or not filt:
                    continue

                # Filter notypes away if asked
                if not hasattr(obj, doby) and '_notype' in filt:
                    return outgraph, False
                elif not hasattr(obj, doby):
                    continue

                # Filtering by multiple metadata values
                target = getattr(obj, doby)
                for rule in [set(self.qpirts_p(x)) for x in filt if ',' in x]:
                    if rule == rule.intersection(target):
                        left = target.difference(rule)
                        if left:
                            setattr(obj, doby, left)
                        else:
                            return outgraph, False

                # Filtering by single values
                target = getattr(obj, doby)
                if target.intersection(filt) != set():
                    # If so, see if any metadata is left
                    left = target.difference(filt)
                    if left:
                        setattr(obj, doby, left)
                    else:
                        return outgraph, False

            # Strip if the node has been added to other order-key
            n = outgraph.nodes.get(obj.node)
            if n:
                if hasattr(n, '_order'):
                    self.ordernodes[n._order].discard(obj.node)
                    if self.ordernodes[n._order] == set():
                        del self.ordernodes[n._order]
            else:
                # update nodeattrlist with non-graph/sync ones
                self.nodeattrs.update(nonguaranteeds_p(obj))
                n = outgraph.nodes.add(obj.node)
                n.update(obj)

            # Add page categories to selection choices in the form
            self.addToAllCats(obj.node)

            if self.orderby:
                value = getattr(obj, self.orderby, None)
                if value:
                    # Strip if the node has been added to unordered
                    self.unordernodes.discard(obj.node)
                    # Add to self.ordernodes by combined value of metadata
                    value = self.qstrip_p(value)
                    n._order = value
                    self.ordernodes.setdefault(value, set()).add(obj.node)
                else:
                    self.unordernodes.add(obj.node)

        # Add edge
        if self.limit:
            if not (outgraph.nodes.get(obj1.node) and
                    outgraph.nodes.get(obj2.node)):
                return outgraph, True

        if add_edge:
            e = outgraph.edges.add(obj1.node, obj2.node)
            e.update(olde)
            if self.hidedges:
                e.style = "invis"

        return outgraph, True

    def orderGraph(self, gr, outgraph):
        # Now it's time to order the nodes
        # Kludges via outgraph as iterating gr.graphviz.edges bugs w/ gv_python
        orderkeys = self.ordernodes.keys()
        orderkeys.sort()
        orderURL = self.getURLns(self.orderby)

        prev_ordernode = ''
        # New subgraphs, nodes to help ranking
        for key in orderkeys:
            cur_ordernode = 'orderkey: ' + key
            sg = gr.graphviz.subg.add(cur_ordernode, rank='same')
            # [1:-1] removes quotes from label
            sg.nodes.add(cur_ordernode, shape='point', style='invis')
            for node in self.ordernodes[key]:
                sg.nodes.add(node)

            if prev_ordernode:
                gr.graphviz.edges.add((prev_ordernode, cur_ordernode),
                                 dir='none', style='invis',
                                 minlen='1', weight='10')
            prev_ordernode = cur_ordernode

        # Unordered nodes to their own rank
        sg = gr.graphviz.subg.add('unordered nodes', rank='same')
        sg.nodes.add('unordered nodes', style='invis')
        for node in self.unordernodes:
            sg.nodes.add(node)
        if prev_ordernode:
            gr.graphviz.edges.add((prev_ordernode, 'unordered nodes'),
                                  dir='none', style='invis',
                                  minlen='1', weight='10')
                                  
        # Edge minimum lengths
        for edge in outgraph.edges.getall():
            tail, head = edge
            edge = gr.graphviz.edges.get(edge)
            taily = getattr(gr.graphviz.nodes.get(head), '_order', '')
            heady = getattr(gr.graphviz.nodes.get(tail), '_order', '')
            # The order attribute is owned by neither, one or
            # both of the end nodes of the edge
            if not heady and not taily:
                minlen = 0
            elif not heady:
                minlen = orderkeys.index(taily) - len(orderkeys)
            elif not taily:
                minlen = len(orderkeys) - orderkeys.index(heady)
            else:
                minlen = orderkeys.index(taily) - orderkeys.index(heady)

            # Redraw edge if it goes reverse wrt hierarcy
            if minlen >= 0:
                edge.set(minlen=str(minlen))
            else:
                backedge = gr.graphviz.edges.get((head, tail))
                if backedge:
                    backedge.set(minlen=str(-minlen))
                    edge.set(constraint='false')
                else:
                    backedge = gr.graphviz.edges.add((head, tail))
                    backedge.set(**dict(edge.__iter__()))
                    backedge.set(**{'dir': 'back', 'minlen': str(-minlen)})
                    edge.delete()

        return gr

    def execute(self):        
        cl.start('execute')
        self.formargs()

        self.browserDetect()

        formatter = self.sendHeaders()

        if self.isstandard:
            self.request.write(formatter.text("No graph data available."))
            self.request.write(formatter.endContent())
            wikiutil.send_footer(self.request, self.pagename)
            return

        # The working with patterns goes a bit like this:
        # First, get a sequence, add it to outgraph
        # Then, match from outgraph, add graphviz attrs

        cl.start('build')
        # First, let's get do the desired traversal, get outgraph
        graphdata = self.buildGraphData()
        outgraph = self.buildOutGraph()
        cl.stop('build')

        cl.start('traverse')
        nodes = self.initTraverse()
        outgraph = self.doTraverse(graphdata, outgraph, nodes)
        cl.stop('traverse')

        cl.start('layout')
        # Stylistic stuff: Color nodes, edges, bold startpages
        if self.colorby:
            outgraph = self.colorNodes(outgraph)
        outgraph = self.colorEdges(outgraph)
        outgraph = self.circleStartNodes(outgraph)

        # Fix URL:s
        outgraph = self.fixNodeUrls(outgraph)

        # Do the layout
        gr = self.generateLayout(outgraph)
        cl.stop('layout')

        cl.start('format')
        if self.format == 'svg':
            self.sendForm()
            self.sendGraph(gr)
            self.sendLegend()
        elif self.format == 'dot':
            self.sendGv(gr)
        elif self.format == 'png':
            self.sendForm()
            self.sendGraph(gr, True)
        else:
            self.sendForm()
            self.request.write(formatter.paragraph(1))
            self.request.write(formatter.text("Nodes in graph: " + str(len(
                outgraph.nodes.getall()))))
            self.request.write(formatter.paragraph(0))
            self.request.write(formatter.paragraph(1))
            self.request.write(formatter.text("Edges in graph: " + str(len(
                outgraph.edges.getall()))))
            self.request.write(formatter.paragraph(0))
            if self.orderby:
                self.request.write(formatter.paragraph(1))
                self.request.write(formatter.text("Order levels: " + str(len(
                    self.ordernodes.keys()))))
                self.request.write(formatter.paragraph(0))

        cl.stop('format')

        cl.stop('execute')
        # print cl.dump()

        self.sendFooter(formatter)

def execute(pagename, request):
    graphshower = ProcessGraphShower(pagename, request)
    graphshower.execute()
