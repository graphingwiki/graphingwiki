# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - ShowGraph action

    @copyright: 2005 by Juhani Eronen <exec@ee.oulu.fi>
    @license: BSD-something
"""
    
import re, os, cPickle, tempfile
from codecs import getencoder
from random import choice, seed
from base64 import b64encode
from urllib import quote

from MoinMoin import search
from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.formatter.text_html import Formatter 
from MoinMoin.parser.wiki import Parser

# cpe imports
from graph import Graph
from graphrepr import GraphRepr, Dot
from patternsjvi import *

dotcolors = ["aquamarine1", "bisque", "blue", "brown4", "burlywood",
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

colors = dotcolors
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

def execute(pagename, request):
    _ = request.getText
    request.http_headers()

    # Encoder from unicode to charset selected in config
    encoder = getencoder(config.charset)
    def _e(str):
        return encoder(str, 'replace')[0]

    # This action generate data using the user language
    request.setContentLanguage(request.lang)

    wikiutil.send_title(request, _('Wiki linkage as seen from "%s"') %
                        pagename, pagename=pagename)

    pageobj = Page(request, pagename)
    pagedir = pageobj.getPagePath()

    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    formatter = Formatter(request)
    request.write(formatter.startContent("content"))
    formatter.setPage(pageobj)

    graphengine = 'neato'

    # Init search graph, output graph, start node and its path
    pagename = _e(pagename)
    pagefilename = wikiutil.quoteWikinameFS(pagename)
    pagename = quote(pagename)
    graphdata = Graph()
    outgraph = Graph()
    nodeitem = graphdata.nodes.add(pagename)
    nodeitem.URL = './' + pagefilename

    # Handling form arguments
    # include otherpages, include pages with certain metadata?
    # engine, (dot, neato, circo)
    # search depth?

    # Get categories for current page, for the category form
    allcategories = pageobj.getCategories(request)

    categories = []
    startpages = [pagename]

    # categories as received from the form
    if request.form.has_key('categories'):
        categories = [_e(x) for x in request.form['categories']]

    # If categories specified in form, add category pages to startpages
    for cat in categories:
        graphshelve = os.path.join(pagedir, '../', 'graphdata.shelve')
        globaldata = shelve.open(graphshelve, 'r')
        if not globaldata['categories'].has_key(cat):
            # graphdata not in sync on disk -> malicious input 
            # or something has gone very, very wrong
            break
        for newpage in globaldata['categories'][cat]:
            if newpage != pagename:
                startpages.append(newpage)
                n = graphdata.nodes.add(newpage)
                n.URL = './' + newpage

    # Other form variables
    colorby = ''
    if request.form.has_key('colorby'):
        colorby = _e(''.join(request.form['colorby']))

    orderby = ''
    if request.form.has_key('orderby'):
        orderby = _e(''.join(request.form['orderby']))
        graphengine = 'dot'
        outgraph.clusterrank = 'local'
        outgraph.compound = 'true'
        outgraph.rankdir = 'LR'

    filteredges = set()
    if request.form.has_key('filteredges'):
        filteredges.update([_e(attr) for attr in request.form['filteredges']])

    filterorder = set()
    if request.form.has_key('filterorder'):
        filterorder.update([_e(attr) for attr in request.form['filterorder']])

    filtercolor = set()
    if request.form.has_key('filtercolor'):
        filtercolor.update([_e(attr) for attr in request.form['filtercolor']])

    # This is the URL addition to the nodes that have graph data
    urladd = "?" + '&'.join([str(x + "=" + ''.join(request.form[x]))
                             for x in request.form])

    # link/node attributes that have been assigned colors
    coloredges = set()
    colornodes = set()

    # node attributes that are not guaranteed
    nonguaranteeds_p = lambda x: x not in ['belongs_to_patterns',
                                           'label', 'URL']

    # Node filter of an existing type
    oftype_p = lambda x: x != '_notype'

    # node attributes
    nodeattrs = set()
    # nodes that do and do not have the attribute designated with orderby
    ordernodes = {}
    unordernodes = set()

    # Start pattern searches from current page +
    # nodes gathered as per form args
    nodes = set(startpages)

    # The working with patterns goes a bit like this:
    # First, get a sequence, add it to outgraph
    # Then, match from outgraph, add dot attrs

    def addseqtograph(obj1, obj2, dir='out'):
        # Get edge from match, skip if filtered
        edge = [obj1.node, obj2.node]
        if dir == 'in':
            edge.reverse()
        olde = graphdata.edges.get(*edge)
        if getattr(olde, 'linktype', '_notype') in filteredges:
            if hasattr(olde, 'linktype'):
                filteredges.add(olde.linktype)
            return

        # Add nodes, data for ordering
        for obj in [obj1, obj2]:
            # filter
            if getattr(obj, orderby, '_notype') in filterorder:
                if hasattr(obj, orderby):
                    filterorder.add(getattr(obj, orderby))
                return
            if getattr(obj, colorby, '_notype') in filtercolor:
                if hasattr(obj, colorby):
                    filtercolor.add(getattr(obj, colorby))
                return
            if outgraph.nodes.get(obj.node):
                continue
            nodeattrs.update(filter(nonguaranteeds_p, dict(obj)))
            n = outgraph.nodes.add(obj.node)
            n.update(obj)
            if orderby:
                value = getattr(obj, orderby, None)
                if value:
                    if ordernodes.has_key(value):
                        ordernodes[value].add(obj.node)
                    else:
                        ordernodes[value] = set([obj.node])
                else:
                    unordernodes.add(obj.node)

        # Add edge
        e = outgraph.edges.add(*edge)
        e.update(olde)

    # The following code traverses 1 to children
    # Init WikiNode at the same
    pattern = Sequence(Fixed(HeadNode(request=request, urladd=urladd,
                                      startpages=startpages)),
                       Fixed(HeadNode()))
    for obj1, obj2 in match(pattern, (nodes, graphdata)):
        addseqtograph(obj1, obj2)

    # This traverses 1 to parents
    pattern = Sequence(Fixed(TailNode()),
                       Fixed(TailNode()))
    for obj1, obj2 in match(pattern, (nodes, graphdata)):
        addseqtograph(obj1, obj2, 'in')

    # If we should color nodes, gather nodes with attribute from
    # the form (ie. variable colorby) and change their colors, plus
    # gather legend data
    if colorby:
        def updatecolors(obj1, obj2):
            rule = getattr(obj1, colorby, None)
            color = getattr(obj1, 'fillcolor', None)
            if rule and not color:
                colornodes.add(rule)
                obj1.fillcolor = hashcolor(rule)
                obj1.style = 'filled'
                n = outgraph.nodes.get(obj1.node)
                n.fillcolor = obj1.fillcolor
                n.style = 'filled'

            rule = getattr(obj2, colorby)
            color = getattr(obj2, 'fillcolor', None)
            if not color:
                colornodes.add(rule)
                obj2.fillcolor = hashcolor(rule)
                obj2.style = 'filled'
                n = outgraph.nodes.get(obj2.node)
                n.fillcolor = obj2.fillcolor
                n.style = 'filled'

        lazyhas = LazyConstant(lambda x, y: hasattr(x, y))

        # no need to gather more in-links, clear startpages
        node1 = Fixed(HeadNode(startpages=[]))
        node2 = Fixed(HeadNode())
        cond2 = Cond(node2, lazyhas(node2, colorby))
        pattern = Sequence(node1, cond2)
        for obj1, obj2 in match(pattern, (nodes, outgraph)):
            updatecolors(obj1, obj2)

        node1 = Fixed(TailNode())
        node2 = Fixed(TailNode())
        cond1 = Cond(node1, lazyhas(node1, colorby))
        pattern = Sequence(cond1, node2)
        for obj1, obj2 in match(pattern, (nodes, outgraph)):
            updatecolors(obj2, obj1)

    # Add color to edges with linktype, gather legend data
    edges = outgraph.edges.getall()
    edge = Fixed(Edge())
    pattern = Cond(edge, edge.linktype)
    for obj in match(pattern, (edges, outgraph)):
        coloredges.add(obj.linktype)
        obj.color = hashcolor(obj.linktype)

    # Make a different url for the page node
    node = outgraph.nodes.get(pagename)
    if not node:
        outgraph.label = "No data"
    else:
        node.URL = './\N'

    # Add all data to graph
    gr = GraphRepr(outgraph, engine=graphengine, order=orderby)

    # Set proto attributes before graph commit to affect all items
    if graphengine == 'neato':
        gr.dot.set(proto='edge', len='3')

    # Make legend
    if coloredges or colornodes:
        legendgraph = Dot('legend', rankdir='LR')
        legend = legendgraph.subg.add("clusterLegend", label='Legend')

    # After this, edit gr.dot, not outgraph!
    outgraph.commit()

    # Now it's time to order the nodes
    # Kludges via outgraph as iterating gr.dot.edges bugs w/ gv_python
    if orderby:
        orderkeys = ordernodes.keys()
        orderkeys.sort()

        prev_ordernode = ''
        # New subgraphs, nodes to help ranking
        for key in orderkeys:
            cur_ordernode = 'orderkey: ' + key
            sg = gr.dot.subg.add(cur_ordernode, rank='same')
            sg.nodes.add(cur_ordernode)
            gr.dot.nodes.add(cur_ordernode, label=key)
            for node in ordernodes[key]:
                sg.nodes.add(node)

            if prev_ordernode:
                gr.dot.edges.add((prev_ordernode, cur_ordernode),
                                 dir='none', style='invis',
                                 minlen='1', weight='10')
            prev_ordernode = cur_ordernode

        # Edge minimum lengths
        for edge in outgraph.edges.getall():
            tail, head = edge
            edge = gr.dot.edges.get(edge)
            taily = getattr(gr.dot.nodes.get(head), orderby, '')
            heady = getattr(gr.dot.nodes.get(tail), orderby, '')
            # The order attribute is owned by neither, one or
            # both of the end nodes of the edge
            if not heady and not taily:
                minlen = 0
            elif not heady:
                minlen = len(orderkeys) - orderkeys.index(taily)
            elif not taily:
                minlen = len(orderkeys) - orderkeys.index(heady)
            else:
                minlen = orderkeys.index(heady) - orderkeys.index(taily)

            # Redraw edge if it goes reverse wrt hierarcy
            if minlen >= 0:
                edge.set(minlen=str(minlen))
            else:
                backedge = gr.dot.edges.get((head, tail))
                if backedge:
                    backedge.set(minlen=str(-minlen))
                else:
                    backedge = gr.dot.edges.add((head, tail))
                    backedge.set(**dict(edge.__iter__()))
                    backedge.set(**{'dir': 'back', 'minlen': str(-minlen)})
                    edge.delete()

    # Add nodes, edges to legend
    # Edges
    typenr = 0
    legendedges = list(coloredges)
    legendedges.sort()
    for linktype in legendedges:
        ln1 = "linktype: " + str(typenr)
        typenr = typenr + 1
        ln2 = "linktype: " + str(typenr)
        legend.nodes.add(ln1, style='invis', label='')
        legend.nodes.add(ln2, style='invis', label='')
        legend.edges.add((ln1, ln2), color=hashcolor(linktype),
                         label=linktype)

    # Nodes
    prev = ''
    legendnodes = list(colornodes)
    legendnodes.sort()
    for nodetype in legendnodes:
        cur = 'colornodes: ' + nodetype
        legend.nodes.add(cur, label=nodetype, style='filled',
                         fillcolor=hashcolor(nodetype))
        if prev:
            legend.edges.add((prev, cur), style="invis", dir='none')
        prev = cur

    # Escape quotes to numeric char references, remove outer quotes.
    def _quoteformstr(str):
        str = str.strip("\"'")
        str = str.replace('"', '&#x22;')
        return _e('&#x22;' + str + '&#x22;')

    # Begin form
    request.write(u'<form method="GET" action="%s">\n' % pagename)
    request.write(u'<input type=hidden name=action value="%s">' %
                  ''.join(request.form['action']))

    request.write(u"<table>\n<tr>\n")

    # categories
    request.write(u"<td>\nInclude page categories:<br>\n")
    for type in allcategories:
        request.write(u'<input type="checkbox" name="categories" ' +
                      u'value="%s"%s%s<br>\n' %
                      (type, type in categories and " checked>" or ">",
                       type))

    # colorby
    request.write(u"<td>\nColor by:<br>\n")
    for type in nodeattrs:
        request.write(u'<input type="radio" name="colorby" ' +
                      u'value="%s"%s%s<br>\n' %
                      (type, type == colorby and " checked>" or ">",
                       type))
    request.write(u'<input type="radio" name="colorby" ' +
                  u'value=""%s%s<br>\n' %
                  (colorby == '' and " checked>" or ">",
                   "no coloring"))

    # orderby
    request.write(u"<td>\nOrder by:<br>\n")
    for type in nodeattrs:
        request.write(u'<input type="radio" name="orderby" ' +
                      u'value="%s"%s%s<br>\n' %
                      (type, type == orderby and " checked>" or ">",
                       type))
    request.write(u'<input type="radio" name="orderby" ' +
                  u'value=""%s%s<br>\n' %
                  (orderby == '' and " checked>" or ">",
                   "no ordering"))

    # filter edges
    request.write(u'<td>\nFilter edges:<br>\n')
    alledges = list(coloredges) + filter(oftype_p, filteredges)
    alledges.sort()
    for type in alledges:
        request.write(u'<input type="checkbox" name="filteredges" ' +
                      u'value="%s"%s%s<br>\n' %
                      (type, type in filteredges and " checked>" or ">",
                       type))
    request.write(u'<input type="checkbox" name="filteredges" ' +
                  u'value="%s"%s%s<br>\n' %
                  ("_notype", "_notype" in filteredges and " checked>"
                   or ">", "No type"))

    # filter nodes (related to colorby)
    if colorby:
        request.write(u'<td>\nFilter from colored:<br>\n')
        allcolor = list(colornodes) + filter(oftype_p, filtercolor)
        allcolor.sort()
        for type in allcolor:
            request.write(u'<input type="checkbox" name="filtercolor" ' +
                          u'value="%s"%s%s<br>\n' %
                          (_quoteformstr(type),
                           type in filtercolor and " checked>" or ">",
                           type))
        request.write(u'<input type="checkbox" name="filtercolor" ' +
                      u'value="%s"%s%s<br>\n' %
                      ("_notype", "_notype" in filtercolor and " checked>"
                       or ">", "No type"))

    # filter nodes (related to orderby)
    if orderby:
        request.write(u'<td>\nFilter from ordered:<br>\n')
        allorder = ordernodes.keys() + filter(oftype_p, filterorder)
        allorder.sort()
        for type in allorder:
            request.write(u'<input type="checkbox" name="filterorder" ' +
                          u'value="%s"%s%s<br>\n' %
                          (_quoteformstr(type),
                           type in filterorder and " checked>" or ">",
                           type))
        request.write(u'<input type="checkbox" name="filterorder" ' +
                      u'value="%s"%s%s<br>\n' %
                      ("_notype", "_notype" in filterorder and " checked>"
                       or ">", "No type"))

    # End form
    request.write(u"</table>\n")
    request.write(u'<input type=submit value="Submit!">\n</form>\n')

    tmp_fileno, tmp_name = tempfile.mkstemp()
    gr.dot.layout(file=tmp_name, format='png')
    f = file(tmp_name)
    img = f.read()

    gr.dot.layout(file=tmp_name, format='cmapx')
    f = file(tmp_name)
    mappi = f.read()

    imgbase = "data:image/png;base64," + b64encode(img)

    page = ('<img src="' + imgbase +
            '" alt="visualisation" usemap="#' +
            gr.graphattrs['name'] + '">\n' + mappi + "\n")

    request.write(page)

    if coloredges or colornodes:
        legendgraph.layout(file=tmp_name, format='png')
        f = file(tmp_name)
        img = f.read()
        imgbase = "data:image/png;base64," + b64encode(img)
        request.write('<img src="' + imgbase + '">\n')

    # edge pruning etc??

    # debug:
    # just to get the graph data out 
    gr.dot.layout(file=tmp_name)
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
