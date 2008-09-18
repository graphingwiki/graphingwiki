# -*- coding: utf-8 -*-"
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

import os
import shelve
import re
import socket
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
from graphingwiki.graphrepr import GraphRepr, Graphviz, gv_found
from graphingwiki.patterns import *
from graphingwiki.editing import ordervalue

import math
import colorsys

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

# Escape quotes to numeric char references
def quoteformstr(text):
    return text.replace('"', '&#x22;')

class GraphShower(object):
    EDGE_DARKNESS = 0.85
    FRINGE_DARKNESS = 0.50
  
    def __init__(self, pagename, request, graphengine = "neato"):
        self.hashcolor = self.wrapColorFunc(self.hashcolor)
        self.gradientcolor = self.wrapColorFunc(self.gradientcolor)
    
        # Fix for mod_python, globals are bad
        self.used_colors = dict()

        self.pagename = pagename
        self.request = request
        self.graphengine = graphengine
        self.available_formats = ['png', 'svg', 'dot']
        self.format = 'png'
        self.limit = ''
        self.unscale = 0
        self.hidedges = 0
        self.edgelabels = 0

        self.isstandard = False
        
        self.categories = list()
        self.otherpages = list()
        self.startpages = list()

        self.depth = 1
        self.orderby = ''
        self.colorby = ''

        self.orderreg = ""
        self.ordersub = ""
        self.colorreg = ""
        self.colorsub = ""

        # Lists for the graph layout
        self.allcategories = set()
        self.filteredges = set()
        self.filterorder = set()
        self.filtercolor = set()
        self.filtercats = set()
        self.rankdir = 'LR'

        # Lists for the filter values for the form
        self.orderfiltervalues = set()
        self.colorfiltervalues = set()

        # What to add to node URL:s in the graph
        self.urladd = ''

        # Selected colorfunction used and postprocessing function
        self.colorfunc = self.hashcolor
        self.colorscheme = 'random'

        # If we should send out just the graphic or forms as well
        # Used by ShowGraphSimple.py
        self.do_form = True

        # link/node attributes that have been assigned colors
        self.coloredges = set()
        self.colornodes = set()

        # node attributes
        self.nodeattrs = set()
        # nodes that do and do not have the attribute designated with orderby
        self.ordernodes = dict()
        self.unordernodes = set()

        # For test, inline
        self.help = ""

        self.height = 0
        self.width = 0
        self.size = ''

        # Node filter of an existing type
        self.oftype_p = lambda x: x != NO_TYPE
 
        # Category, Template matching regexps
        self.cat_re = re.compile(request.cfg.page_category_regex)
        self.temp_re = re.compile(request.cfg.page_template_regex)

    def wrapColorFunc(self, func):
        def colorFunc(string, darknessFactor=1.0):
            # Black edges must be black                  
            if string == NO_TYPE:
                return "black"        
        
            color = self.used_colors.get(string, None)
            if color is None:
                color = func(string)
                self.used_colors[string] = color
  
            h, s, v = color
            v *= darknessFactor
    
            rgb = colorsys.hsv_to_rgb(h, s, v)
            rgb = tuple(map(lambda x: int(x * 255), rgb))
            cl = "#%02x%02x%02x" % rgb 
        
            return cl  
        return colorFunc

    def hashcolor(self, string):
        magicNumber = 17.31337 / 113.0
        h = (magicNumber * len(self.used_colors)) % 1.0
        s = 0.40 + math.sin(h * 37.0) * 0.04
        v = 0.90 + math.cos(h * 39.0) * 0.05
        return h, s, v                  

    def gradientcolor(self, string):
        clrnodes = sorted(self.colornodes)

        blueHSV = 0.67, 0.25, 1.0
        redHSV = 1.0, 0.50, 0.95

        if len(clrnodes) <= 1:
            return blueHSV

        factor = float(clrnodes.index(string)) / (len(clrnodes) - 1)
        h, s, v = map(lambda blue, red: blue + 
                      (red-blue)*factor, blueHSV, redHSV)
        return h, s, v
            
    def formargs(self):
        request = self.request
        error = False
        
        if self.do_form:
            # Get categories for current page, for the category form
            self.allcategories.update(request.page.getCategories(request))
        
        # Bail out flag on if underlay page etc.
        # FIXME: a bit hack, make consistent with other no data cases?
        if not request.page.isStandardPage(includeDeleted = False):
            self.isstandard = True

        # depth
        if request.form.has_key('depth'):
            depth = request.form['depth'][0]
            try:
                depth = int(depth)
                if depth >= 1:
                    self.depth = depth
            except ValueError:
                self.depth = 1

        # format
        if request.form.has_key('format'):
            format = request.form['format'][0]
            if format in self.available_formats:
                self.format = format

        # Categories
        if request.form.has_key('categories'):
            self.categories = request.form['categories']

        # Other pages
        if request.form.has_key('otherpages'):
            self.otherpages = ','.join(request.form["otherpages"]).split(',')
            
        # Limit
        if request.form.has_key('limit'):
            self.limit = ''.join(request.form['limit'])
            
        # Rankdir
        if request.form.has_key('dir'):
            self.rankdir = ''.join(request.form['dir'])

        # Unscale
        if request.form.has_key('unscale'):
            self.unscale = 1

        # Hide edges
        if request.form.has_key('hidedges'):
            self.hidedges = 1

        # Hide edges
        if request.form.has_key('edgelabels'):
            self.edgelabels = 1

        # Orderings
        if request.form.has_key('orderby'):
            self.orderby = ''.join(request.form['orderby'])
            # Checked due to weirdo problems with ShowGraphSimple
            if self.orderby:
                self.graphengine = 'dot'
        if request.form.has_key('colorby'):
            self.colorby = ''.join(request.form['colorby'])

        # Color schema
        if request.form.has_key('colorscheme'):
            self.colorscheme = ''.join(request.form['colorscheme'])
            if self.colorscheme == 'gradient':
                self.colorfunc = self.gradientcolor

        # Regexps
        if request.form.has_key('orderreg'):
            self.orderreg = ''.join(request.form['orderreg'])
        if request.form.has_key('ordersub'):
            self.ordersub = ''.join(request.form['ordersub'])
        if self.ordersub and self.orderreg:
            try:
                self.re_order = re.compile(self.orderreg)
            except:
                error = "Erroneus regexp: s/%s/%s/" % (self.orderreg,
                                                       self.ordersub)
        if request.form.has_key('colorreg'):
            self.colorreg = ''.join(request.form['colorreg'])
        if request.form.has_key('colorsub'):
            self.colorsub = ''.join(request.form['colorsub'])
        if self.colorsub and self.colorreg:
            try:
                self.re_color = re.compile(self.colorreg)
            except:
                error = "Erroneus regexp: s/%s/%s/" % (self.colorreg,
                                                       self.colorsub)

        # Filters
        if request.form.has_key('filteredges'):
            self.filteredges.update(request.form['filteredges'])
        if request.form.has_key('filterorder'):
            self.filterorder.update(request.form['filterorder'])
        if request.form.has_key('filtercolor'):
            self.filtercolor.update(request.form['filtercolor'])
        if request.form.has_key('filtercats'):
            self.filtercats.update(request.form['filtercats'])

        # This is the URL addition to the nodes that have graph data
        self.urladd = '?'
        for key in request.form:
            for val in request.form[key]:
                self.urladd = (self.urladd + key + '=' + val + '&')
        self.urladd = self.urladd[:-1]

        # Disable output if testing graph
        if request.form.has_key('test'):
            self.format = ''
            self.help = 'test'

        # Show inline graph
        if request.form.has_key('inline'):
            self.help = 'inline'

        # Height and Width
        for attr in ['height', 'width']:
            if request.form.has_key(attr):
                val = ''.join([x for x in request.form[attr]])
                try:
                    setattr(self, attr, float(val))
                except ValueError:
                    pass

        if not self.height and self.width:
            self.height = self.width
        elif self.height and not self.width:
            self.width = self.height
        elif not self.height and not self.width:
            self.width = self.height = 1024

        if not self.unscale:
            self.size = "%.2f,%.2f" % ((self.width / 72),
                                       (self.height / 72))

        return error

    def addToStartPages(self, graphdata, pagename):
        self.startpages.append(pagename)
        root = graphdata.nodes.add(pagename)
        root.gwikiURL = './' + pagename

        return graphdata

    def addToAllCats(self, cats):
        if not cats:
            return

        # No need to list all categories if the list is not going to be used
        if not self.do_form:
            return

        self.allcategories.update(cats)

    def buildGraphData(self):
        graphdata = Graph()

        pagedir = self.request.page.getPagePath()
        pagename = self.pagename

        def get_categories(nodename):
            pagedata = self.request.graphdata.getpage(nodename)
            return pagedata.get('out', dict()).get('gwikicategory', list())

        for nodename in self.otherpages:
            graphdata = self.addToStartPages(graphdata, nodename)

            self.addToAllCats(get_categories(nodename))

        # Do not add self to graph if self is category or
        # template page and we're looking at categories
        if not self.categories:
            graphdata = self.addToStartPages(graphdata, pagename)
        elif not (self.cat_re.search(pagename) or
                  self.temp_re.search(pagename)):
            graphdata = self.addToStartPages(graphdata, pagename)

        # If categories specified in form, add category pages to startpages
        for cat in self.categories:
            # Permissions
            if not self.request.user.may.read(cat):
                continue
            catpage = self.request.graphdata.getpage(cat)
            for type in catpage['in']:
                for newpage in catpage['in'][type]:
                    if not (self.cat_re.search(newpage) or
                            self.temp_re.search(newpage)):
                        graphdata = self.addToStartPages(graphdata, newpage)
                        self.addToAllCats(get_categories(newpage))

        return graphdata

    def buildOutGraph(self):
        outgraph = Graph()        

        if getattr(self, 'orderby', '_hier') != '_hier':
            outgraph.clusterrank = 'local'
            outgraph.compound = 'true'

        # Add neato-specific layout stuff
        if self.graphengine == 'neato':
            outgraph.overlap = 'compress'
            outgraph.splines = 'true'

        outgraph.rankdir = self.rankdir

        # Formatting features here!
        outgraph.bgcolor = "transparent"

        if self.size:
            outgraph.size = self.size

        return outgraph
    
    def addToGraphWithFilter(self, graphdata, outgraph, obj1, obj2):
        _ = self.request.getText

        # Get edge from match, skip if filtered
        olde = graphdata.edges.get(obj1.node, obj2.node)
        types = olde.linktype.copy()
        for type in types:
            if type in self.filteredges:
                olde.linktype.remove(type)
        if olde.linktype == set():
            return

        # Add nodes, data for ordering
        for obj in [obj1, obj2]:
            # If traverse limited to startpages
            if self.limit == 'start':
                if not obj.node in self.startpages:
                    continue
            # or to pages within the wiki
            elif self.limit == 'wiki':
                if not obj.gwikiURL[0] == '.':
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
                if not hasattr(obj, doby) and NO_TYPE in filt:
                    return
                elif not hasattr(obj, doby):
                    continue
                
                # Filtering by multiple metadata values
                target = getattr(obj, doby)
                for rule in [set(x) for x in filt if ',' in x]:
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

            # User rights have been checked before, at traverse
            pagedata = self.request.graphdata.getpage(obj.node)

            cats = obj.gwikicategory

            # Filter pages by category
            for filt in self.filtercats:
                filt = '"%s"' % filt
                if filt in cats:
                    return

            # Add page categories to selection choices in the form
            # (for local pages only, ie. existing and saved)
            if pagedata.get('saved', False):
                self.addToAllCats(cats)

            # update nodeattrlist with non-graph/sync ones
            self.nodeattrs.update(nonguaranteeds_p(obj))
            n = outgraph.nodes.add(obj.node)
            n.update(obj)

            # Add tooltip, if applicable
            # Only add non-guaranteed attrs to tooltip
            pagemeta = pagedata.get('meta', dict())
            pagemeta.update(pagedata.get('out', dict()))
            if (pagemeta and not hasattr(obj, 'gwikitooltip')):
                pagekeys = nonguaranteeds_p(pagemeta)
                tooldata = '\n'.join("-%s: %s" % 
                                     (x == '_notype' and _('Links') or x,
                                      ', '.join(pagemeta[x]))
                                     for x in pagekeys)
                n.gwikitooltip = '%s\n%s' % (obj.node, tooldata)

            # Shapefiles
            if getattr(obj, 'gwikishapefile', None):
                # Enter file path for attachment shapefiles
                value = obj.gwikishapefile[11:]
                components = value.split('/')
                if len(components) == 1:
                    page = obj.node
                else:
                    page = '/'.join(components[:-1])
                file = components[-1]

                shapefile, exists = attachment_file(self.request, page, file)

                # get attach file path, empty label
                if exists:
                    n.gwikishapefile = shapefile
                    
                    # Stylistic stuff: label, borders
                    # "Note that user-defined shapes are treated as a form
                    # of box shape, so the default peripheries value is 1
                    # and the user-defined shape will be drawn in a
                    # bounding rectangle. Setting peripheries=0 will turn
                    # this off."
                    # http://www.graphviz.org/doc/info/attrs.html#d:peripheries
                    n.gwikilabel = ' '
                    n.gwikiperipheries = '0'
                    n.gwikistyle = 'filled'
                    n.gwikifillcolor = 'transparent'
                else:
                    del n.gwikishapefile
