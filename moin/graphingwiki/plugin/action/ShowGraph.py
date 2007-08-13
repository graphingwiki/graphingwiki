# -*- coding: iso-8859-1 -*-
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
from MoinMoin.action import AttachFile

from MoinMoin.request import Clock
cl = Clock()

from graphingwiki.graph import Graph
from graphingwiki.graphrepr import GraphRepr, Graphviz
from graphingwiki.patterns import *

# imports from other actions
from savegraphdata import local_page

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

graphvizcolors = ["aquamarine1", "blue", "brown4", "burlywood",
"chocolate3", "cornflowerblue", "crimson", "cyan", "darkkhaki",
"darkolivegreen3", "darksalmon", "darkseagreen", "darkslateblue",
"darkslategray", "darkviolet", "deeppink", "deepskyblue", "gray33",
"forestgreen", "gold2", "goldenrod", "gray", "green", "greenyellow",
"hotpink", "lavender", "lightpink", "lightsalmon",
"lightseagreen", "lightskyblue", "lightsteelblue", "limegreen",
"magenta", "maroon", "mediumaquamarine", "mediumorchid1",
"mediumpurple", "mediumseagreen", "olivedrab", "orange", "orangered",
"palegoldenrod", "palegreen", "palevioletred", "peru", "plum",
"red2", "rosybrown", "royalblue4", "salmon", "slategray",
"springgreen", "steelblue", "tomato3", "turquoise",
"violetred", "yellow", "yellowgreen"]

hotcoldgradient = ['#00008f', '#00009f', '#0000af', '#0000bf', '#0000cf',
'#0000df', '#0000ef', '#0000ff', '#000fff', '#001fff', '#002fff',
'#003fff', '#004fff', '#005fff', '#006fff', '#007fff', '#008fff',
'#009fff', '#00afff', '#00bfff', '#00cfff', '#00dfff', '#00efff',
'#00ffff', '#0fffef', '#1fffdf', '#2fffcf', '#3fffbf', '#4fffaf',
'#5fff9f', '#6fff8f', '#7fff7f', '#8fff6f', '#9fff5f', '#afff4f',
'#bfff3f', '#cfff2f', '#dfff1f', '#efff0f', '#ffff00', '#ffef00',
'#ffdf00', '#ffcf00', '#ffbf00', '#ffaf00', '#ff9f00', '#ff8f00',
'#ff7f00', '#ff6f00', '#ff5f00', '#ff4f00', '#ff3f00', '#ff2f00',
'#ff1f00', '#ff0f00', '#ff0000', '#ef0000', '#df0000', '#cf0000',
'#bf0000', '#af0000', '#9f0000', '#8f0000', '#7f0000']

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

# Escape quotes to numeric char references, remove outer quotes.
def quoteformstr(text):
    text = text.strip("\"'")
    text = text.replace('"', '&#x22;')
    return unicode('&#x22;' + text + '&#x22;', config.charset)

def quotetoshow(text):
    return unicode(url_unquote(text), config.charset)

