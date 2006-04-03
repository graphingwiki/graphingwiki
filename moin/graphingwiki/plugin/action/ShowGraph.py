# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - ShowGraph action

    @copyright: 2005 by Juhani Eronen <exec@ee.oulu.fi>
    @license: BSD-something
"""
    
import os
from tempfile import mkstemp
from codecs import getencoder
from random import choice, seed
from base64 import b64encode
from urllib import quote as url_quote
from urllib import unquote as url_unquote

from MoinMoin import search
from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.formatter.text_html import Formatter 
from MoinMoin.parser.wiki import Parser

from graphingwiki.graph import Graph
from graphingwiki.graphrepr import GraphRepr, Graphviz
from graphingwiki.patterns import *

graphvizcolors = ["aquamarine1", "bisque", "blue", "brown4", "burlywood",
"chocolate3", "cornflowerblue", "crimson", "cyan", "darkkhaki",
"darkolivegreen3", "darksalmon", "darkseagreen", "darkslateblue",
"darkslategray", "darkviolet", "deeppink", "deepskyblue", "gray33",
"forestgreen", "gold2", "goldenrod", "gray", "green", "greenyellow",
"hotpink", "indigo", "lavender", "lightpink", "lightsalmon",
"lightseagreen", "lightskyblue", "lightsteelblue", "limegreen",
"magenta", "maroon", "mediumaquamarine", "mediumorchid1",
"mediumpurple", "mediumseagreen", "olivedrab", "orange", "orangered",
"palegoldenrod", "palegreen", "palevioletred", "peru", "plum",
"powderblue", "red2", "rosybrown", "royalblue4", "salmon",
"slategray", "springgreen", "steelblue", "tomato3", "turquoise",
"violetred", "yellow", "yellowgreen"]

colors = graphvizcolors
used_colors = []
used_colorlabels = []

def hashcolor(string):
    if string in used_colorlabels:
        return used_colors[used_colorlabels.index(string)]

    seed(string)
    cl = choice(colors)
    while cl in used_colors:
        cl = choice(colors)
    used_colors.append(cl)
    used_colorlabels.append(string)
    return cl

# Escape quotes to numeric char references, remove outer quotes.
def quoteformstr(str):
    str = str.strip("\"'")
    str = str.replace('"', '&#x22;')
    return unicode('&#x22;' + str + '&#x22;', config.charset)

def quotetoshow(str):
    return unicode(url_unquote(str), config.charset)

encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]

class GraphShower(object):
    def __init__(self, pagename, request, graphengine = "neato"):
        self.pagename = pagename
        self.request = request
        self.graphengine = graphengine

        self.pageobj = Page(request, pagename)
        self.isstandard = False
        
        self.allcategories = []
        self.categories = []
        self.startpages = []

        self.orderby = ''
        self.colorby = ''
        
        self.filteredges = set()
        self.filterorder = set()
        self.filtercolor = set()

        self.urladd = ''

        # link/node attributes that have been assigned colors
        self.coloredges = set()
        self.colornodes = set()

        # node attributes
        self.nodeattrs = set()
        # nodes that do and do not have the attribute designated with orderby
        self.ordernodes = {}
        self.unordernodes = set()

        # Node filter of an existing type
        self.oftype_p = lambda x: x != '_notype'

        # For stripping lists of quoted strings
        self.qstrip_p = lambda lst: ('"' +
                                     ','.join([x.strip('"') for x in lst]) +
                                     '"')
        self.qpirts_p = lambda txt: ['"' + x + '"' for x in
                                     txt.strip('"').split(',')]

    def formargs(self):
        request = self.request

        # Get categories for current page, for the category form
        self.allcategories = self.pageobj.getCategories(self.request)
        
        # Bail out flag on if underlay page etc.
        # FIXME: a bit hack, make consistent with other no data cases?
        if not self.pageobj.isStandardPage(includeDeleted = False):
            self.isstandard = True

        # Categories
        if request.form.has_key('categories'):
            self.categories = [encode(x) for x in request.form['categories']]

        # Orderings
        if request.form.has_key('orderby'):
            self.orderby = encode(''.join(request.form['orderby']))
            self.graphengine = 'dot'            
        if request.form.has_key('colorby'):
            self.colorby = encode(''.join(request.form['colorby']))

        # Filters
        if request.form.has_key('filteredges'):
            self.filteredges.update(
                [encode(attr) for attr in request.form['filteredges']])
        if request.form.has_key('filterorder'):
            self.filterorder.update(
                [encode(attr) for attr in request.form['filterorder']])
        if request.form.has_key('filtercolor'):
            self.filtercolor.update(
                [encode(attr) for attr in request.form['filtercolor']])

        # This is the URL addition to the nodes that have graph data
        self.urladd = '?'
        for key in request.form:
            for val in request.form[key]:
                self.urladd = (self.urladd + url_quote(key) +
                               '=' + url_quote(val) + '&')
        self.urladd = encode(self.urladd[:-1])

    def buildGraphData(self):
        graphdata = Graph()

        pagedir = self.pageobj.getPagePath()
        pagename = url_quote(encode(self.pagename))
        self.pagename = pagename

        if not self.categories:
            self.startpages = [pagename]
            root = graphdata.nodes.add(pagename)
            root.URL = './' + pagename
            return graphdata
        
        # If categories specified in form, add category pages to startpages
        for cat in self.categories:
            graphshelve = os.path.join(pagedir, '../', 'graphdata.shelve')
            globaldata = shelve.open(graphshelve, 'r')
            if not globaldata.has_key(cat):
                # graphdata not in sync on disk -> malicious input 
                # or something has gone very, very wrong
                # FIXME: Should raise an exception here and end the misery?
                break
            for newpage in globaldata[cat]:
                if not (newpage.endswith('Template') or
                    newpage.startswith('Category')):
                    self.startpages.append(newpage)
                    node = graphdata.nodes.add(newpage)
                    node.URL = './' + newpage
            globaldata.close()

        return graphdata

    def buildOutGraph(self):
        outgraph = Graph()        

        if self.orderby:
            outgraph.clusterrank = 'local'
            outgraph.compound = 'true'
            outgraph.rankdir = 'LR'

        # Add neato-specific layout stuff
        if self.graphengine == 'neato':
            outgraph.overlap = 'false'

        return outgraph

    def addToGraphWithFilter(self, graphdata, outgraph, obj1, obj2):
        # node attributes that are not guaranteed (by sync/savegraph)
        nonguaranteeds_p = lambda x: x not in ['belongs_to_patterns',
                                               'label', 'URL']

        # Get edge from match, skip if filtered
        olde = graphdata.edges.get(obj1.node, obj2.node)
        if getattr(olde, 'linktype', '_notype') in self.filteredges:
            # FIXME: What possible purpose could these lines have??
#            if hasattr(olde, 'linktype'):
#                self.filteredges.add(olde.linktype)
            return outgraph

        # Add nodes, data for ordering
        for obj in [obj1, obj2]:
            # If node already added, nothing to do
            if outgraph.nodes.get(obj.node):
                continue

            # Node filters
            for filt, doby in [(self.filterorder, self.orderby),
                               (self.filtercolor, self.colorby)]:
                # If no filters, continue
                if not doby or not filt:
                    continue

                # Filter notypes away if asked
                if not hasattr(obj, doby) and '_notype' in filt:
                    return outgraph
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
                            return outgraph

                # Filtering by single values
                target = getattr(obj, doby)
                if target.intersection(filt) != set():
                    # If so, see if any metadata is left
                    left = target.difference(filt)
                    if left:
                        setattr(obj, doby, left)
                    else:
                        return outgraph

            # update nodeattrlist with non-graph/sync ones
            self.nodeattrs.update(filter(nonguaranteeds_p, dict(obj)))
            n = outgraph.nodes.add(obj.node)
            n.update(obj)
            if self.orderby:
                value = getattr(obj, self.orderby, None)
                if value:
                    # Add to self.ordernodes by combined value of metadata
                    value = self.qstrip_p(value)
                    n._order = value
                    self.ordernodes.setdefault(value, set()).add(obj.node)
                else:
                    self.unordernodes.add(obj.node)

        # Add edge
        e = outgraph.edges.add(obj1.node, obj2.node)
        e.update(olde)

        return outgraph

    def traverseParentChild(self, addFunc, graphdata, outgraph):
        # addFunc is the function to be called for each graph addition
        # graphdata is the 'in' graph extended and traversed

        # Start pattern searches from current page +
        # nodes gathered as per form args
        nodes = set(self.startpages)

        # Init WikiNode-pattern
        WikiNode(request=self.request,
                 urladd=self.urladd,
                 startpages=self.startpages)

        # This traverses 1 to parents
        pattern = Sequence(Fixed(TailNode()),
                           Fixed(TailNode()))
        for obj1, obj2 in match(pattern, (nodes, graphdata)):
            outgraph = addFunc(graphdata, outgraph, obj2, obj1)

        # This traverses 1 to children
        pattern = Sequence(Fixed(HeadNode()),
                           Fixed(HeadNode()))
        for obj1, obj2 in match(pattern, (nodes, graphdata)):
            outgraph = addFunc(graphdata, outgraph, obj1, obj2)

        return outgraph

    def colorNodes(self, outgraph):
        colorby = self.colorby

        # If we should color nodes, gather nodes with attribute from
        # the form (ie. variable colorby) and change their colors, plus
        # gather legend data
        def updatecolors(obj):
            rule = getattr(obj, colorby, None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                rule = self.qstrip_p(rule)
                self.colornodes.add(rule)
                obj.fillcolor = hashcolor(rule)
                obj.style = 'filled'

        lazyhas = LazyConstant(lambda x, y: hasattr(x, y))

        nodes = outgraph.nodes.getall()
        node = Fixed(Node())
        cond = Cond(node, lazyhas(node, colorby))
        for obj in match(cond, (nodes, outgraph)):
            updatecolors(obj)
        return outgraph

    def colorEdges(self, outgraph):
        # Add color to edges with linktype, gather legend data
        edges = outgraph.edges.getall()
        edge = Fixed(Edge())
        pattern = Cond(edge, edge.linktype)
        for obj in match(pattern, (edges, outgraph)):
            self.coloredges.add(obj.linktype)
            obj.color = hashcolor(obj.linktype)
        return outgraph

    def fixNodeUrls(self, outgraph):
        import re
        
        # Make a different url for the page node
        node = outgraph.nodes.get(self.pagename)
        if node:
            node.URL = './\N'
        elif not outgraph.nodes.getall():
            outgraph.label = "No data"

        subrank = self.pagename.count('/')
        # Fix URLs for subpages
        if subrank > 0:
            for name, in outgraph.nodes.getall():
                node = outgraph.nodes.get(name)
                # All nodes should have URL:s, change relative ones
                if not re.search(r'^\w+:', node.URL):
                    node.URL = '../' * (subrank-1) + '.' + node.URL
            self.pagename = '../' * (subrank) + self.pagename

        return outgraph

    def circleStartNodes(self, outgraph):
        # Have bold circles on startnodes
        for node in [outgraph.nodes.get(name) for name in self.startpages]:
            if node:
                if hasattr(node, 'style'):
                    node.style = node.style + ', bold'
                else:
                    node.style = 'bold'

        return outgraph

    def orderGraph(self, gr, outgraph):
        # Now it's time to order the nodes
        # Kludges via outgraph as iterating gr.graphviz.edges bugs w/ gv_python
        orderkeys = self.ordernodes.keys()
        orderkeys.sort()

        prev_ordernode = ''
        # New subgraphs, nodes to help ranking
        for key in orderkeys:
            cur_ordernode = 'orderkey: ' + key
            sg = gr.graphviz.subg.add(cur_ordernode, rank='same')
            # [1:-1] removes quotes from label
            sg.nodes.add(cur_ordernode, label=key[1:-1])
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

    def makeLegend(self):
        # Make legend
        legendgraph = Graphviz('legend', rankdir='LR')
        legend = legendgraph.subg.add("clusterLegend", label='Legend')

        # Add nodes, edges to legend
        # Edges
        typenr = 0
        legendedges = list(self.coloredges)
        legendedges.sort()
        for linktype in legendedges:
            ln1 = "linktype: " + str(typenr)
            typenr = typenr + 1
            ln2 = "linktype: " + str(typenr)
            legend.nodes.add(ln1, style='invis', label='')
            legend.nodes.add(ln2, style='invis', label='')
            legend.edges.add((ln1, ln2), color=hashcolor(linktype),
                             label=url_unquote(linktype))

        # Nodes
        prev = ''
        legendnodes = list(self.colornodes)
        legendnodes.sort()
        for nodetype in legendnodes:
            cur = 'self.colornodes: ' + nodetype
            legend.nodes.add(cur, label=nodetype[1:-1], style='filled',
                             fillcolor=hashcolor(nodetype))
            if prev:
                legend.edges.add((prev, cur), style="invis", dir='none')
            prev = cur

        return legendgraph


    def sendForm(self):
        request = self.request

        ## Begin form
        request.write(u'<form method="GET" action="%s">\n' %
                      quotetoshow(self.pagename))
        request.write(u'<input type=hidden name=action value="%s">' %
                      ''.join(request.form['action']))

        request.write(u"<table>\n<tr>\n")

        # categories
        request.write(u"<td>\nInclude page categories:<br>\n")
        for type in self.allcategories:
            request.write(u'<input type="checkbox" name="categories" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type in self.categories and " checked>" or ">",
                           type))

        # colorby
        request.write(u"<td>\nColor by:<br>\n")
        for type in self.nodeattrs:
            request.write(u'<input type="radio" name="colorby" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.colorby and " checked>" or ">",
                           quotetoshow(type)))
        request.write(u'<input type="radio" name="colorby" ' +
                      u'value=""%s%s<br>\n' %
                      (self.colorby == '' and " checked>" or ">",
                       "no coloring"))

        # orderby
        request.write(u"<td>\nOrder by:<br>\n")
        for type in self.nodeattrs:
            request.write(u'<input type="radio" name="orderby" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.orderby and " checked>" or ">",
                           quotetoshow(type)))
        request.write(u'<input type="radio" name="orderby" ' +
                      u'value=""%s%s<br>\n' %
                      (self.orderby == '' and " checked>" or ">",
                       "no ordering"))

        # filter edges
        request.write(u'<td>\nFilter edges:<br>\n')
        alledges = list(self.coloredges) + filter(self.oftype_p,
                                                  self.filteredges)
        alledges.sort()
        for type in alledges:
            request.write(u'<input type="checkbox" name="filteredges" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type in self.filteredges and " checked>" or ">",
                           quotetoshow(type)))
        request.write(u'<input type="checkbox" name="filteredges" ' +
                      u'value="%s"%s%s<br>\n' %
                      ("_notype",
                       "_notype" in self. filteredges and " checked>" or ">",
                       "No type"))

        # filter nodes (related to colorby)
        if self.colorby:
            request.write(u'<td>\nFilter from colored:<br>\n')
            allcolor = set(filter(self.oftype_p, self.filtercolor))
            allcolor.update(self.colornodes)
            for txt in [x for x in self.colornodes if ',' in x]:
                allcolor.update(self.qpirts_p(txt))
            allcolor = list(allcolor)
            allcolor.sort()
            for type in allcolor:
                request.write(u'<input type="checkbox" name="filtercolor" ' +
                              u'value="%s"%s%s<br>\n' %
                              (quoteformstr(type),
                               type in self.filtercolor and " checked>" or ">",
                               quotetoshow(type[1:-1])))
            request.write(u'<input type="checkbox" name="filtercolor" ' +
                          u'value="%s"%s%s<br>\n' %
                          ("_notype",
                           "_notype" in self.filtercolor and " checked>" or ">",
                           "No type"))

        if self.orderby:
            # filter nodes (related to orderby)
            request.write(u'<td>\nFilter from ordered:<br>\n')
            allorder = list(set(self.ordernodes.keys() +
                                filter(self.oftype_p, self.filterorder)))
            allorder.sort()
            for type in allorder:
                request.write(u'<input type="checkbox" name="filterorder" ' +
                              u'value="%s"%s%s<br>\n' %
                              (quoteformstr(type),
                               type in self.filterorder and " checked>" or ">",
                               quotetoshow(type[1:-1])))
            request.write(u'<input type="checkbox" name="filterorder" ' +
                          u'value="%s"%s%s<br>\n' %
                          ("_notype",
                           "_notype" in self.filterorder and " checked>" or ">",
                       "No type"))
        # End form
        request.write(u"</table>\n")
        request.write(u'<input type=submit value="Submit!">\n</form>\n')


    def execute(self):
        self.formargs()
        request = self.request
        pagename = self.pagename

        request.http_headers()
        # This action generate data using the user language
        request.setContentLanguage(request.lang)

        title = request.getText('Wiki linkage as seen from "%s"') % pagename
        wikiutil.send_title(request, title, pagename = pagename)

        # Start content - IMPORTANT - without content div, there is no
        # direction support!
        formatter = Formatter(request)
        request.write(formatter.startContent("content"))
        formatter.setPage(self.pageobj)

        if self.isstandard:
            request.write(formatter.text("No graph data available."))
            request.write(formatter.endContent())
            wikiutil.send_footer(request, pagename)
            return

        # The working with patterns goes a bit like this:
        # First, get a sequence, add it to outgraph
        # Then, match from outgraph, add graphviz attrs

        # First, let's get do the desired traversal, get outgraph
        graphdata = self.buildGraphData()
        outgraph = self.buildOutGraph()
        outgraph = self.traverseParentChild(self.addToGraphWithFilter,
                                            graphdata, outgraph)

        # Stylistic stuff: Color nodes, edges, bold startpages
        if self.colorby:
            outgraph = self.colorNodes(outgraph)
        outgraph = self.colorEdges(outgraph)
        outgraph = self.circleStartNodes(outgraph)

        # Fix URL:s
        outgraph = self.fixNodeUrls(outgraph)

        # Add all data to graph
        gr = GraphRepr(outgraph, engine=self.graphengine, order='_order')

        # After this, edit gr.graphviz, not outgraph!
        outgraph.commit()

        if self.orderby:
            gr = self.orderGraph(gr, outgraph)

        legend = None
        if self.coloredges or self.colornodes:
            legend = self.makeLegend()

        self.sendForm()

        tmp_fileno, tmp_name = mkstemp()
        gr.graphviz.layout(file=tmp_name, format='png')
        f = file(tmp_name)
        img = f.read()

        gr.graphviz.layout(file=tmp_name, format='cmapx')
        f = file(tmp_name)
        mappi = f.read()

        imgbase = "data:image/png;base64," + b64encode(img)

        page = ('<img src="' + imgbase +
                '" alt="visualisation" usemap="#' +
                gr.graphattrs['name'] + '">\n' + mappi + "\n")

        request.write(page)

        if legend:
            legend.layout(file=tmp_name, format='png')
            f = file(tmp_name)
            img = f.read()
            imgbase = "data:image/png;base64," + b64encode(img)
            request.write('<img src="' + imgbase + '">\n')

        # edge pruning etc??

        # debug:
        # just to get the graph data out 
        gr.graphviz.layout(file=tmp_name)
        f = file(tmp_name)
        gtext = f.read()
        request.write(formatter.preformatted(1))
        request.write(formatter.text(gtext))
        request.write(formatter.preformatted(0))

        os.close(tmp_fileno)
        os.remove(tmp_name)

        # End content
        request.write(formatter.endContent()) # end content div
        # Footer
        wikiutil.send_footer(request, pagename)

def execute(pagename, request):
    graphshower = GraphShower(pagename, request)
    graphshower.execute()