#            elif 'AttachFile' in obj.node:
#                # Have shapefiles of image attachments
#                if obj.node.split('.')[-1] in ['gif', 'png', 'jpg', 'jpeg']:
#                    print obj.node

            if getattr(self, 'orderby', '_hier') != '_hier':
                value = getattr(obj, self.orderby, None)
                if value:
                    # Add to self.ordernodes by combined value of metadata
                    value = ''.join(value)
                    # Add to filterordervalues in the nonmodified form
                    self.orderfiltervalues.add(value)
                    re_order = getattr(self, 're_order', None)
                    if re_order:
                        value = re_order.sub(self.ordersub, value)

                    # Graphviz attributes must be strings
                    n._order = value

                    # Internally, some values are given a special treatment
                    value = ordervalue(value)
                    self.ordernodes.setdefault(value, set()).add(obj.node)
                else:
                    self.unordernodes.add(obj.node)

        # Add edge if not limited
        if self.limit:
            if not (outgraph.nodes.get(obj1.node) and
                    outgraph.nodes.get(obj2.node)):
                return

        e = outgraph.edges.add(obj1.node, obj2.node)
        e.update(olde)

        # Hide edges if applicable
        if self.hidedges:
            e.style = "invis"

        return

    def traverseParentChild(self, graphdata, outgraph, nodes):
        # graphdata is the 'in' graph extended and traversed

        request = self.request
        urladd = self.urladd

        cl.start('traverseparent')
        # This traverses 1 to parents
        for node in nodes:
            nodeitem = graphdata.nodes.get(node)
            parents = load_parents(request, graphdata, node, urladd)
            for parent in parents:
                parentitem = graphdata.nodes.get(parent)
                self.addToGraphWithFilter(graphdata, outgraph, 
                                          parentitem, nodeitem)
        cl.stop('traverseparent')

        cl.start('traversechild')
        # This traverses 1 to children
        for node in nodes:
            nodeitem = graphdata.nodes.get(node)
            children = load_children(request, graphdata, node, urladd)
            for child in children:
                childitem = graphdata.nodes.get(child)
                self.addToGraphWithFilter(graphdata, outgraph, 
                                          nodeitem, childitem)
        cl.stop('traversechild')

        return outgraph

    def colorNodes(self, outgraph):
        colorby = self.colorby

        # If we should color nodes, gather nodes with attribute from
        # the form (ie. variable colorby) and change their colors, plus
        # gather legend data
        def getcolors(obj):
            rule = getattr(obj, colorby, None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                rule = ''.join(rule)
                re_color = getattr(self, 're_color', None)
                # Add to filterordervalues in the nonmodified form
                self.colorfiltervalues.add(rule)
                if re_color:
                    rule = re_color.sub(self.colorsub, rule)
                self.colornodes.add(rule)

        def updatecolors(obj):
            rule = getattr(obj, colorby, None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                rule = ''.join(rule)
                re_color = getattr(self, 're_color', None)
                if re_color:
                    rule = re_color.sub(self.colorsub, rule)
                obj.gwikifillcolor = self.colorfunc(rule)
                obj.gwikicolor = self.colorfunc(rule, self.FRINGE_DARKNESS)
                obj.gwikistyle = 'filled'

        nodes = filter(lambda x: hasattr(x, colorby), 
                       map(outgraph.nodes.get, outgraph.nodes))
        for obj in nodes:
            getcolors(obj)
            updatecolors(obj)

        return outgraph

    def colorEdges(self, outgraph):
        # Add color to edges with linktype, gather legend data
        edges = filter(lambda x: getattr(x, "linktype", None), 
                       [outgraph.edges.get(*x) for x in outgraph.edges])
        for obj in edges:
            self.coloredges.update(filter(self.oftype_p, obj.linktype))
            obj.color = ':'.join(self.hashcolor(x, self.EDGE_DARKNESS) 
                                 for x in obj.linktype)
            if self.edgelabels:
                obj.decorate = 'true'
                obj.label = ','.join(x for x in obj.linktype if x != NO_TYPE)
                                     
        return outgraph

    def fixNodeUrls(self, outgraph):
        import re
        _ = self.request.getText
        
        # Make a different url for start nodes
        for nodename in self.startpages:
            node = outgraph.nodes.get(nodename)
            if node:
                node.gwikiURL = './\N'

        # You managed to filter out all your pages, dude!
        if not outgraph.nodes:
            outgraph.label = _("No data")
            outgraph.bgcolor = 'white'

        # Make the attachment node labels look nicer
        # Also fix overlong labels
        for name in outgraph.nodes:
            node = outgraph.nodes.get(name)
            if not node.gwikilabel:
                node.gwikilabel = name

            # local full-path relative links
            if node.gwikiURL[0] == '/':
                continue
            # local relative links
            elif node.gwikiURL[0] == '.':
                node.gwikiURL = self.request.getScriptname() + \
                                node.gwikiURL.lstrip('.')
            elif len(node.gwikilabel) == 0 and len(node.gwikiURL) > 50:
                node.gwikilabel = node.gwikiURL[:47] + '...'
            elif len(node.gwikilabel) > 50:
                node.gwikilabel = node.gwikilabel[:47] + '...'
            elif not ':' in node.gwikilabel:
                node.gwikilabel = node.gwikiURL

        return outgraph

    def circleStartNodes(self, outgraph):
        # Have bold circles on startnodes
        for node in [outgraph.nodes.get(name) for name in self.startpages]:
            if node:
                # Do not circle image nodes
                if hasattr(node, 'gwikishapefile'):
                    continue
                if hasattr(node, 'gwikistyle'):
                    node.gwikistyle = node.gwikistyle + ', bold'
                else:
                    node.gwikistyle = 'bold'

        return outgraph

    def getURLns(self, link):
        # Find out subpage level to adjust URL:s accordingly
        subrank = self.request.page.page_name.count('/')
        if not hasattr(self.request, 'iwlist'):
            get_interwikilist(self.request)
        # Namespaced names
        if ':' in link:
            iwname = link.split(':')
            if self.request.iwlist.has_key(iwname[0]):
                return self.request.iwlist[iwname[0]] + iwname[1]
            else:
                return '../' * subrank + './InterWiki'
        # handle categories differently as ordernodes:
        # they will just direct to the category page
        if link == 'gwikicategory':
            return ''
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
            # As we're trying to see what the name of the ordernode
            # should be, we�ll have to check out which of the different
            # types it might be.
            if isinstance(key, basestring):
                label = ""
                # Stylistic fixing of IP address key labels
                if key.startswith('00') and len(key) == 6:
                    try:
                        label = '"%s"' % socket.inet_ntoa(key[2:])
                    except socket.error:
                        pass

                # For normal text labels, label == key
                if not label:
                    label = key
            # For numeric keys, convert int to str
            else:
                label = '"%s"' % str(key)
            cur_ordernode = 'orderkey: ' + label
            sg = gr.graphviz.subg.add(cur_ordernode, rank='same')
            # handle categories as ordernodes different
            # so that they would point to the corresponding categories
            # [1:-1] removes quotes from label
            if not orderURL:
                sg.nodes.add(cur_ordernode, label=label[1:-1],
                             URL=label[1:-1])
            else:
                sg.nodes.add(cur_ordernode, label=label[1:-1],
                             URL=orderURL)
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
        for edge in outgraph.edges:
            tail, head = edge
            edge = gr.graphviz.edges.get(edge)
            taily = getattr(gr.graphviz.nodes.get(head), '_order', '')
            heady = getattr(gr.graphviz.nodes.get(tail), '_order', '')

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
        _ = self.request.getText
        # Make legend
        if self.size:
            legendgraph = Graphviz('legend', rankdir='LR', constraint='false',
                                   **{'size': self.size})

        else:
            legendgraph = Graphviz('legend', rankdir='LR', constraint='false')
        legend = legendgraph.subg.add("clusterLegend",
                                      label=_('Legend'))
        subrank = self.pagename.count('/')
        colorURL = self.getURLns(self.colorby)
        per_row = 0

	# Formatting features here! 
	legend.bgcolor = "transparent" 
        legend.pencolor = "black" 

        # Add nodes, edges to legend
        # Edges
        if not self.hidedges:

            typenr = 0
            for linktype in sorted(self.coloredges):
                if per_row == 4:
                    per_row = 0
                    typenr = typenr + 1
                ln1 = "linktype: " + str(typenr)
                typenr = typenr + 1
                ln2 = "linktype: " + str(typenr)
                legend.nodes.add(ln1, style='invis', label='')
                legend.nodes.add(ln2, style='invis', label='')

                legend.edges.add((ln1, ln2),
                                 color=self.hashcolor(linktype,
                                                      self.EDGE_DARKNESS),
                                 label=linktype,
                                 URL=self.getURLns(linktype))
                per_row = per_row + 1

        # Nodes
        prev = ''
        per_row = 0

        for nodetype in sorted(self.colornodes):
            cur = 'self.colornodes: ' + nodetype

            fillcolor = self.colorfunc(nodetype)
            color = self.colorfunc(nodetype, self.FRINGE_DARKNESS)

            legend.nodes.add(cur, label=nodetype, style='filled', 
                             color=color, fillcolor=fillcolor,
                             URL=colorURL)
            if prev:
                if per_row == 3:
                    per_row = 0
                else:
                    legend.edges.add((prev, cur), style="invis", dir='none')
                    per_row = per_row + 1
            prev = cur

        return legendgraph


    def sendForm(self):
        request = self.request
        _ = request.getText

        self.request.write('<!-- $Id$ -->\n')

        ## Begin form
        request.write(u'<div class="showgraph-form">\n')
        request.write(u'<form method="GET" action="%s">\n' %
                      actionname(request, self.pagename))
        request.write(u'<input type=hidden name=action value="%s">' %
                      ''.join(request.form['action']))

        request.write(u'<div class="showgraph-panel1">\n')
	# PANEL 1 
        request.write(u'<a href="javascript:toggle(\'tab0\')">View & Include</a><br>\n')
        request.write(u'<table border="1" id="tab0"><tr>\n')

        # outputformat
        request.write(u"<td valign=top>\n")
        request.write(u"<u>" + _("Format:") + u"</u><br>\n")
        request.write(u'<select name="format"><br>\n')
        for type in self.available_formats:
            request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (type,
                          type == self.format and " selected>" or ">",
                          type))
        request.write(u'</select><br>\n')

        # Height
        request.write(_("Max height") + u"<br>\n")
        request.write(u'<input type="text" name="height" ' +
                      u'size=5 value="%s"><br>\n' % str(self.height))

        # Width
        request.write(_("Max width") + u"<br>\n")
        request.write(u'<input type="text" name="width" ' +
                      u'size=5 value="%s"><br>\n' % str(self.width))

        # Unscale
        request.write(u'<input type="checkbox" name="unscale" ' +
                      u'value="0"%s\n' %
                      (self.unscale and ' checked>' or '>') +
                      _('Unscale'))

        # hide edges
        request.write(u"<br><u>" + _("Edges:") + u"</u><br>\n")
        request.write(u'<input type="checkbox" name="hidedges" ' +
                      u'value="1"%s\n' %
                      (self.hidedges and ' checked>' or '>') +
                      _('Hide edges'))

        # show edge labels
        request.write(u'<br><input type="checkbox" name="edgelabels" ' +
                      u'value="1"%s\n' %
                      (self.edgelabels and ' checked>' or '>') +
                      _('Edge labels'))

        # Include
	request.write(u"<td valign=top>\n")

        # categories
        if self.allcategories:
            request.write(u"<u>" + _("Categories:") + u"</u><br>\n")
        if len(self.allcategories) > 5:
	    request.write(u'<select name="categories" multiple size=6><br>\n')

        for type in self.allcategories:
            if len(self.allcategories) > 5:
                request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (type,
                          type in self.categories and " selected>" or ">",
                          type))
            else:
                request.write(u'<input type="checkbox" name="categories" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type in self.categories and " checked>" or ">",
                           type))

        if len(self.categories) > 5: 
	    request.write(u'</select><br>\n')


        # Depth
        request.write(u"<u>" + _("Link depth") + u"</u><br>\n")
        request.write(u'<input type="text" name="depth" ' +
                      u'size=2 value="%s"><br>\n' % str(self.depth))


        # otherpages
        otherpages = ', '.join(self.otherpages)
        request.write(u"<td valign=top>\n<u>" + 
                      _("Other pages:") + u"</u><br>\n")
        request.write(u'<input type="text" name="otherpages" ' +
                      u'size=20 value="%s"><br>\n' % otherpages)

        # limit
        request.write(u"<u>" + _("Include rules:") + u"</u><br>\n")
        request.write(u'<input type="radio" name="limit" ' +
                      u'value="start"%s' %
                      (self.limit == 'start' and ' checked>' or '>') +
                      _('These pages only') + u'<br>\n')
        request.write(u'<input type="radio" name="limit" ' +
                      u'value="wiki"%s' %
                      (self.limit == 'wiki' and ' checked>' or '>') +
                      _('From this wiki only') + u'<br>\n')
        request.write(u'<input type="radio" name="limit" ' +
                      u'value=""%s' %
                      (self.limit == '' and ' checked>' or '>') +
                      _('All links') + u'<br>\n')

        request.write(u'</table>\n')
        request.write(u'</div>\n')

        def sortShuffle(types):
            types = sorted(types)
            if 'gwikicategory' in types:
                types.remove('gwikicategory')
            types.insert(0, 'gwikicategory')
            return types

        request.write(u'<div class="showgraph-panel2">\n')
	# PANEL 2
        request.write(u'<a href="javascript:toggle(\'tab1\')">Color & Order</a><br>\n')
        request.write(u'<table border="1" id="tab1"><tr>\n')

        # colorby
        request.write(u"<td valign=top>\n")
	request.write(u"<u>" + _("Color by:") + u"</u><br>\n")
        types = sortShuffle(self.nodeattrs)

	if len(types) > 5: 
	    request.write(u'<select name="colorby" size=6><br>\n')

        for type in types:
	    if len(types) > 5:
                request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (type,
                          type == self.colorby and " selected>" or ">",
                          type))
            else:
                request.write(u'<input type="radio" name="colorby" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.colorby and " checked>" or ">",
                           type))
        if len(types) > 5:
            request.write(u'<option value=""%s%s</option><br>\n' %
                          (self.colorby == '' and " selected>" or ">",
                          _("no coloring")))
            request.write(u'</select><br>\n')
        else:
            request.write(u'<input type="radio" name="colorby" ' +
                      u'value=""%s%s<br>\n' %
                      (self.colorby == '' and " checked>" or ">",
                       _("no coloring")))

        if self.colorby:
	    request.write(u"<td valign=top>\n")
            request.write(u"<u>" + _("Color type:") + u"</u><br>\n")
            request.write(u'<select name="colorscheme">')
            for ord, name in zip(['random', 'gradient'],
                                 [_('random'), _('gradient')]):
                request.write('<option %s label="%s" value="%s">%s</option>\n'%
                              (self.colorscheme == ord and 'selected' or '',
                               ord, ord, name))
            request.write(u'</select><br>\n<u>' + _('Color regexp:') + '</u><br>\n')
            request.write(u'<input type=text name="colorreg" size=10 ' +
                          u'value="%s"><br>\n' % str(self.colorreg))
            request.write(u'<u>' + _('substitution:') + '</u><br>\n')
            request.write(u'<input type=text name="colorsub" size=10 ' +
                          u'value="%s"><br>\n' % str(self.colorsub))
	
        # orderby
        request.write(u"<td valign=top>\n")
	request.write(u"<u>" + _("Order by:") + u"</u><br>\n")
        types = sortShuffle(self.nodeattrs)

	if len(types) > 5: 
	    request.write(u'<select name="orderby" size=6><br>\n')

        for type in types:
	    if len(types) > 5:
                request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (type,
                          type == self.orderby and " selected>" or ">",
                          type))
            else:
                request.write(u'<input type="radio" name="orderby" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.orderby and " checked>" or ">",
                           type))
        if len(types) > 5:
            request.write(u'<option value=""%s%s</option><br>\n' %
                          (self.orderby == '' and " selected>" or ">",
                          _("no ordering")))
            request.write(u'<option value="%s"%s%s</option><br>\n' %
                      ('_hier',
                       self.orderby == '_hier' and " selected>" or ">",
                       _("hierarchical")))
            request.write(u'</select><br>\n')
        else:
            request.write(u'<input type="radio" name="orderby" ' +
                      u'value=""%s%s<br>\n' %
                      (self.orderby == '' and " checked>" or ">",
                       _("no ordering")))
            request.write(u'<input type="radio" name="orderby" ' +
                      u'value="%s"%s%s<br>\n' %
                      ('_hier',
                       self.orderby == '_hier' and " checked>" or ">",
                       _("hierarchical")))
	
        if self.orderby:
	    request.write(u"<td valign=top>\n")
            request.write(u"<u>" + _("Order direction:") + u"</u><br>\n")
            request.write('<select name="dir">')
            for ord, name in zip(['TB', 'BT', 'LR', 'RL'],
                              [_('top to bottom'), _('bottom to top'),
                               _('left to right'), _('right to left')]):
                request.write('<option %s label="%s" value="%s">%s</option>\n'%
                              (self.rankdir == ord and 'selected' or '',
                               ord, ord, name))
            if self.orderby != '_hier':
                request.write(u'</select><br>\n<u>' + _('Order regexp:') +
                              u'</u><br>\n')
                request.write(u'<input type=text name="orderreg" size=10 ' +
                              u'value="%s"><br>\n' % str(self.orderreg))
                request.write(u'<u>' + _('substitution:') + u'</u><br>\n')
                request.write(u'<input type=text name="ordersub" size=10 ' +
                              u'value="%s"><br>\n' % str(self.ordersub))

	request.write(u'</table>\n')
        request.write(u'</div>\n')


        request.write(u'<div class="showgraph-panel3">\n')
        # PANEL 3 
        request.write(u'<a href="javascript:toggle(\'tab2\')">Filters</a><br>\n')
        request.write(u'<td valign=top><table border="1" id="tab2"><tr>\n')

        # filter edges
        request.write(u'<td valign=top>\n<u>' + _('Edges:') + u'</u><br>\n')
        alledges = list(self.coloredges) + filter(self.oftype_p,
                                                  self.filteredges)
        alledges.sort()

	if len(alledges) > 5: 
	     request.write(u'<select name="filteredges" multiple size=6><br>\n')

        for type in alledges:
            if len(alledges) > 5:
                request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (type,
                          type in self.filteredges and " selected>" or ">",
                          type))
            else:
                request.write(u'<input type="checkbox" name="filteredges" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                          type in self.filteredges and " checked>" or ">",
                          type))

        if len(alledges) > 5:
            request.write(u'<option value="%s"%s%s</option><br>\n' %
                      (NO_TYPE,
                      NO_TYPE in self.filteredges and " selected>" or ">",
                      _("No type")))
            request.write(u'</select><br>\n')
        else:
            request.write(u'<input type="checkbox" name="filteredges" ' +
                      u'value="%s"%s%s<br>\n' %
                      (NO_TYPE,
                      NO_TYPE in self.filteredges and
                      " checked>"
                      or ">",
                      _("No type")))
	
	# filter categories
        if self.allcategories:
            request.write(u"<td valign=top>\n<u>" + _('Categories:') + u"</u><br>\n")

            if len(self.allcategories) > 5: 
		request.write(u'<select name="filtercats" multiple size=6><br>\n')
            for type in self.allcategories:
                if len(self.allcategories) > 5:
                    request.write(u'<option value="%s"%s%s</option><br>\n' %
                              (type,
                              type in self.filtercats and " selected>" or ">",
                              type))
                else:
                    request.write(u'<input type="checkbox" name="filtercats" ' +
                              u'value="%s"%s%s<br>\n' %
                              (type,
                               type in self.filtercats and " checked>" or ">",
                               type))
	    if len(self.allcategories) > 5: 
		request.write(u'</select><br>\n')

        # filter nodes (related to colorby)
        if self.colorby:
            request.write(u"<td valign=top>\n<u>" + _('Colored:') + u"</u><br>\n")
            allcolor = set(filter(self.oftype_p, self.filtercolor))
            allcolor.update(self.colorfiltervalues)
            for txt in [x for x in self.colorfiltervalues if ',' in x]:
                allcolor.update(txt)
            allcolor = list(allcolor)
            allcolor.sort()
  
            if len(allcolor) > 5: 
		request.write(u'<select name="filtercolor" multiple size=6><br>\n')

            for type in allcolor:
		if len(allcolor) > 5:
                    request.write(u'<option value="%s"%s%s</option><br>\n' % 
		              (quoteformstr(type), 
			      type in self.filtercolor and " selected>" or ">",
			      type[1:-1]))
                else:
                    request.write(u'<input type="checkbox" name="filtercolor" ' +
                              u'value="%s"%s%s<br>\n' %
                              (quoteformstr(type),
                               type in self.filtercolor and " checked>" or ">",
                               type[1:-1]))

            if len(allcolor) > 5:
		request.write(u'<option value="%s"%s%s</option><br>\n' %
		  	  (NO_TYPE,
		  	  NO_TYPE in self.filtercolor and " selected>" or ">",
		          _("No type")))
		request.write(u'</select><br>\n')
    	    else:
		request.write(u'<input type="checkbox" name="filtercolor" ' +
		          u'value="%s"%s%s<br>\n' %
		          (NO_TYPE,
		          NO_TYPE in self.filtercolor and
		          " checked>"
		          or ">",
		          _("No type")))

	# filter nodes (related to orderby)
	if getattr(self, 'orderby', '_hier') != '_hier':
    	    request.write(u'<td valign=top>\n<u>' + _('Ordered:') + u'</u><br>\n')
            allorder = set(filter(self.oftype_p, self.filterorder))
            allorder.update(self.orderfiltervalues)
            for txt in [x for x in self.orderfiltervalues if ',' in x]:
                allorder.update(txt)
            allorder = list(allorder)
            allorder.sort()

            if len(allorder) > 5: 
		request.write(u'<select name="filterorder" multiple size=6><br>\n')

            for type in allorder:
                if len(allorder) > 5:
                    request.write(u'<option value="%s"%s%s</option><br>\n' %
                              (quoteformstr(type),
                              type in self.filterorder and " selected>" or ">",
                              type[1:-1]))
                else:
                    request.write(u'<input type="checkbox" name="filterorder" ' +
                              u'value="%s"%s%s<br>\n' %
                              (quoteformstr(type),
                               type in self.filterorder and " checked>" or ">",
                               type[1:-1]))

            if len(allorder) > 5:
                request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (NO_TYPE,
                          NO_TYPE in self.filterorder and " selected>" or ">",
                          _("No type")))
                request.write(u'</select><br>\n')
            else:
                request.write(u'<input type="checkbox" name="filterorder" ' +
                          u'value="%s"%s%s<br>\n' %
                          (NO_TYPE,
                           NO_TYPE in self.filterorder
                           and " checked>"
                           or ">",
                           _("No type")))
        request.write(u"</table>\n")
        request.write(u'</div>\n')
        request.write(u'</div>\n')

        # End form
        request.write(u'<div class="showgraph-buttons">\n')
        request.write(u'<input type=submit name=graph ' +
                      'value="%s">\n' % _('Create'))
        request.write(u'<input type=submit name=test ' +
                      'value="%s">\n' % _('Test'))
        request.write(u'<input type=submit name=inline ' +
                      'value="%s">\n</form>\n' % _('Inline'))
        request.write(u'</div>\n')

        request.write(u'<script type="text/javascript">')
        request.write(u'document.getElementById(\'tab0\').style.display="block";\n')
        request.write(u'document.getElementById(\'tab1\').style.display="none";\n')
        request.write(u'document.getElementById(\'tab2\').style.display="none";\n')

        request.write(u'function toggle(table){\n')
        request.write(u'var tableElementStyle=document.getElementById(table).style;\n')
        request.write(u'if (tableElementStyle.display=="none"){\n')
        request.write(u'tableElementStyle.display="block";\n')
        request.write(u'}else{tableElementStyle.display="none";}\n')
        request.write(u'}</script>\n')

    def generateLayout(self, outgraph):
        # Add all data to graph
        gr = GraphRepr(outgraph, engine=self.graphengine, order='_order')

        if getattr(self, 'orderby', '_hier') != '_hier':
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
        _ = self.request.getText

        if map:
            imgbase = "data:image/" + self.format + ";base64," + b64encode(img)

            page = ('<img src="%s" alt="%s" usemap="#%s">\n' % 
                    (imgbase, _('visualisation'), gr.graphattrs['name']))

            self.sendMap(gr.graphviz)
        else:
            imgbase = "data:image/svg+xml;base64," + b64encode(img)
            
            page = ('<embed height=800 width=1024 src="%s" alt="%s">\n' %
                    (imgbase, _('visualisation')))

        self.request.write(page)

    def sendMap(self, graphviz):
        mappi = self.getLayoutInFormat(graphviz, 'cmapx')

        # Dot output is utf-8
        self.request.write(unicode(mappi, config.charset) + '\n')

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
        _ = self.request.getText
        legend = None
        if self.coloredges or self.colornodes:
            legend = self.makeLegend()

        if legend:
            img = self.getLayoutInFormat(legend, self.format)
            
            if self.format == 'svg':
                imgbase = "data:image/svg+xml;base64," + b64encode(img)
                self.request.write('<embed width=800 src="%s">\n' % imgbase)
            else:
                imgbase = "data:image/" + self.format + \
                          ";base64," + b64encode(img)
                self.request.write('<img src="%s" alt="%s" usemap="#%s">\n' %
                                   (imgbase, _('visualisation'), legend.name))
                self.sendMap(legend)
                                   
    def sendFooter(self, formatter):
        if self.format != 'dot' or not gv_found:
            # End content
            self.request.write(formatter.endContent()) # end content div
            # Footer
            wikiutil.send_footer(self.request, self.pagename)
        else:
            raise MoinMoinNoFooter

    def sendHeaders(self):
        request = self.request
        pagename = self.pagename
        _ = request.getText

        if self.format != 'dot' or not gv_found:
            request.http_headers()
            # This action generate data using the user language
            request.setContentLanguage(request.lang)
  
            title = _(u'Wiki linkage as seen from') + \
                    '"%s"' % pagename

            wikiutil.send_title(request, title, pagename=pagename)

            # fix for moin 1.3.5
            if not hasattr(request, 'formatter'):
                formatter = HtmlFormatter(request)
            else:
                formatter = request.formatter

            # Start content - IMPORTANT - without content div, there is no
            # direction support!
            request.write(formatter.startContent("content"))
            formatter.setPage(self.request.page)
        else:
            request.http_headers(["Content-type: text/plain;charset=%s" %
                                  config.charset])
            formatter = TextFormatter(request)
            formatter.setPage(self.request.page)

        return formatter

    def doTraverse(self, graphdata, outgraph, nodes):
        newnodes = nodes
    
        for n in range(1, self.depth+1):
            outgraph = self.traverseParentChild(graphdata, outgraph, newnodes)
            newnodes = set(outgraph.nodes)
            # continue only if new pages were found
            newnodes = newnodes.difference(nodes)
            if not newnodes:
                break
            nodes.update(newnodes)

        return outgraph

    def browserDetect(self):
        if 'MSIE' in self.request.getUserAgent():
            self.parts = list()
            self.sendGraph = self.sendGraphIE
            self.sendLegend = self.sendLegendIE
            self.sendHeaders = self.sendHeadersIE
            self.sendFooter = self.sendFooterIE

    def fail_page(self, reason):
        self.request.write(self.request.formatter.text(reason))
        self.request.write(self.request.formatter.endContent())
        wikiutil.send_footer(self.request, self.pagename)

    def edgeTooltips(self, outgraph):
        for edge in outgraph.edges:
            e = outgraph.edges.get(*edge)
            # Fix linktypes to strings
            linktypes = getattr(e, 'linktype', [NO_TYPE])
            lt = ', '.join(linktypes)

            e.linktype = lt

            # Double URL quoting? I have created a monster!
            filtstr = str()
            for lt in linktypes:
                filtstr += '&filteredges=%s' % lt
            e.URL = self.request.request_uri + filtstr

            # For display cosmetics, don't show _notype
            # as it's a bit ugly
            ltdisp = ', '.join(x for x in linktypes if x != NO_TYPE)
            val = '%s>%s>%s' % (edge[0], ltdisp, edge[1])

            e.tooltip = val
            
        return outgraph

    def execute(self):        
        cl.start('execute')
        _ = self.request.getText

        self.browserDetect()

        error = self.formargs()
        
        formatter = self.sendHeaders()

        if error:
            self.pagename = self.pagename
            self.fail_page(error)
            return

        if self.isstandard:
            self.fail_page(_("No graph data available."))
            return
            
        # The working with patterns goes a bit like this:
        # First, get a sequence, add it to outgraph
        # Then, match from outgraph, add graphviz attrs