class GraphShower(object):
    def __init__(self, pagename, request, graphengine = "neato"):
        # Fix for mod_python, globals are bad
        self.used_colors = []
        self.used_colorlabels = []

        self.pagename = pagename
        self.request = request
        self.graphengine = graphengine
        self.available_formats = ['png', 'svg', 'dot']
        self.format = 'png'
        self.traverse = self.traverseParentChild
        self.limit = ''
        self.hidedges = 0
        self.edgelabels = 0

        self.isstandard = False
        self.interwikilist = []
        
        self.categories = []
        self.otherpages = []
        self.startpages = []

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

        # Selected colors, function used and postprocessing function
        self.colors = graphvizcolors
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
        self.ordernodes = {}
        self.unordernodes = set()

        # For test, inline
        self.help = ""

        # Node filter of an existing type
        self.oftype_p = lambda x: x != '_notype'
 
        # Category, Template matching regexps
        self.cat_re = re.compile(request.cfg.page_category_regex)
        self.temp_re = re.compile(request.cfg.page_template_regex)

    def hashcolor(self, string):
        # Black edges must be black
        if string == '_notype':
            return "black"
        
        if string in self.used_colorlabels:
            return self.used_colors[self.used_colorlabels.index(string)]

        seed(string)
        cl = choice(self.colors)
        while cl in self.used_colors:
            cl = choice(self.colors)
        self.used_colors.append(cl)
        self.used_colorlabels.append(string)
        return cl

    def gradientcolor(self, string):
        clrnodes = sorted(self.colornodes)
        if len(clrnodes) > 1:
            step = (len(self.colors) / (len(clrnodes) - 1)) - 1
        else:
            step = 0
        return self.colors[clrnodes.index(string)*step]
            
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
            if otherpages:
                self.otherpages = [url_quote(encode(x.strip()))
                                   for x in otherpages.split(',')]
            
        # Limit
        if request.form.has_key('limit'):
            self.limit = ''.join([x for x in request.form['limit']])
            
        # Rankdir
        if request.form.has_key('dir'):
            self.rankdir = encode(''.join([x for x in request.form['dir']]))

        # Hide edges
        if request.form.has_key('hidedges'):
            self.hidedges = 1

        # Hide edges
        if request.form.has_key('edgelabels'):
            self.edgelabels = 1

        # Orderings
        if request.form.has_key('orderby'):
            self.orderby = encode(''.join(request.form['orderby']))
            # Checked due to weirdo problems with ShowGraphSimple
            if self.orderby:
                self.graphengine = 'dot'            
        if request.form.has_key('colorby'):
            self.colorby = encode(''.join(request.form['colorby']))

        # Color schema
        if request.form.has_key('colorscheme'):
            self.colorscheme = encode(''.join(request.form['colorscheme']))
            if self.colorscheme == 'gradient':
                self.colors = hotcoldgradient
                self.colorfunc = self.gradientcolor

        # Regexps
        if request.form.has_key('orderreg'):
            self.orderreg = encode(''.join(request.form['orderreg']))
        if request.form.has_key('ordersub'):
            self.ordersub = encode(''.join(request.form['ordersub']))
        if self.ordersub and self.orderreg:
            try:
                self.re_order = re.compile(self.orderreg)
            except:
                error = "Erroneus regexp: s/%s/%s/" % (self.orderreg,
                                                       self.ordersub)
        if request.form.has_key('colorreg'):
            self.colorreg = encode(''.join(request.form['colorreg']))
        if request.form.has_key('colorsub'):
            self.colorsub = encode(''.join(request.form['colorsub']))
        if self.colorsub and self.colorreg:
            try:
                self.re_color = re.compile(self.colorreg)
            except:
                error = "Erroneus regexp: s/%s/%s/" % (self.colorreg,
                                                       self.colorsub)

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
        if request.form.has_key('filtercats'):
            self.filtercats.update(
                [encode(attr) for attr in request.form['filtercats']])

        # This is the URL addition to the nodes that have graph data
        self.urladd = '?'
        for key in request.form:
            for val in request.form[key]:
                self.urladd = (self.urladd + url_quote(encode(key)) +
                               '=' + url_quote(encode(val)) + '&')
        self.urladd = self.urladd[:-1]

        # Disable output if testing graph
        if request.form.has_key('test'):
            self.format = ''
            self.help = 'test'

        # Show inline graph
        if request.form.has_key('inline'):
            self.help = 'inline'

        return error

    def addToStartPages(self, graphdata, pagename):
        self.startpages.append(pagename)
        root = graphdata.nodes.add(pagename)
        root.URL = './' + pagename

        return graphdata

    def addToAllCats(self, nodename):
        if not self.do_form:
            return

        opageobj = Page(self.request,
                        unicode(url_unquote(nodename),
                                config.charset))
        self.allcategories.update(opageobj.getCategories(self.request))

    def buildGraphData(self):
        graphdata = Graph()

        pagedir = self.request.page.getPagePath()
        pagename = url_quote(encode(self.pagename))
        self.pagename = pagename

        for nodename in self.otherpages:
            graphdata = self.addToStartPages(graphdata, nodename)
            self.addToAllCats(nodename)

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
            if not self.request.user.may.read(unicode(url_unquote(cat),
                                                      config.charset)):
                continue
            catpage = self.globaldata.getpage(cat)
            if not catpage.has_key('in'):
                # graphdata not in sync on disk -> malicious input 
                # or something has gone very, very wrong
                # FIXME: Should raise an exception here and end the misery?
                break
            for type in catpage['in']:
                for newpage in catpage['in'][type]:
                    if not (self.cat_re.search(newpage) or
                            self.temp_re.search(newpage)):
                        graphdata = self.addToStartPages(graphdata, newpage)
                        self.addToAllCats(newpage)

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

        return outgraph
    
    def _handleordervalue(self, value):
        # IP addresses and numeric values get special treatment
        try:
            value = int(value.strip('"'))
        except ValueError:
            try:
                value = float(value.strip('"'))
            except ValueError:
                if value.strip('"').replace('.', '').isdigit():
                    try:
                        # 00 is stylistic to avoid this:
                        # >>> sorted(['a', socket.inet_aton('100.2.3.4'),
                        #     socket.inet_aton('1.2.3.4')])
                        # ['\x01\x02\x03\x04', 'a', 'd\x02\x03\x04']
                        value = '00' + socket.inet_aton(value.strip('"'))
                    except socket.error:
                        pass
                pass

        return value

    def addToGraphWithFilter(self, graphdata, outgraph, obj1, obj2):
        # Get edge from match, skip if filtered
        olde = graphdata.edges.get(obj1.node, obj2.node)
        types = olde.linktype.copy()
        for type in types:
            if type in self.filteredges:
                olde.linktype.remove(type)
        if olde.linktype == set([]):
            return outgraph, False

