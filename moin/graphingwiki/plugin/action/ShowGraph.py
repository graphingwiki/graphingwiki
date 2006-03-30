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

    # Bail out if underlay page etc.
    # FIXME: a bit hack, make consistent with other no data cases?
    if not pageobj.isStandardPage(includeDeleted=False):
        request.write(formatter.text(
            "No graph data available."))
        request.write(formatter.endContent())
        wikiutil.send_footer(request, pagename)
        return

    # How many ../ must be inserted in the beginning of urls
    subrank = pagename.count('/')

    # Init search graph, output graph, start node and its path
    pagefilename = wikiutil.quoteWikinameFS(pagename)
    pagename = url_quote(_e(pagename))
    graphdata = Graph()
    outgraph = Graph()
    nodeitem = graphdata.nodes.add(pagename)
    nodeitem.URL = './' + pagefilename

    # Handling form arguments

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
        if not globaldata.has_key(cat):
            # graphdata not in sync on disk -> malicious input 
            # or something has gone very, very wrong
            break
        for newpage in globaldata[cat]:
            if newpage != pagename:
                startpages.append(newpage)
                n = graphdata.nodes.add(newpage)
                n.URL = './' + wikiutil.quoteWikinameFS(unicode(
                    url_unquote(newpage), config.charset))
        globaldata.close()

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

    # Add neato-specific layout stuff
    if graphengine == 'neato':
        outgraph.overlap = 'false'

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
    urladd = "?" + '&'.join([str(url_quote(x) + "=" +
                                 url_quote(''.join(request.form[x])))
                             for x in request.form])

    # link/node attributes that have been assigned colors
    coloredges = set()
    colornodes = set()

    # node attributes that are not guaranteed to be there (by sync/savegraph)
    nonguaranteeds_p = lambda x: x not in ['belongs_to_patterns',
                                           'label', 'URL']

    # Node filter of an existing type
    oftype_p = lambda x: x != '_notype'

    # For stripping lists of quoted strings
    qstrip_p = lambda lst: '"' + ','.join([x.strip('"') for x in lst]) + '"'
    qpirts_p = lambda txt: ['"' + x + '"' for x in txt.strip('"').split(',')]

    # node attributes
    nodeattrs = set()
    # nodes that do and do not have the attribute designated with orderby
    ordernodes = {}
    unordernodes = set()

    # Start pattern searches from current page +
    # nodes gathered as per form args
    nodes = set(startpages)

    # Init WikiNode-pattern
    WikiNode(request=request, urladd=urladd, startpages=startpages)

    # The working with patterns goes a bit like this:
    # First, get a sequence, add it to outgraph
    # Then, match from outgraph, add graphviz attrs
    def addseqtograph(obj1, obj2):
        # Get edge from match, skip if filtered
        olde = graphdata.edges.get(obj1.node, obj2.node)
        if getattr(olde, 'linktype', '_notype') in filteredges:
            if hasattr(olde, 'linktype'):
                filteredges.add(olde.linktype)
            return

        # Add nodes, data for ordering
        for obj in [obj1, obj2]:
            # If node already added, nothing to do
            if outgraph.nodes.get(obj.node):
                continue

            # Node filters
            for filt, doby in [(filterorder, orderby),
                               (filtercolor, colorby)]:
                # If no filters, continue
                if not doby or not filt:
                    continue
                
                # Filter notypes away if asked
                if not hasattr(obj, doby) and '_notype' in filt:
                    return
                elif not hasattr(obj, doby):
                    continue

                # Filtering by multiple metadata values
                target = getattr(obj, doby)
                for rule in [set(qpirts_p(x)) for x in filt if ',' in x]:
                    if rule == rule.intersection(target):
                        left = target.difference(rule)
                        if left:
                            setattr(obj, doby, left)
                        else:
                            return

                # Filtering by single values
                target = getattr(obj, doby)
                if target.intersection(filt) != set():
                    # If so, see if any metadata is left
                    left = target.difference(filt)
                    if left:
                        setattr(obj, doby, left)
                    else:
                        return

            # update nodeattrlist with non-graph/sync ones
            nodeattrs.update(filter(nonguaranteeds_p, dict(obj)))
            n = outgraph.nodes.add(obj.node)
            n.update(obj)
            if orderby:
                value = getattr(obj, orderby, None)
                if value:
                    # Add to ordernodes by combined value of metadata
                    value = qstrip_p(value)
                    n.__order = value
                    ordernodes.setdefault(value, set()).add(obj.node)
                else:
                    unordernodes.add(obj.node)

        # Add edge
        e = outgraph.edges.add(obj1.node, obj2.node)
        e.update(olde)

    # This traverses 1 to parents
    pattern = Sequence(Fixed(TailNode()),
                       Fixed(TailNode()))
    for obj1, obj2 in match(pattern, (nodes, graphdata)):
        addseqtograph(obj2, obj1)

    # The following code traverses 1 to children
    pattern = Sequence(Fixed(HeadNode()),
                       Fixed(HeadNode()))
    for obj1, obj2 in match(pattern, (nodes, graphdata)):
        addseqtograph(obj1, obj2)

    # If we should color nodes, gather nodes with attribute from
    # the form (ie. variable colorby) and change their colors, plus
    # gather legend data
    if colorby:
        def updatecolors(obj):
            rule = getattr(obj, colorby, None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                rule = qstrip_p(rule)
                colornodes.add(rule)
                obj.fillcolor = hashcolor(rule)
                obj.style = 'filled'

        lazyhas = LazyConstant(lambda x, y: hasattr(x, y))

        nodes = outgraph.nodes.getall()
        node = Fixed(Node())
        cond = Cond(node, lazyhas(node, colorby))
        for obj in match(cond, (nodes, outgraph)):
            updatecolors(obj)

    # Add color to edges with linktype, gather legend data
    edges = outgraph.edges.getall()
    edge = Fixed(Edge())
    pattern = Cond(edge, edge.linktype)
    for obj in match(pattern, (edges, outgraph)):
        coloredges.add(obj.linktype)
        obj.color = hashcolor(obj.linktype)

    # Make a different url for the page node
    node = outgraph.nodes.get(pagename)
    if node:
        node.URL = './\N'
    elif not outgraph.nodes.getall():
        outgraph.label = "No data"

    # Fix URLs for subpages
    if subrank > 0:
        for name, in outgraph.nodes.getall():
            node = outgraph.nodes.get(name)
            # All nodes should have URL:s, change relative ones
            if not re.search(r'^\w+:', node.URL):
                node.URL = '../' * (subrank-1) + '.' + node.URL

    # Add all data to graph
    gr = GraphRepr(outgraph, engine=graphengine, order='__order')

    # Make legend
    if coloredges or colornodes:
        legendgraph = Graphviz('legend', rankdir='LR')
        legend = legendgraph.subg.add("clusterLegend", label='Legend')        

    # Have bold circles on startnodes
    for node in [outgraph.nodes.get(name) for name in startpages]:
        if node:
            if hasattr(node, 'style'):
                node.style = node.style + ', bold'
            else:
                node.style = 'bold'

    # After this, edit gr.graphviz, not outgraph!
    outgraph.commit()

    # Now it's time to order the nodes
    # Kludges via outgraph as iterating gr.graphviz.edges bugs w/ gv_python
    if orderby:
        orderkeys = ordernodes.keys()
        orderkeys.sort()

        prev_ordernode = ''
        # New subgraphs, nodes to help ranking
        for key in orderkeys:
            cur_ordernode = 'orderkey: ' + key
            sg = gr.graphviz.subg.add(cur_ordernode, rank='same')
            # [1:-1] removes quotes from label
            sg.nodes.add(cur_ordernode, label=key[1:-1])
            for node in ordernodes[key]:
                sg.nodes.add(node)

            if prev_ordernode:
                gr.graphviz.edges.add((prev_ordernode, cur_ordernode),
                                 dir='none', style='invis',
                                 minlen='1', weight='10')
            prev_ordernode = cur_ordernode

        # Unordered nodes to their own rank
        sg = gr.graphviz.subg.add('unordered nodes', rank='same')
        sg.nodes.add('unordered nodes', style='invis')
        for node in unordernodes:
            sg.nodes.add(node)
        if prev_ordernode:
            gr.graphviz.edges.add((prev_ordernode, 'unordered nodes'),
                                  dir='none', style='invis',
                                  minlen='1', weight='10')
                                  
        # Edge minimum lengths
        for edge in outgraph.edges.getall():
            tail, head = edge
            edge = gr.graphviz.edges.get(edge)
            # set change
            taily = getattr(gr.graphviz.nodes.get(head), '__order', '')
            heady = getattr(gr.graphviz.nodes.get(tail), '__order', '')
            # The order attribute is owned by neither, one or
            # both of the end nodes of the edge
            if not heady and not taily:
                minlen = 0
            elif not heady:
                minlen = orderkeys.index(taily) - len(orderkeys)
            elif not taily:
                minlen = len(orderkeys) - orderkeys.index(heady)
            else:
                minlen = orderkeys.index(heady) - orderkeys.index(taily)

            # Redraw edge if it goes reverse wrt hierarcy
            if minlen >= 0:
                edge.set(minlen=str(minlen))
            else:
                backedge = gr.graphviz.edges.get((head, tail))
                if backedge:
                    backedge.set(minlen=str(-minlen))
                else:
                    backedge = gr.graphviz.edges.add((head, tail))
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
                         label=url_unquote(linktype))

    # Nodes
    prev = ''
    legendnodes = list(colornodes)
    legendnodes.sort()
    for nodetype in legendnodes:
        cur = 'colornodes: ' + nodetype
        legend.nodes.add(cur, label=nodetype[1:-1], style='filled',
                         fillcolor=hashcolor(nodetype))
        if prev:
            legend.edges.add((prev, cur), style="invis", dir='none')
        prev = cur

    # Escape quotes to numeric char references, remove outer quotes.
    def _quoteformstr(str):
        str = str.strip("\"'")
        str = str.replace('"', '&#x22;')
        return unicode('&#x22;' + str + '&#x22;', config.charset)

    def _quotetoshow(str):
        return unicode(url_unquote(str), config.charset)

    ## Begin form
    request.write(u'<form method="GET" action="%s">\n' %
                  _quotetoshow(pagename))
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
                       _quotetoshow(type)))
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
                       _quotetoshow(type)))
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
                       _quotetoshow(type)))
    request.write(u'<input type="checkbox" name="filteredges" ' +
                  u'value="%s"%s%s<br>\n' %
                  ("_notype", "_notype" in filteredges and " checked>"
                   or ">", "No type"))

    # filter nodes (related to colorby)
    if colorby:
        request.write(u'<td>\nFilter from colored:<br>\n')
        # set change
        allcolor = set(filter(oftype_p, filtercolor))
        allcolor.update(colornodes)
        for txt in [x for x in colornodes if ',' in x]:
            allcolor.update(qpirts_p(txt))
        allcolor = list(allcolor)
        allcolor.sort()
        for type in allcolor:
            request.write(u'<input type="checkbox" name="filtercolor" ' +
                          u'value="%s"%s%s<br>\n' %
                          (_quoteformstr(type),
                           type in filtercolor and " checked>" or ">",
                           _quotetoshow(type[1:-1])))
        request.write(u'<input type="checkbox" name="filtercolor" ' +
                      u'value="%s"%s%s<br>\n' %
                      ("_notype", "_notype" in filtercolor and " checked>"
                       or ">", "No type"))

    # filter nodes (related to orderby)
    if orderby:
        request.write(u'<td>\nFilter from ordered:<br>\n')
        # set change
        allorder = list(set(ordernodes.keys() + filter(oftype_p, filterorder)))
        allorder.sort()
        for type in allorder:
            request.write(u'<input type="checkbox" name="filterorder" ' +
                          u'value="%s"%s%s<br>\n' %
                          (_quoteformstr(type),
                           type in filterorder and " checked>" or ">",
                           _quotetoshow(type[1:-1])))
        request.write(u'<input type="checkbox" name="filterorder" ' +
                      u'value="%s"%s%s<br>\n' %
                      ("_notype", "_notype" in filterorder and " checked>"
                       or ">", "No type"))

    # End form
    request.write(u"</table>\n")
    request.write(u'<input type=submit value="Submit!">\n</form>\n')

    tmp_fileno, tmp_name = tempfile.mkstemp()
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

    if coloredges or colornodes:
        legendgraph.layout(file=tmp_name, format='png')
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
