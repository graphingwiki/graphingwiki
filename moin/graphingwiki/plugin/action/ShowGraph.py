# -*- coding: iso-8859-1 -*-
"""
    ShowGraph action plugin to MoinMoin

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
    
import os
import shelve
from tempfile import mkstemp
from random import choice, seed
from base64 import b64encode
from urllib import quote as url_quote
from urllib import unquote as url_unquote

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.formatter.text_html import Formatter as HtmlFormatter
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from MoinMoin.util import MoinMoinNoFooter

from MoinMoin.request import Clock
cl = Clock()

from graphingwiki.graph import Graph
from graphingwiki.graphrepr import GraphRepr, Graphviz
from graphingwiki.patterns import *

# imports from other actions
from savegraphdata import encode, local_page

# Header stuff for IE
msie_header = """Content-type: message/rfc822

From: <Graphingwiki>
Subject: A graph
Date: Sat, 8 Apr 2006 23:57:55 +0300
MIME-Version: 1.0
Content-Type: multipart/related; boundary="partboundary"; type="text/html"

--partboundary
Content-Type: text/html

"""

def add_mime_part(name, type, data):
    basdata = ''
    for x in range(1, (len(data)/64)+1):
        basdata = basdata + data[(x-1)*64:x*64] + '\n'
    basdata = basdata + data[x*64:]

    return """
--partboundary
Content-Location: %s
Content-Type: %s
Content-Transfer-Encoding: base64