#         if getattr(olde, 'linktype', '_notype') in self.filteredges:
#             return outgraph, False

        # Add nodes, data for ordering
        for obj in [obj1, obj2]:
            # If traverse limited to startpages
            if self.limit == 'start':
                if not obj.node in self.startpages:
                    continue
            # or to pages within the wiki
            elif self.limit == 'wiki':
                if not obj.URL[0] in ['.', '/']:
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
                for rule in [set(qpirts_p(x)) for x in filt if ',' in x]:
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

            # Add page categories to selection choices in the form
            # (for local pages only)
#            print obj.node
            if obj.URL[0] in ['.', '/']:
                self.addToAllCats(obj.node)

            # Category filter
            for filt in self.filtercats:
                filt = '"%s"' % filt
                cats = getattr(obj, 'WikiCategory', set([]))
                if filt in cats:
                    return outgraph, False

            # update nodeattrlist with non-graph/sync ones
            self.nodeattrs.update(nonguaranteeds_p(obj))
            n = outgraph.nodes.add(obj.node)
            n.update(obj)

            # User rights have been checked before, as traverse
            # uses GraphData.load_graph, which handles them
            pagedata = self.globaldata.getpage(obj.node)
            # Add tooltip, if applicable
            # Only add non-guaranteed attrs to tooltip
            if (pagedata.has_key('meta') and
                not hasattr(obj, 'tooltip')):
                pagemeta = nonguaranteeds_p(pagedata['meta'])
                tooldata = '\n'.join([url_unquote("-%s: %s" %
                                      (x,
                                       qstrip_p(
                    pagedata['meta'][x]).strip('"')
                                       ))
                                      for x in pagemeta])
                n.tooltip = '%s\n%s' % (url_unquote(obj.node), tooldata)


            # Shapefiles
            if getattr(obj, 'shapefile', None):
                # Stylistic stuff: label, borders
                # "Note that user-defined shapes are treated as a form
                # of box shape, so the default peripheries value is 1
                # and the user-defined shape will be drawn in a
                # bounding rectangle. Setting peripheries=0 will turn
                # this off."
                # http://www.graphviz.org/doc/info/attrs.html#d:peripheries
                n.label = ' '
                n.peripheries = '0'

                # Non-attachment shapefiles arbitrary (SVG, anyone?)
                if not hasattr(obj, 'shapefile'):
                    continue
                #if not obj.shapefile.startswith('attachment:'):
                #    continue
                
                # Enter file path for attachment shapefiles
                value = obj.shapefile[11:]
                components = value.split('/')
                if len(components) == 1:
                    page = obj.node
                else:
                    page = '/'.join(components[:-1])
                file = components[-1]
                # get attach file path, empty label
                n.shapefile = AttachFile.getFilename(self.request,
                                                     page, file)
                n.tooltip = url_unquote(obj.node)
