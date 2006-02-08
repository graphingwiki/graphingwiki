# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - ShowGraph action

    @copyright: 2005 by Juhani Eronen <exec@ee.oulu.fi>
    @license: GNU GPL, see COPYING for details.
"""
    
import os, cPickle, tempfile
from random import choice, seed

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.formatter.text_html import Formatter 
from MoinMoin.parser.wiki import Parser

# cpe imports
import graph
import graphrepr

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

    # This action generate data using the user language
    request.setContentLanguage(request.lang)

    wikiutil.send_title(request, _('Wiki linkage as seen from "%s"') %
                        (pagename), pagename=pagename)

    pageobj = Page(request, pagename)
    pagedir = pageobj.getPagePath()

    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    formatter = Formatter(request)
    request.write(formatter.startContent("content"))
    formatter.setPage(pageobj)

    gfn = os.path.join(pageobj.getPagePath(), 'graphdata.pickle')

    colorby = ''
    if request.form.has_key('colorby'):
        colorby = str(''.join(request.form['colorby']))

    try:
        gf = file(gfn)
        graphdata = cPickle.load(gf)
        gr = graphrepr.GraphRepr(graphdata, engine='neato')

        linksoftype = []
        nodesoftype = []

        guaranteeds = lambda x: x not in ['belongs_to_patterns', 'label', 'URL']
        nodetypes = set()
        linktypes = set()

        # Set proto attributes before the data is loaded, because
        # currently proto attributes affect only items added after
        # adding the proto!
        gr.dot.set(proto='edge', len='3')

        for node in graphdata.nodes.getall():
            nodeitem = graphdata.nodes.get(*node)
            nodetypes.update(filter(guaranteeds, dict(nodeitem).keys()))
            k = getattr(nodeitem, 'URL', '')
            # If local link
            if k.startswith('./'):
                # Prolly not needed, as the page contents is not read?
                if not request.user.may.read(node[0]):
                    continue
                inc_page = Page(request, node[0], formatter=formatter)
                afn = os.path.join(inc_page.getPagePath(), 'graphdata.pickle')
                if os.path.exists(afn):
                    af = file(afn)
                    adata = cPickle.load(af)
                    othernode = adata.nodes.get(*node)
                    nodeitem.update(othernode)
                    nodetypes.update(filter(guaranteeds, dict(othernode).keys()))
                    # Add action name, args to URL
                    nodeitem.URL = nodeitem.URL + "?" + \
                                   '&'.join([str(x + "=" + \
                                                 ''.join(request.form[x]))
                                             for x in request.form])
            if colorby:
                rule = getattr(nodeitem, colorby, '')
                if rule:
                    nodesoftype.append(rule)
                    nodeitem.fillcolor = hashcolor(rule)
                    nodeitem.style = 'filled'

        for edge in graphdata.edges.getall():
            edgeitem = graphdata.edges.get(*edge)
            k = getattr(edgeitem, 'linktype', '')
            if k:
                linksoftype.append(k)
                edgeitem.color = hashcolor(k)

        if linksoftype or nodesoftype:
            legend = gr.dot.subg.add("clusterLegend", label='legend')
            start = 0
            for i in linksoftype:
                ln1 = "linktype: " + str(start)
                start = start + 1
                ln2 = "linktype: " + str(start)
                legend.nodes.add(ln1, style='invis')
                legend.nodes.add(ln2, style='invis')
                legend.edges.add((ln1, ln2), color=hashcolor(i), label=i)
            for i in nodesoftype:
                legend.nodes.add('nodesoftype: ' + i, label=i, style='filled',
                                 fillcolor=hashcolor(i))


        request.write(u'<form method="GET" action="./%s">' %
                      pagename + "\n")
        request.write(u'<input type=hidden name=action value="%s">' %
                      ''.join(request.form['action']) + "Color by:<br>\n")

        for type in nodetypes:
            request.write(u'%s <input type="radio" name="colorby" value="%s"><br>' %
                          (type, type) + "\n")

#         request.write(u'Color by: <input type=text name="colorby" size=11>' + \
#                       "\n")
        request.write(u'<input type=submit value="Submit!">' + \
                      "\n" '</form>' + "\n")

        graphdata.commit()
        
        from base64 import b64encode

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

        # filter by graph/link type
        # color by -""-
        # order by -""-
        # edge pruning etc??

        # debug:
        # just to get the graph data out 
        # gr.dot.layout(file=tmp_name)
        # f = file(tmp_name)
        # gtext = f.read()
        # request.write(formatter.preformatted(1))
        # request.write(formatter.text(gtext))
        # request.write(formatter.preformatted(0))

        request.write(formatter.preformatted(1))
        request.write(formatter.text(str(nodetypes)))
        request.write(formatter.preformatted(0))

        os.close(tmp_fileno)

        args = [x for x in request.form.keys() if x != 'action']
        if args:
            request.write(formatter.preformatted(1))
            for arg in args:
                request.write(arg)
                for val in request.form[arg]:
                    request.write(" " + val)
            request.write(formatter.preformatted(0))
    except IOError, err:
        if err.errno == 2:
            # no such file or directory
            request.write(formatter.paragraph(1))
            request.write("No graph data available")
            request.write(formatter.paragraph(0))

    # End content
    request.write(formatter.endContent()) # end content div
    # Footer
    wikiutil.send_footer(request, pagename)