%s
""" % (name, type, basdata)

msie_end = "\n--partboundary--\n\n"


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

def get_interwikilist(request):
    # request.cfg._interwiki_list is gathered by wikiutil
    # the first time resolve_wiki is called
    wikiutil.resolve_wiki(request, 'Dummy:Testing')

    iwlist = {}
    selfname = get_selfname(request)

    # Add interwikinames to namespaces
    for iw in request.cfg._interwiki_list:
        iw_url = request.cfg._interwiki_list[iw]
        if iw_url.startswith('/'):
            if iw != selfname:
                continue
            iw_url = get_wikiurl(request)
        iwlist[iw] = iw_url

    return iwlist

def get_selfname(request):
    if request.cfg.interwikiname:
        return request.cfg.interwikiname
    else:
        return 'Self'

def get_wikiurl(request):
    return request.getBaseURL() + '/'

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
def quoteformstr(text):
    text = text.strip("\"'")
    text = text.replace('"', '&#x22;')
    return unicode('&#x22;' + text + '&#x22;', config.charset)

def quotetoshow(text):
    return unicode(url_unquote(text), config.charset)

# node attributes that are not guaranteed (by sync/savegraph)
nonguaranteeds_p = lambda node: filter(lambda y: y not in
                                       ['belongs_to_patterns',
                                        'label', 'URL'], dict(node))

class GraphShower(object):
    def __init__(self, pagename, request, graphengine = "neato"):
        self.pagename = pagename
        self.request = request
        self.graphengine = graphengine
        self.available_formats = ['png', 'svg', 'dot']
        self.format = 'png'
        self.traverse = self.traverseParentChild
        self.limit = 0
        self.hidedges = 0

        self.pageobj = Page(request, pagename)
        self.isstandard = False
        self.interwikilist = []
        
        self.categories = []
        self.otherpages = []
        self.startpages = []

        self.depth = 1
        self.orderby = ''
        self.colorby = ''
        
        self.allcategories = set()
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
        self.allcategories.update(self.pageobj.getCategories(self.request))
        
        # Bail out flag on if underlay page etc.
        # FIXME: a bit hack, make consistent with other no data cases?
        if not self.pageobj.isStandardPage(includeDeleted = False):
            self.isstandard = True

        # depth
        if request.form.has_key('depth'):
            depth = [encode(x) for x in request.form['depth']][0]
            try:
                depth = int(depth)
                if depth >= 1:
                    self.depth = depth
            except ValueError:
                self.depth = 1

        # format
        if request.form.has_key('format'):
            format = [encode(x) for x in request.form['format']][0]
            if format in self.available_formats:
                self.format = format

        # Categories
        if request.form.has_key('categories'):
            self.categories = [encode(x) for x in request.form['categories']]

        # Other pages
        if request.form.has_key('otherpages'):
            otherpages = ''.join([x for x in request.form['otherpages']])
            self.otherpages = [url_quote(encode(x.strip()))
                               for x in otherpages.split(',')]

        # Limit
        if request.form.has_key('limit'):
            self.limit = 1

        # Hide edges
        if request.form.has_key('hidedges'):
            self.hidedges = 1

        # Orderings
        if request.form.has_key('orderby'):
            self.orderby = encode(''.join(request.form['orderby']))
            # Checked due to weirdo problems with ShowGraphSimple
            if self.orderby:
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
                self.urladd = (self.urladd + url_quote(encode(key)) +
                               '=' + url_quote(encode(val)) + '&')
        self.urladd = self.urladd[:-1]

    def addToStartPages(self, graphdata, pagename):
        self.startpages.append(pagename)
        root = graphdata.nodes.add(pagename)
        root.URL = './' + pagename

        return graphdata

    def addToAllCats(self, nodename):
        opageobj = Page(self.request,
                        unicode(url_unquote(nodename),
                                config.charset))
        self.allcategories.update(opageobj.getCategories(self.request))

    def buildGraphData(self):
        graphdata = Graph()

        pagedir = self.pageobj.getPagePath()
        pagename = url_quote(encode(self.pagename))
        self.pagename = pagename

        for nodename in self.otherpages:
            graphdata = self.addToStartPages(graphdata, nodename)
            self.addToAllCats(nodename)

        # Do not add self to graph if self is category or
        # template page and we're looking at categories
        if not self.categories:
            graphdata = self.addToStartPages(graphdata, pagename)
        elif not (pagename.startswith('Category') or
                  pagename.endswith('Template')):
            graphdata = self.addToStartPages(graphdata, pagename)

        # If categories specified in form, add category pages to startpages
        for cat in self.categories:
            globaldata = get_shelve(self.request)
            if not globaldata['in'].has_key(cat):
                # graphdata not in sync on disk -> malicious input 
                # or something has gone very, very wrong
                # FIXME: Should raise an exception here and end the misery?
                break
            for newpage in globaldata['in'][cat]:
                if not (newpage.endswith('Template') or
                    newpage.startswith('Category')):
                    graphdata = self.addToStartPages(graphdata, newpage)
                    self.addToAllCats(newpage)

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
        # Get edge from match, skip if filtered
        olde = graphdata.edges.get(obj1.node, obj2.node)
        if getattr(olde, 'linktype', '_notype') in self.filteredges:
            return outgraph, False

        # Add nodes, data for ordering
        for obj in [obj1, obj2]:
            # If traverse limited to startpages
            if self.limit:
                if not obj.node in self.startpages:
                    continue

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

            # update nodeattrlist with non-graph/sync ones
            self.nodeattrs.update(nonguaranteeds_p(obj))
            n = outgraph.nodes.add(obj.node)
            n.update(obj)
            
            # Add page categories to selection choices in the form
            self.addToAllCats(obj.node)

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
        if self.limit:
            if not (outgraph.nodes.get(obj1.node) and
                    outgraph.nodes.get(obj2.node)):
                return outgraph, True

        e = outgraph.edges.add(obj1.node, obj2.node)
        e.update(olde)
        if self.hidedges:
            e.style = "invis"

        return outgraph, True

    def traverseParentChild(self, addFunc, graphdata, outgraph, nodes):
        # addFunc is the function to be called for each graph addition
        # graphdata is the 'in' graph extended and traversed

        cl.start('traverseparent')
        # This traverses 1 to parents
        pattern = Sequence(Fixed(TailNode()),
                           Fixed(TailNode()))
        for obj1, obj2 in match(pattern, (nodes, graphdata)):
            outgraph, ret = addFunc(graphdata, outgraph, obj2, obj1)
        cl.stop('traverseparent')

        cl.start('traversechild')
        # This traverses 1 to children
        pattern = Sequence(Fixed(HeadNode()),
                           Fixed(HeadNode()))
        for obj1, obj2 in match(pattern, (nodes, graphdata)):
            outgraph, ret = addFunc(graphdata, outgraph, obj1, obj2)
        cl.stop('traversechild')

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
        
        # Make a different url for start nodes
        for nodename in self.startpages:
            node = outgraph.nodes.get(nodename)
            if node:
                node.URL = './\N'

        # You managed to filter out all your pages, dude!
        if not outgraph.nodes.getall():
            outgraph.label = "No data"

        subrank = self.pagename.count('/')
        # Fix URLs for subpages
        if subrank > 0:
            for name, in outgraph.nodes.getall():
                node = outgraph.nodes.get(name)
                # All nodes should have URL:s, change relative ones
                if not local_page(node.URL):
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

    def getURLns(self, link):
        if not self.interwikilist:
            self.interwikilist = get_interwikilist(self.request)
        # Namespaced names
        if ':' in link:
            iwname = link.split(':')
            if self.interwikilist.has_key(iwname[0]):
                return self.interwikilist[iwname[0]] + iwname[1]
            else:
                subrank = self.pagename.count('/')
                return '../' * subrank + './InterWiki'
        subrank = self.pagename.count('/')
        return '../' * subrank + './Property' + link

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
            sg.nodes.add(cur_ordernode, label=key[1:-1], URL=orderURL)
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
        legendgraph = Graphviz('legend', rankdir='LR', constraint='false')
        legend = legendgraph.subg.add("clusterLegend", label='Legend')
        subrank = self.pagename.count('/')
        colorURL = self.getURLns(self.colorby)

        # Add nodes, edges to legend
        # Edges
        if not self.hidedges:
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
                                 label=url_unquote(linktype),
                                 URL=self.getURLns(linktype))

        # Nodes
        prev = ''
        legendnodes = list(self.colornodes)
        legendnodes.sort()
        for nodetype in legendnodes:
            cur = 'self.colornodes: ' + nodetype
            legend.nodes.add(cur, label=nodetype[1:-1], style='filled',
                             fillcolor=hashcolor(nodetype), URL=colorURL)
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

        # outputformat
        request.write(u"<td>\nOutput format:<br>\n")
        for type in self.available_formats:
            request.write(u'<input type="radio" name="format" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.format and " checked>" or ">",
                           type))


        # Depth
        request.write(u"Link depth:<br>\n")
        request.write(u'<input type="text" name="depth" ' +
                      u'size=2 value="%s"><br>\n' % str(self.depth))

        # categories
        request.write(u"<td>Include page categories:<br>\n")
        for type in self.allcategories:
            request.write(u'<input type="checkbox" name="categories" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type in self.categories and " checked>" or ">",
                           type))

        # otherpages
        otherpages = quotetoshow(', '.join(self.otherpages))
        request.write(u"Include other pages:<br>\n")
        request.write(u'<input type="text" name="otherpages" ' +
                      u'size=20 value="%s"><br>\n' % otherpages)

        # limit
        request.write(u'<input type="checkbox" name="limit" ' +
                      u'value="1"%sShow links between these pages only<br>\n' %
                      (self.limit and ' checked>' or '>'))

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

        # hide edges
        request.write(u'<br>Hide edges: ' +
                      u'<input type="checkbox" name="hidedges" ' +
                      u'value="1"%s\n' %
                      (self.hidedges and ' checked>' or '>'))

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
            allorder = set(self.ordernodes.keys() +
                           filter(self.oftype_p, self.filterorder))
            for txt in [x for x in self.ordernodes if ',' in x]:
                allorder.update(self.qpirts_p(txt))
            allorder = list(allorder)
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

    def initTraverse(self):
        # Init WikiNode-pattern
        WikiNode(request=self.request,
                 urladd=self.urladd,
                 startpages=self.startpages)

        # Start pattern searches from current page +
        # nodes gathered as per form args
        nodes = set(self.startpages)

        return nodes

    def generateLayout(self, outgraph):
        # Add all data to graph
        gr = GraphRepr(outgraph, engine=self.graphengine, order='_order')

        # After this, edit gr.graphviz, not outgraph!
        outgraph.commit()

        if self.orderby:
            gr = self.orderGraph(gr, outgraph)

        return gr

    def getLayoutInFormat(self, graphviz, format):
        tmp_fileno, tmp_name = mkstemp()
        graphviz.layout(file=tmp_name, format=format)
        f = file(tmp_name)
        data = f.read()
        os.close(tmp_fileno)
        os.remove(tmp_name)

        return data
    
    def sendGraph(self, gr, map=False):
        img = self.getLayoutInFormat(gr.graphviz, self.format)

        if map:
            imgbase = "data:image/" + self.format + ";base64," + b64encode(img)

            page = ('<img src="' + imgbase +
                    '" alt="visualisation" usemap="#' +
                    gr.graphattrs['name'] + '">\n')
            self.sendMap(gr.graphviz)
        else:
            imgbase = "data:image/svg+xml;base64," + b64encode(img)
            
            page = ('<embed height=800 width=1024 src="' +
                    imgbase + '" alt="visualisation">\n')

        self.request.write(page)

    def sendMap(self, graphviz):
        mappi = self.getLayoutInFormat(graphviz, 'cmapx')

        self.request.write(mappi + '\n')

    def sendGv(self, gr):
        gvdata = self.getLayoutInFormat(gr.graphviz, 'dot')

        self.request.write(gvdata)

        legend = None
        if self.coloredges or self.colornodes:
            legend = self.makeLegend()

        if legend:
            img = self.getLayoutInFormat(legend, 'dot')
            self.request.write(img)

    def sendLegend(self):
        legend = None
        if self.coloredges or self.colornodes:
            legend = self.makeLegend()

        if legend:
            img = self.getLayoutInFormat(legend, self.format)
            
            if self.format == 'svg':
                imgbase = "data:image/svg+xml;base64," + b64encode(img)
                self.request.write('<embed width=800 src="' + imgbase + '">\n')
            else:
                imgbase = "data:image/" + self.format + \
                          ";base64," + b64encode(img)
                self.request.write('<img src="' + imgbase +
                                   '" alt="visualisation" usemap="#' +
                                   legend.name + '">\n')
                self.sendMap(legend)
                                   
    def sendFooter(self, formatter):
        if self.format != 'dot':
            # End content
            self.request.write(formatter.endContent()) # end content div
            # Footer
            wikiutil.send_footer(self.request, self.pagename)
        else:
            raise MoinMoinNoFooter

    def sendHeaders(self):
        request = self.request
        pagename = self.pagename

        if self.format != 'dot':
            request.http_headers()
            # This action generate data using the user language
            request.setContentLanguage(request.lang)
  
            title = request.getText('Wiki linkage as seen from "%s"') % \
                    pagename

            wikiutil.send_title(request, title, pagename=pagename)

            # Start content - IMPORTANT - without content div, there is no
            # direction support!
            formatter = HtmlFormatter(request)
            request.write(formatter.startContent("content"))
            formatter.setPage(self.pageobj)
        else:
            request.http_headers(["Content-type: text/plain;charset=%s" %
                                  config.charset])
            formatter = TextFormatter(request)
            formatter.setPage(self.pageobj)

        return formatter

    def doTraverse(self, graphdata, outgraph, nodes):
        for n in range(1, self.depth+1):
            outgraph = self.traverse(self.addToGraphWithFilter,
                                     graphdata, outgraph, nodes)
            newnodes = set([x for x, in outgraph.nodes.getall()])
            # continue only if new pages were found
            if not newnodes.difference(nodes):
                break
            nodes.update(newnodes)

        return outgraph

    def browserDetect(self):
        if 'MSIE' in self.request.getUserAgent():
            self.parts = []
            self.sendGraph = self.sendGraphIE
            self.sendLegend = self.sendLegendIE
            self.sendHeaders = self.sendHeadersIE
            self.sendFooter = self.sendFooterIE

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
        else:
            self.sendForm()
            self.sendGraph(gr, True)
            self.sendLegend()
        cl.stop('format')

        cl.stop('execute')
        # print cl.dump()

        self.sendFooter(formatter)

    # IE versions of some relevant functions

    def sendGraphIE(self, gr, map=False):
        img = self.getLayoutInFormat(gr.graphviz, self.format)
        filename = gr.graphattrs['name'] + "." + self.format

        if map:
            self.parts.append((filename,
                               'image/' + self.format,
                               b64encode(img)))
            
            page = ('<img src="' + filename +
                    '" alt="visualisation" usemap="#' +
                    gr.graphattrs['name'] + '">\n')
            self.sendMap(gr.graphviz)
        else:
            self.parts.append((filename,
                               'image/svg+xml',
                               b64encode(img)))

            page = ('<embed height=800 width=1024 src="' +
                    filename + '" alt="visualisation">\n')

        self.request.write(page)

    def sendLegendIE(self):
        legend = None
        if self.coloredges or self.colornodes:
            legend = self.makeLegend()

        if legend:
            img = self.getLayoutInFormat(legend, self.format)
            filename = legend.name + "." + self.format

            if self.format == 'svg':
                self.parts.append((filename,
                                   'image/svg+xml',
                                   b64encode(img)))

                self.request.write('<embed width=800 src="' +
                                   filename + '">\n')
            else:
                self.parts.append((filename,
                                   'image/' + self.format,
                                   b64encode(img)))
            
                self.request.write('<img src="' + filename +
                                   '" alt="visualisation" usemap="#' +
                                   legend.name + '">\n')
                self.sendMap(legend)

    def sendPartsIE(self):
        for part in self.parts:
            self.request.write(add_mime_part(*part))        

    def sendHeadersIE(self):
        request = self.request
        pagename = self.pagename

        if self.format != 'dot':
            request.write(msie_header)

            title = request.getText('Wiki linkage as seen from "%s"') % \
                    pagename
            wikiutil.send_title(request, title, pagename=pagename)

            # Start content - IMPORTANT - without content div, there is no
            # direction support!
            formatter = HtmlFormatter(request)
            request.write(formatter.startContent("content"))
            formatter.setPage(self.pageobj)
        else:
            request.http_headers(["Content-type: text/plain;charset=%s" %
                                  config.charset])
            formatter = TextFormatter(request)
            formatter.setPage(self.pageobj)

        return formatter

    def sendFooterIE(self, formatter):
        if self.format != 'dot':
            # End content
            self.request.write(formatter.endContent()) # end content div
            # Footer
            wikiutil.send_footer(self.request, self.pagename)
            self.request.write('</body></html>')
            self.sendPartsIE()
            self.request.write(msie_end)

        raise MoinMoinNoFooter

def execute(pagename, request):
    graphshower = GraphShower(pagename, request)
    graphshower.execute()