#            elif 'AttachFile' in obj.node:
#                # Have shapefiles of image attachments
#                if obj.node.split('.')[-1] in ['gif', 'png', 'jpg', 'jpeg']:
#                    print obj.node

            if getattr(self, 'orderby', '_hier') != '_hier':
                value = getattr(obj, self.orderby, None)
                if value:
                    # Add to self.ordernodes by combined value of metadata
                    value = qstrip_p(value)
                    # Add to filterordervalues in the nonmodified form
                    self.orderfiltervalues.add(value)
                    re_order = getattr(self, 're_order', None)
                    if re_order:
                        # Don't remember the reason for quotes right now,
                        # so just keeping them
                        value = value.strip('"')
                        value = '"' + re_order.sub(self.ordersub, value) + '"'

                    # Graphviz attributes must be strings
                    n._order = value

                    # Internally, some values are given a special treatment
                    value = self._handleordervalue(value)
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
        def getcolors(obj):
            rule = getattr(obj, colorby, None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                rule = qstrip_p(rule)
                re_color = getattr(self, 're_color', None)
                # Add to filterordervalues in the nonmodified form
                self.colorfiltervalues.add(rule)
                if re_color:
                    rule = rule.strip('"')
                    rule = '"' + re_color.sub(self.colorsub, rule) + '"'
                self.colornodes.add(rule)

        def updatecolors(obj):
            rule = getattr(obj, colorby, None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                rule = qstrip_p(rule)
                re_color = getattr(self, 're_color', None)
                if re_color:
                    rule = rule.strip('"')
                    rule = '"' + re_color.sub(self.colorsub, rule) + '"'
                obj.fillcolor = self.colorfunc(rule)
                obj.style = 'filled'

        lazyhas = LazyConstant(lambda x, y: hasattr(x, y))

        nodes = outgraph.nodes.getall()
        node = Fixed(Node())
        cond = Cond(node, lazyhas(node, colorby))
        for obj in match(cond, (nodes, outgraph)):
            getcolors(obj)

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
            self.coloredges.update(filter(self.oftype_p, obj.linktype))
            obj.color = ':'.join(self.hashcolor(x) for x in obj.linktype)
            if self.edgelabels:
                obj.decorate = 'true'
                obj.label = ','.join(url_unquote(x) for x in obj.linktype
                                     if x != '_notype')
        return outgraph

    def fixNodeUrls(self, outgraph):
        import re
        _ = self.request.getText
        
        # Make a different url for start nodes
        for nodename in self.startpages:
            node = outgraph.nodes.get(nodename)
            if node:
                node.URL = './\N'
                if not node.label:
                    node.label = url_unquote(nodename)

        # You managed to filter out all your pages, dude!
        if not outgraph.nodes.getall():
            outgraph.label = encode(_("No data"))
            outgraph.bgcolor = 'white'

        # Make the attachment node labels look nicer
        # Also fix overlong labels
        for name, in outgraph.nodes.getall():
            node = outgraph.nodes.get(name)
            # If local link:
            if node.URL[0] in ['.', '/']:
                node.URL = url_unquote(node.URL)
                # If attachment
                if 'action=AttachFile' in node.URL:
                    node.label = encode(_("Attachment")) + ":\n" + \
                                 re.search('target=(.+)&?', node.URL).group(1)

            elif len(node.label) == 0 and len(node.URL) > 50:
                node.label = node.URL[:47] + '...'
            elif len(node.label) > 50:
                node.label = node.label[:47] + '...'
            elif not ':' in node.label:
                node.label = node.URL

        subrank = self.pagename.count('/')
        # Fix URLs for subpages
        if subrank > 0:
            for name, in outgraph.nodes.getall():
                node = outgraph.nodes.get(name)
                # All nodes should have URL:s, change relative ones
                if local_page(node.URL):
                    node.URL = '../' * (subrank-1) + '.' + node.URL
            self.pagename = '../' * (subrank) + self.pagename

        return outgraph

    def circleStartNodes(self, outgraph):
        # Have bold circles on startnodes
        for node in [outgraph.nodes.get(name) for name in self.startpages]:
            if node:
                # Do not circle image nodes
                if hasattr(node, 'shapefile'):
                    continue
                if hasattr(node, 'style'):
                    node.style = node.style + ', bold'
                else:
                    node.style = 'bold'

        return outgraph

    def getURLns(self, link):
        # Find out subpage level to adjust URL:s accordingly
        subrank = self.request.page.page_name.count('/')
        if not self.interwikilist:
            self.interwikilist = get_interwikilist(self.request)
        # Namespaced names
        if ':' in link:
            iwname = link.split(':')
            if self.interwikilist.has_key(iwname[0]):
                return self.interwikilist[iwname[0]] + iwname[1]
            else:
                return '../' * subrank + './InterWiki'
        # handle categories differently as ordernodes:
        # they will just direct to the category page
        if link == 'WikiCategory':
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
            # should be, weäll have to check out which of the different
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
                sg.nodes.add(cur_ordernode, label=label[1:-1], URL=label[1:-1])
            else:
                sg.nodes.add(cur_ordernode, label=label[1:-1], URL=orderURL)
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

            # Some values get special treatment
            heady = self._handleordervalue(heady)
            taily = self._handleordervalue(taily)

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
        legendgraph = Graphviz('legend', rankdir='LR', constraint='false')
        legend = legendgraph.subg.add("clusterLegend",
                                      label=encode(_('Legend')))
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

                legend.edges.add((ln1, ln2), color=self.hashcolor(linktype),
                                 label=url_unquote(linktype),
                                 URL=self.getURLns(linktype))
                per_row = per_row + 1

        # Nodes
        prev = ''
        per_row = 0

        for nodetype in sorted(self.colornodes):
            cur = 'self.colornodes: ' + nodetype
            legend.nodes.add(cur, label=nodetype[1:-1], style='filled',
                             fillcolor=self.colorfunc(nodetype), URL=colorURL)
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
        request.write(u'<form method="GET" action="%s">\n' %
                      quotetoshow(self.pagename))
        request.write(u'<input type=hidden name=action value="%s">' %
                      ''.join(request.form['action']))

        request.write(u"<table>\n<tr>\n")

        # outputformat
        request.write(u"<td>\n" + _("Output format") + u"<br>\n")
        for type in self.available_formats:
            request.write(u'<input type="radio" name="format" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.format and " checked>" or ">",
                           type))


        # Depth
        request.write(_("Link depth") + u"<br>\n")
        request.write(u'<input type="text" name="depth" ' +
                      u'size=2 value="%s"><br>\n' % str(self.depth))

        # categories
        request.write(u"<td>" + _("Include page categories") + "<br>\n")
        for type in self.allcategories:
            request.write(u'<input type="checkbox" name="categories" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type in self.categories and " checked>" or ">",
                           type))

        # otherpages
        otherpages = quotetoshow(', '.join(self.otherpages))
        request.write(_("Include other pages") + u"<br>\n")
        request.write(u'<input type="text" name="otherpages" ' +
                      u'size=20 value="%s"><br>\n' % otherpages)

        # limit
        request.write(u'<input type="radio" name="limit" ' +
                      u'value="start"%s' %
                      (self.limit == 'start' and ' checked>' or '>') + 
                      _('Show links between these pages only') + u'<br>\n')
        request.write(u'<input type="radio" name="limit" ' +
                      u'value="wiki"%s' %
                      (self.limit == 'wiki' and ' checked>' or '>') + 
                      _('Only include pages in this wiki') + u'<br>\n')
        request.write(u'<input type="radio" name="limit" ' +
                      u'value=""%s' %
                      (self.limit == '' and ' checked>' or '>') +
                      _('Include all links') + u'<br>\n')

        def sortShuffle(types):
            types = sorted(types)
            if 'WikiCategory' in types:
                types.remove('WikiCategory')
                types.insert(0, 'WikiCategory')
            return types

        # colorby
        request.write(u"<td>\n" + _('Color by') + u"<br>\n")
        types = sortShuffle(self.nodeattrs)
        for type in types:
            request.write(u'<input type="radio" name="colorby" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.colorby and " checked>" or ">",
                           quotetoshow(type)))
        request.write(u'<input type="radio" name="colorby" ' +
                      u'value=""%s%s<br>\n' %
                      (self.colorby == '' and " checked>" or ">",
                       _("no coloring")))
        if self.colorby:
            request.write(u'<select name="colorscheme">')
            for ord, name in zip(['random', 'gradient'],
                                 [_('random'), _('gradient')]):
                request.write('<option %s label="%s" value="%s">%s</option>\n'%
                              (self.colorscheme == ord and 'selected' or '',
                               ord, ord, name))
            request.write(u'</select><br>\n' + _('Color regexp') + '<br>\n')
            request.write(u'<input type=text name="colorreg" size=10 ' +
                          u'value="%s"><br>\n' % str(self.colorreg))
            request.write(_('substitution') + '<br>\n')
            request.write(u'<input type=text name="colorsub" size=10 ' +
                          u'value="%s"><br>\n' % str(self.colorsub))

        # orderby
        request.write(u"<td>\n" + _('Order by') + "<br>\n")
        types = sortShuffle(self.nodeattrs)
        for type in types:
            request.write(u'<input type="radio" name="orderby" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.orderby and " checked>" or ">",
                           quotetoshow(type)))
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
            request.write('<select name="dir">')
            for ord, name in zip(['TB', 'BT', 'LR', 'RL'],
                              [_('top to bottom'), _('bottom to top'),
                               _('left to right'), _('right to left')]):
                request.write('<option %s label="%s" value="%s">%s</option>\n'%
                              (self.rankdir == ord and 'selected' or '',
                               ord, ord, name))
            if self.orderby != '_hier':
                request.write(u'</select><br>\n' + _('Order regexp') +
                              u'<br>\n')
                request.write(u'<input type=text name="orderreg" size=10 ' +
                              u'value="%s"><br>\n' % str(self.orderreg))
                request.write(_('substitution') + u'<br>\n')
                request.write(u'<input type=text name="ordersub" size=10 ' +
                              u'value="%s"><br>\n' % str(self.ordersub))
            
        # filter edges
        request.write(u'<td>\n' + _('Filter edges') + u'<br>\n')
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
                       _("No type")))

        # hide edges
        request.write(u'<br>' + _('Hide edges') + 
                      u'<input type="checkbox" name="hidedges" ' +
                      u'value="1"%s\n' %
                      (self.hidedges and ' checked>' or '>'))

        # show edge labels
        request.write(u'<br>' + _('Edge labels') + 
                      u'<input type="checkbox" name="edgelabels" ' +
                      u'value="1"%s\n' %
                      (self.edgelabels and ' checked>' or '>'))

        # filter nodes (related to colorby)
        if self.colorby:
            request.write(u'<td>\n' + _('Filter from colored') + u'<br>\n')
            allcolor = set(filter(self.oftype_p, self.filtercolor))
            allcolor.update(self.colorfiltervalues)
            for txt in [x for x in self.colorfiltervalues if ',' in x]:
                allcolor.update(qpirts_p(txt))
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
                           "_notype" in self.filtercolor and
                           " checked>"
                           or ">",
                           _("No type")))

        if getattr(self, 'orderby', '_hier') != '_hier':
            # filter nodes (related to orderby)
            request.write(u'<td>\n' + _('Filter from ordered') + u'<br>\n')
            allorder = set(filter(self.oftype_p, self.filterorder))
            allorder.update(self.orderfiltervalues)
            for txt in [x for x in self.orderfiltervalues if ',' in x]:
                allorder.update(qpirts_p(txt))
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
                           "_notype" in self.filterorder
                           and " checked>"
                           or ">",
                           _("No type")))

        if self.allcategories:
            # filter categories
            request.write(u"<td>" + _('Filter page categories') + u"<br>\n")
            for type in self.allcategories:
                request.write(u'<input type="checkbox" name="filtercats" ' +
                              u'value="%s"%s%s<br>\n' %
                              (type,
                               type in self.filtercats and " checked>" or ">",
                               type))

        # End form
        request.write(u"</table>\n")
        request.write(u'<input type=submit name=graph ' +
                      'value="%s">\n' % _('Create'))
        request.write(u'<input type=submit name=test ' +
                      'value="%s">\n' % _('Test'))
        request.write(u'<input type=submit name=inline ' +
                      'value="%s">\n</form>\n' % _('Inline'))

    def generateLayout(self, outgraph):
        # Add all data to graph
        gr = GraphRepr(outgraph, engine=self.graphengine, order='_order')

        # After this, edit gr.graphviz, not outgraph!
        outgraph.commit()

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
        _ = request.getText

        if self.format != 'dot':
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

    def fail_page(self, reason):
        self.request.write(self.request.formatter.text(reason))
        self.request.write(self.request.formatter.endContent())
        wikiutil.send_footer(self.request, self.pagename)

    def edgeTooltips(self, outgraph):
        for edge in outgraph.edges.getall():
            e = outgraph.edges.get(*edge)
            # Fix linktypes to strings
            lt = ', '.join(filter(self.oftype_p,
                                  getattr(e, 'linktype', ['_notype'])))
            e.linktype = lt

            val = '%s>%s>%s' % (url_unquote(edge[0]),
                                lt != '_notype' and url_unquote(lt) or '',
                                url_unquote(edge[1]))
            # Double URL quoting? I have created a monster!
            e.URL = self.request.request_uri + '&filteredges=%s' % \
                    url_quote(lt)
            e.tooltip = val
            
        return outgraph

    def execute(self):        
        cl.start('execute')
        _ = self.request.getText

        self.browserDetect()

        error = self.formargs()
        
        formatter = self.sendHeaders()

        if error:
            self.pagename = url_quote(encode(self.pagename))
            self.fail_page(error)
            return

        if self.isstandard:
            self.fail_page(_("No graph data available."))
            return
            
        # The working with patterns goes a bit like this:
        # First, get a sequence, add it to outgraph
        # Then, match from outgraph, add graphviz attrs