#        self.request.write('execute' + repr(self.request.user).replace('<', ' ').replace('>', ' ') + '<br>')

        cl.start('build')
        # First, let's get do the desired traversal, get outgraph
        #print "Init-build <br> <br>"
        graphdata = self.buildGraphData()
        #print "Out-graph built <br> <br>"
        outgraph = self.buildOutGraph()
        #print "Init-build over <br> <br>"
        cl.stop('build')

        cl.start('traverse')
        # Start pattern searches from current page +
        # nodes gathered as per form args
        nodes = set(self.startpages)
        #print "Traverse"
        outgraph = self.doTraverse(graphdata, outgraph, nodes)
        #print "Traverse over"
        cl.stop('traverse')
        
        if gv_found:
            cl.start('layout')
            # Stylistic stuff: Color nodes, edges, bold startpages
            if self.colorby:
                outgraph = self.colorNodes(outgraph)
            outgraph = self.colorEdges(outgraph)
            outgraph = self.edgeTooltips(outgraph)
            outgraph = self.circleStartNodes(outgraph)

            # Fix URL:s
            outgraph = self.fixNodeUrls(outgraph)

            # Do the layout
            gr = self.generateLayout(outgraph)
            cl.stop('layout')

        cl.start('format')
        if self.help == 'inline':
            self.sendForm()
            urladd = self.request.page.page_name + \
                     self.urladd.replace('&inline=Inline', '')
            urladd = urladd.replace('action=ShowGraph',
                                    'action=ShowGraphSimple')
            self.request.write('[[InlineGraph(%s)]]' % urladd)
        elif self.format in ['svg', 'dot', 'png']:
            if not gv_found:
                self.sendForm()
                self.request.write(formatter.text(_(\
                    "ERROR: Graphviz Python extensions not installed. " +\
                    "Not performing layout.")))
            elif self.format == 'svg':
                self.sendForm()
                self.sendGraph(gr)
                self.sendLegend()
            elif self.format == 'dot':
                self.sendGv(gr)
            elif self.format == 'png':
                self.sendForm()
                self.sendGraph(gr, True)
                self.sendLegend()
        else:
            # Test graph
            self.sendForm()
            self.request.write(formatter.paragraph(1))
            self.request.write(formatter.text("%s: " % _("Nodes in graph") +
                                              str(len(outgraph.nodes))))
            self.request.write(formatter.paragraph(0))
            
            self.request.write(formatter.paragraph(1))
            self.request.write(formatter.text("%s: " % _("Edges in graph") +
                                              str(len(outgraph.edges))))
            self.request.write(formatter.paragraph(0))

            if getattr(self, 'orderby', '_hier') != '_hier':
                self.request.write(formatter.paragraph(1))
                self.request.write(formatter.text("%s: " % _("Order levels") +
                                                    str(len(
                    self.ordernodes.keys()))))
                self.request.write(formatter.paragraph(0))

            self.request.write(formatter.paragraph(1))
            self.request.write("%s: " % _('Density'))
            nroedges = float(len(outgraph.edges))
            nronodes = float(len(outgraph.nodes))
            self.request.write(str(nroedges / (nronodes*nronodes-1)))
            self.request.write(formatter.paragraph(0))

        cl.stop('format')

        cl.stop('execute')
        # print cl.dump()

        self.sendFooter(formatter)

    # IE versions of some relevant functions

    def sendGraphIE(self, gr, map=False):
        _ = self.request.getText
        img = self.getLayoutInFormat(gr.graphviz, self.format)
        filename = gr.graphattrs['name'] + "." + self.format

        if map:
            self.parts.append((filename,
                               'image/' + self.format,
                               b64encode(img)))
            
            page = ('<img src="%s" alt="%s" usemap="#%s">\n' %
                    (filename, _('visualisation'), gr.graphattrs['name']))
            self.sendMap(gr.graphviz)
        else:
            self.parts.append((filename,
                               'image/svg+xml',
                               b64encode(img)))

            page = ('<embed height=800 width=1024 src="%s" alt=">\n' %
                    (filename, _('visualisation')))

        self.request.write(page)

    def sendLegendIE(self):
        _ = self.request.getText
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

                self.request.write('<embed width=800 src="%s">\n' % filename)
            else:
                self.parts.append((filename,
                                   'image/' + self.format,
                                   b64encode(img)))
            
                self.request.write('<img src="%s" alt="%s" usemap="#%s">\n'
                                   (filename, _('visualisation'), legend.name))
                self.sendMap(legend)

    def sendPartsIE(self):
        for part in self.parts:
            self.request.write(add_mime_part(*part))        

    def sendHeadersIE(self):
        request = self.request
        pagename = self.pagename

        if self.format != 'dot' or not gv_found:
            request.write(msie_header)
            _ = request.getText

            title = _('Wiki linkage as seen from') + \
                    '"%s"' % pagename
            wikiutil.send_title(request, title, pagename=pagename)

            # Start content - IMPORTANT - without content div, there is no
            # direction support!
            formatter = HtmlFormatter(request)
            request.write(formatter.startContent("content"))
            formatter.setPage(self.request.page)
        else:
            request.http_headers(["Content-type: text/plain;charset=%s" %
                                  config.charset])
            formatter = TextFormatter(request)
            formatter.setPage(self.request.page)

        return formatter

    def sendFooterIE(self, formatter):
        if self.format != 'dot' or not gv_found:
            # End content
            self.request.write(formatter.endContent()) # end content div
            # Footer
            wikiutil.send_footer(self.request, self.pagename)
            self.request.write('</body>\n</html>\n')
            self.sendPartsIE()
            self.request.write(msie_end)

        raise MoinMoinNoFooter

def execute(pagename, request):
    graphshower = GraphShower(pagename, request)
    graphshower.execute()