#        self.request.write('execute' + repr(self.request.user).replace('<', ' ').replace('>', ' ') + '<br>')

        # Init WikiNode-pattern
#        print "Starting to init WikiNode"
        self.globaldata = WikiNode(request=self.request,
                                   urladd=self.urladd,
                                   startpages=self.startpages).graphdata

        cl.start('build')
        # First, let's get do the desired traversal, get outgraph
#        print "Init-build <br> <br>"
        graphdata = self.buildGraphData()
        #        print "Out-graph built <br> <br>"
        # Stupid ugly hack:
        # after saving page, the code execution seems to
        # go pretty erratic, buildgraphdata is somehow
        # executed two times over (??), leaving the
        # db closed - hence opening the db again
        # here seems to do the trick?
        if not self.globaldata.opened:
            self.globaldata.opendb()
        outgraph = self.buildOutGraph()
#        print "Init-build over <br> <br>"
        cl.stop('build')

        cl.start('traverse')
        # Start pattern searches from current page +
        # nodes gathered as per form args
        nodes = set(self.startpages)
#        print "Traverse"
        outgraph = self.doTraverse(graphdata, outgraph, nodes)
#        print "Traverse over"
        cl.stop('traverse')

        cl.start('layout')
        # Stylistic stuff: Color nodes, edges, bold startpages
        if self.colorby:
            outgraph = self.colorNodes(outgraph)
        outgraph = self.colorEdges(outgraph)
        outgraph = self.edgeTooltips(outgraph)
        outgraph = self.circleStartNodes(outgraph)

        # Fix URL:s
        outgraph = self.fixNodeUrls(outgraph)

#        self.request.write("Da nodes:" + repr(outgraph.nodes.getall()))

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
            self.sendForm()
            self.request.write(formatter.paragraph(1))
            self.request.write(formatter.text("%s: " % _("Nodes in graph") +
                                              str(len(
                outgraph.nodes.getall()))))
            self.request.write(formatter.paragraph(0))
            
            self.request.write(formatter.paragraph(1))
            self.request.write(formatter.text("%s: " % _("Edges in graph") +
                                              str(len(
                outgraph.edges.getall()))))
            self.request.write(formatter.paragraph(0))

            if getattr(self, 'orderby', '_hier') != '_hier':
                self.request.write(formatter.paragraph(1))
                self.request.write(formatter.text("%s: " % _("Order levels") +
                                                    str(len(
                    self.ordernodes.keys()))))
                self.request.write(formatter.paragraph(0))

        cl.stop('format')

        cl.stop('execute')
        # print cl.dump()

        self.globaldata.closedb()
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

        if self.format != 'dot':
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
        if self.format != 'dot':
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
