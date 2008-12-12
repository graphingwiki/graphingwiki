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
from MoinMoin.macro.Include import _sysmsg

from MoinMoin.request import Clock
cl = Clock()

from graphingwiki.graph import Graph
from graphingwiki.graphrepr import GraphRepr, Graphviz, gv_found
from graphingwiki.patterns import attachment_file, url_parameters, get_url_ns, url_escape, load_parents, load_children, nonguaranteeds_p, NO_TYPE, actionname, form_escape
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

# The selection form ending
form_end = u"""<div class="showgraph-buttons">\n
<input type=submit name=graph value="%s">
<input type=submit name=test value="%s">
<input type=submit name=inline value="%s">
</form>
</div>

<script type="text/javascript">
  document.getElementById('tab0').style.display="block";
  document.getElementById('tab1').style.display="none";
  document.getElementById('tab2').style.display="none";

  function toggle(table){
    var tableElementStyle=document.getElementById(table).style;
    if (tableElementStyle.display == "none") {
      tableElementStyle.display="block";
    }else{
      tableElementStyle.display="none";
    }
  }
</script>"""

def form_optionlist(request, name, data, comparison, 
                    default_args=dict(), radio=False):
    # Function to make a checkbox/radio or option/selection list,
    # depending on input size. The set of data is displayed, and the
    # items matching comparison selected.
    
    # The list defaults to checkboxes, use radio for radio buttons

    check_type = 'checked'
    input_type = 'checkbox'

    if len(data) > 5: 
        request.write(u'<select name="%s" multiple size=6><br>\n' % 
                      form_escape(name))
        check_type = 'selected'
    elif radio:
        input_type = 'radio'

    # If radio list is desired, single selections on the list are implied
    if radio:
        replvalue = lambda type, name: (form_escape(type),
                comparison==type and " %s>" % check_type or ">",
                form_escape(name))
    else:
        replvalue = lambda type, name: (form_escape(type),
                type in comparison and " %s>" % check_type or ">",
                form_escape(name))

    for type in data:
        if len(data) > 5:
            request.write(u'<option value="%s"%s%s</option><br>\n' % 
                          replvalue(type, type))
        else:
            request.write(u'<input type="%s" name="%s" ' % (input_type, name) +
                          u'value="%s"%s%s<br>\n' % 
                          replvalue(type, type))

    # Default values can be also included in the list
    for default, default_name in default_args.items():
        if len(data) > 5:
            request.write(u'<option value="%s"%s%s</option><br>\n' % 
                          replvalue(default, default_name))
        else:
            request.write(u'<input type="%s" name="%s" ' % (input_type, name) +
                      u'value="%s"%s%s<br>\n' % 
                          replvalue(default, default_name))
    if len(data) > 5:
        request.write(u'</select><br>\n')


def form_textbox(request, name, size, value):
    request.write(u'<input type="text" name="%s" ' % (name) +
                  u'size=%s value="%s"><br>\n' % 
                  (form_escape(str(size)), form_escape(value)))

def form_checkbox(request, name, value, test, text):
    # Unscale
    request.write(u'<input type="checkbox" name="%s" ' % (name) +
                  u'value="%s"%s%s\n' % 
                  (form_escape(value),
                   test and ' checked>' or '>',
                   form_escape(text)))

class GraphShower(object):
    EDGE_WIDTH = 2.0
    EDGE_DARKNESS = 0.83
    FRINGE_DARKNESS = 0.50
  
    def __init__(self, pagename, request, graphengine = "neato"):
        self.hashcolor = self.wrap_color_func(self.hashcolor)
        self.gradientcolor = self.wrap_color_func(self.gradientcolor)
    
        # Fix for mod_python, globals are bad
        self.used_colors = dict()

        self.pagename = pagename
        # Page the graph appears in, used in inline graphs
        self.app_page = pagename

        self.request = request
        self.graphengine = graphengine
        self.available_formats = ['png', 'svg', 'dot']
        self.format = 'png'
        self.limit = ''
        self.unscale = 0
        self.hidedges = 0
        self.edgelabels = 0
        self.noloners = 0

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
        self.nodes_in_edge = set()
        self.allcategories = set()
        self.filteredges = set()
        self.filterorder = set()
        self.filtercolor = set()
        self.filtercats = set()
        self.dir = 'LR'

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

    def wrap_color_func(self, func):
        def color_func(string, darknessFactor=1.0):
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
        return color_func

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
            
    def form_args(self):
        request = self.request
        error = False
        
        if self.do_form:
            # Get categories for current page, for the category form
            self.allcategories.update(request.page.getCategories(request))
        
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
            self.otherpages = [x.strip() for x in 
                               ','.join(request.form["otherpages"]).split(',')
                               if x.strip()]

        # String arguments, only include non-empty
        for arg in ['limit', 'dir', 'orderby', 'colorby', 'colorscheme',
                    'orderreg', 'ordersub', 'colorreg', 'colorsub']:
            if request.form.get(arg):
                setattr(self, arg, ''.join(request.form[arg]))

        # Toggle arguments
        for arg in ['unscale', 'hidedges', 'edgelabels', 'noloners']:
            if request.form.has_key(arg):
                setattr(self, arg, 1)

        # Set attributes
        for arg in ['filteredges', 'filtercats']:
            if request.form.has_key(arg):
                data = getattr(self, arg)
                data.update(request.form[arg])

        if self.orderby:
            self.graphengine = 'dot'

        if self.colorscheme == 'gradient':
            self.colorfunc = self.gradientcolor

        # Evaluating regexes
        if self.ordersub and self.orderreg:
            try:
                self.re_order = re.compile(self.orderreg)
            except:
                error = "Erroneus regexp: s/%s/%s/" % (self.orderreg,
                                                       self.ordersub)

        if self.colorsub and self.colorreg:
            try:
                self.re_color = re.compile(self.colorreg)
            except:
                error = "Erroneus regexp: s/%s/%s/" % (self.colorreg,
                                                       self.colorsub)

        # Update filters only if needed
        if self.orderby and request.form.has_key('filterorder'):
            self.filterorder.update(request.form['filterorder'])
        if self.colorby and request.form.has_key('filtercolor'):
            self.filtercolor.update(request.form['filtercolor'])

        # This is the URL addition to the nodes that have graph data
        self.urladd = url_parameters(request.form)

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
                val = ''.join(request.form[attr])
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

        # Calculate scaling factor
        if not self.unscale:
            self.size = "%.2f,%.2f" % ((self.width / 72),
                                       (self.height / 72))

        return error

    def categories_add(self, cats):
        if not cats:
            return

        # No need to list all categories if the list is not going to be used
        if not self.do_form:
            return

        self.allcategories.update(cats)

    def build_graph_data(self):
        self.graphdata = Graph()

        pagedir = self.request.page.getPagePath()
        pagename = self.pagename

        def get_categories(nodename):
            pagedata = self.request.graphdata.getpage(nodename)
            return pagedata.get('out', dict()).get('gwikicategory', list())

        for nodename in self.otherpages:
            self.startpages.append(nodename)
            load_node(self.request, self.graphdata, nodename, self.urladd)
            self.categories_add(get_categories(nodename))

        # Do not add self to graph if self is category or
        # template page and we're looking at categories
        if not self.categories:
            self.startpages.append(pagename)
        elif not (self.cat_re.search(pagename) or
                  self.temp_re.search(pagename)):
            self.startpages.append(pagename)

        # If categories specified in form, add category pages to startpages
        for cat in self.categories:
            # Permissions
            if not self.request.user.may.read(cat):
                continue
            catpage = self.request.graphdata.getpage(cat)
            for type in catpage.get('in', dict()):
                for newpage in catpage['in'][type]:
                    if not (self.cat_re.search(newpage) or
                            self.temp_re.search(newpage)):
                        load_node(self.request, self.graphdata, 
                                  newpage, self.urladd)
                        self.startpages.append(newpage)
                        self.categories_add(get_categories(newpage))

    def build_outgraph(self):
        outgraph = Graph()        

        if self.orderby and self.orderby != '_hier':
            outgraph.clusterrank = 'local'
            outgraph.compound = 'true'

        # Add neato-specific layout stuff
        if self.graphengine == 'neato':
            outgraph.overlap = 'compress'
            outgraph.splines = 'true'

        outgraph.rankdir = self.dir

        # Formatting features here!
        outgraph.bgcolor = "transparent"

        if self.size:
            outgraph.size = self.size

        return outgraph
    
    def graph_add_filtered(self, outgraph, obj1, obj2):
        _ = self.request.getText

        obj1name, obj2name = unicode(obj1), unicode(obj2)
        
        # Filter linktypes
        olde = self.graphdata.edges.get(obj1name, obj2name)
        types = olde.linktype.copy()
        for type in types:
            if type in self.filteredges:
                olde.linktype.remove(type)
        if not olde.linktype:
            return

        # Add nodes, data for ordering
        for obj in [obj1, obj2]:
            # If previously marked as removed, do not continue
            if hasattr(obj, 'gwikiremove'):
                continue

            objname = unicode(obj)

            # If traverse limited to startpages
            if self.limit == 'start':
                if not objname in self.startpages:
                    continue
            # or to pages within the wiki
            elif self.limit == 'wiki':
                # The gwikiURL is set in patterns
                if not obj.gwikiURL[0] == '.':
                    continue

            # If node already added, nothing to do
            if outgraph.nodes.get(objname):
                continue

            # Node filters
            for filt, doby in [(self.filterorder, self.orderby),
                               (self.filtercolor, self.colorby)]:

                # If no filters, continue
                if not doby or not filt:
                    continue

                # Filtering of untyped nodes
                if not getattr(obj, doby, list()) and NO_TYPE in filt:
                    obj.gwikiremove = True
                    break
                # If filter is not relevant to this node
                elif not getattr(obj, doby, list()):
                    continue
                
                # Filtering by metadata values
                target = set(getattr(obj, doby))
                for rule in set(filt):

                    if rule in target:
                        # Filter only the metadata values filtered
                        target.remove(rule)
                        setattr(obj, doby, list(target))

                # If all values of object were filtered, filter object
                if not target:
                    obj.gwikiremove = True
                    break

            # If object marked as removed from graph while filtering
            if hasattr(obj, 'gwikiremove'):
                continue

            cats = set(obj.gwikicategory)
            filtered = False

            # Filter pages by category
            for filt in self.filtercats:
                if filt in cats:
                    cats.remove(filt)
                    obj.gwikicategory = list(cats)
                    filtered = True

            if filtered and not cats:
                obj.gwikiremove = True
                continue

            if not hasattr(obj, 'gwikiremove'):
                # Not filtered - add node
                outgraph.nodes.add(objname)

        # When not to add edge: 
        # if the inclusion of nodes is limited and a node not in the graph
        if self.limit:
            if not (outgraph.nodes.get(obj1name) and
                    outgraph.nodes.get(obj2name)):
                return
        # if one of the nodes is marked as deleted in the graph
        if hasattr(obj1, 'gwikiremove') or hasattr(obj2, 'gwikiremove'):
            return

        e = outgraph.edges.add(obj1name, obj2name)
        e.update(olde)

        # Count connected so that unconnected ones can be filtered
        if self.noloners:
            self.nodes_in_edge.update([obj1name, obj2name])

        # Hide edges if applicable
        if self.hidedges:
            e.style = "invis"

    def gather_layout_data(self, outgraph):
        _ = self.request.getText

        delete = set()

        for objname in outgraph.nodes:
            obj = self.graphdata.nodes.get(objname)

            # List loner pages to be filtered
            if self.noloners:
                if objname not in self.nodes_in_edge:
                    delete.add(objname)
                    continue

            # update nodeattrlist with non-graph/sync ones
            self.nodeattrs.update(nonguaranteeds_p(obj))
            n = outgraph.nodes.get(objname)
            n.update(obj)

            # User rights have been checked before, at traverse
            pagedata = self.request.graphdata.getpage(objname)

            # Add page categories to selection choices in the form
            # (for local pages only, ie. existing and saved)
            if pagedata.get('saved', False):
                self.categories_add(obj.gwikicategory)

            # Add tooltip, if applicable
            # Only add non-guaranteed attrs to tooltip
            pagemeta = dict()
            for key in pagedata.get('meta', dict()):
                pagemeta[key] = [x for x in pagedata['meta'][key]]
            for key in pagedata.get('out', dict()):
                pagemeta.setdefault(key, list()).extend(pagedata['out'][key])

            if (pagemeta and not hasattr(obj, 'gwikitooltip')):
                pagekeys = nonguaranteeds_p(pagemeta)
                tooldata = '\n'.join("-%s: %s" % 
                                     (x == '_notype' and _('Links') or x,
                                      ', '.join(pagemeta[x]))
                                     for x in pagekeys)
                n.gwikitooltip = '%s\n%s' % (objname, tooldata)

            # Shapefiles
            if getattr(obj, 'gwikishapefile', None):
                # Enter file path for attachment shapefiles
                value = obj.gwikishapefile[11:]
                components = value.split('/')
                if len(components) == 1:
                    page = objname
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

            # Ordernodes setup
            if self.orderby and self.orderby != '_hier':
                value = getattr(obj, self.orderby, None)

                if value:
                    # Add to filterordervalues in the nonmodified form
                    self.orderfiltervalues.update(value)
                    # Add to self.ordernodes by combined value of metadata
                    value = ', '.join(sorted(value))

                    re_order = getattr(self, 're_order', None)
                    if re_order:
                        value = re_order.sub(self.ordersub, value)

                    # Graphviz attributes must be strings
                    n.gwikiorder = value

                    # Internally, some values are given a special treatment
                    value = ordervalue(value)

                    self.ordernodes.setdefault(value, set()).add(objname)
                else:
                    self.unordernodes.add(objname)

        # Delete the loner pages
        for page in delete:
            outgraph.nodes.delete(page)

        return outgraph

    def traverse_one(self, outgraph, nodes):
        # self.graphdata is the 'in' graph extended and traversed

        request = self.request
        urladd = self.urladd

        cl.start('traverseparent')
        # This traverses 1 to parents
        for node in nodes:
            parents = load_parents(request, self.graphdata, node, urladd)
            nodeitem = self.graphdata.nodes.get(node)
            for parent in parents:
                parentitem = self.graphdata.nodes.get(parent)
                self.graph_add_filtered(outgraph, parentitem, nodeitem)
        cl.stop('traverseparent')

        cl.start('traversechild')
        # This traverses 1 to children
        for node in nodes:
            children = load_children(request, self.graphdata, node, urladd)
            nodeitem = self.graphdata.nodes.get(node)
            for child in children:
                childitem = self.graphdata.nodes.get(child)
                self.graph_add_filtered(outgraph, nodeitem, childitem)
        cl.stop('traversechild')

        return outgraph

    def color_nodes(self, outgraph):
        colorby = self.colorby

        # If we should color nodes, gather nodes with attribute from
        # the form (ie. variable colorby) and change their colors, plus
        # gather legend data
        def getcolors(obj):
            rule = getattr(obj, colorby, None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                self.colorfiltervalues.update(rule)
                rule = ', '.join(sorted(rule))
                re_color = getattr(self, 're_color', None)
                # Add to filterordervalues in the nonmodified form
                if re_color:
                    rule = re_color.sub(self.colorsub, rule)
                self.colornodes.add(rule)

        def updatecolors(obj):
            rule = getattr(obj, colorby, None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                rule = ', '.join(sorted(rule))
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

    def color_edges(self, outgraph):
        # Add color to edges with linktype, gather legend data
        edges = filter(lambda x: getattr(x, "linktype", None), 
                       [outgraph.edges.get(*x) for x in outgraph.edges])
        for obj in edges:
            self.coloredges.update(filter(self.oftype_p, obj.linktype))
            obj.color = ':'.join(self.hashcolor(x, self.EDGE_DARKNESS) 
                                 for x in obj.linktype)
            style = getattr(obj, "style", "")
            if style:
                style += ","
            obj.style = style + "setlinewidth(%.02f)" % self.EDGE_WIDTH
            if self.edgelabels:
                obj.decorate = 'true'
                obj.label = ','.join(x for x in obj.linktype if x != NO_TYPE)
                                     
        return outgraph

    def fix_node_urls(self, outgraph):
        _ = self.request.getText
        
        # Make page links to startpages instead of navigation ones
        for nodename in self.startpages:
            node = outgraph.nodes.get(nodename)
            if node:
                node.gwikiURL = './\N'

        # You managed to filter out all your pages, dude!
        if not outgraph:
            outgraph.label = _("No data")
            outgraph.bgcolor = 'white'

        # Make the attachment node labels look nicer
        # Also fix overlong labels
        for name in outgraph.nodes:
            node = outgraph.nodes.get(name)
            if not hasattr(node, 'gwikilabel'):
                node.gwikilabel = name

            # local full-path relative links
            if node.gwikiURL[0] == '/':
                continue
            # local relative links
            elif node.gwikiURL[0] == '.':
                node.gwikiURL = self.request.getScriptname() + \
                                node.gwikiURL.lstrip('.')
            # Shorten the labels of long URL:s
            elif len(node.gwikilabel) == 0 and len(node.gwikiURL) > 50:
                node.gwikilabel = node.gwikiURL[:47] + '...'
            elif len(node.gwikilabel) > 50:
                node.gwikilabel = node.gwikilabel[:47] + '...'
            elif not ':' in node.gwikilabel:
                node.gwikilabel = node.gwikiURL

        return outgraph

    def circle_start_nodes(self, outgraph):
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

    def make_legend(self):
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

        colorURL = get_url_ns(self.request, self.app_page, self.colorby)
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
                                 URL=get_url_ns(self.request, self.app_page,
                                                linktype))
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


    def send_form(self):
        request = self.request
        _ = request.getText

        self.request.write('<!-- $Id$ -->\n')

        ## Begin form
        request.write(u'<div class="showgraph-form">\n')
        request.write(u'<form method="GET" action="%s">\n' %
                      actionname(request, self.pagename))
        request.write(u'<input type=hidden name=action value="%s">' %
                      form_escape(''.join(request.form['action'])))

        request.write(u'<div class="showgraph-panel1">\n')
	# PANEL 1 
        request.write(u'<a href="javascript:toggle(\'tab0\')">'+
                      u'View & Include</a><br>\n')
        request.write(u'<table border="1" id="tab0"><tr>\n')

        # outputformat
        request.write(u"<td valign=top>\n")
        request.write(u"<u>" + _("Format:") + u"</u><br>\n")
        request.write(u'<select name="format"><br>\n')
        for type in self.available_formats:
            request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (form_escape(type),
                          type == self.format and " selected>" or ">",
                          form_escape(type)))
        request.write(u'</select><br>\n')

        # Height
        request.write(_("Max height") + u"<br>\n")
        form_textbox(request, 'height', 5, str(self.height))

        # Width
        request.write(_("Max width") + u"<br>\n")
        form_textbox(request, 'width', 5, str(self.width))

        # Unscale
        form_checkbox(request, 'unscale', '0', self.unscale, _('Unscale'))

        # hide edges
        request.write(u"<br><u>" + _("Edges:") + u"</u><br>\n")
        form_checkbox(request, 'hidedges', '1', self.hidedges, _('Hide edges'))
        request.write(u'<br>\n')

        # show edge labels
        form_checkbox(request, 'edgelabels', '1', self.edgelabels, 
                      _('Edge labels'))

        request.write(u"<br><u>" + _("Nodes:") + u"</u><br>\n")
        # filter unconnected nodes
        form_checkbox(request, 'noloners', '1', self.noloners, 
                      _('Filter lonely'))

        # Include
	request.write(u"<td valign=top>\n")

        allcategories = self.allcategories
        allcategories.update(self.filtercats)

        # categories
        if allcategories:
            request.write(u"<u>" + _("Categories:") + u"</u><br>\n")
            form_optionlist(request, 'categories', 
                            allcategories, self.categories)

        # Depth
        request.write(u"<u>" + _("Link depth") + u"</u><br>\n")
        form_textbox(request, 'depth', 2, str(self.depth))

        # otherpages
        request.write(u"<td valign=top>\n<u>" + 
                      _("Other pages:") + u"</u><br>\n")
        form_textbox(request, 'otherpages', 20, ', '.join(self.otherpages))

        # limit
        request.write(u"<u>" + _("Include rules:") + u"</u><br>\n")
        for x,y in [('start', _('These pages only')),
                    ('wiki', _('From this wiki only')),
                    ('', _('All links'))]:
            request.write(u'<input type="radio" name="limit" ' +
                          u'value="%s"%s' %
                          (form_escape(x), 
                           self.limit == x and ' checked>' or '>') 
                          + form_escape(y) + u'<br>\n')
                          
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
        request.write(u'<a href="javascript:toggle(\'tab1\')">' +
                      u'Color & Order</a><br>\n')
        request.write(u'<table border="1" id="tab1"><tr>\n')

        # colorby
        request.write(u"<td valign=top>\n")
	request.write(u"<u>" + _("Color by:") + u"</u><br>\n")
        types = sortShuffle(self.nodeattrs)

        form_optionlist(request, 'colorby', types, self.colorby, 
                        {'': _("no coloring")}, True)

        if self.colorby:
	    request.write(u"<td valign=top>\n")
            request.write(u"<u>" + _("Color type:") + u"</u><br>\n")
            request.write(u'<select name="colorscheme">')
            for ord, name in zip(['random', 'gradient'],
                                 [_('random'), _('gradient')]):
                request.write('<option %s label="%s" value="%s">%s</option>\n'%
                              (self.colorscheme == ord and 'selected' or '',
                               form_escape(ord), form_escape(ord), 
                               form_escape(name)))
                          
            request.write(u'</select><br>\n<u>' + _('Color regexp:') + '</u><br>\n')
                          
            form_textbox(request, 'colorreg', 10, str(self.colorreg))
            request.write(u'<u>' + _('substitution:') + '</u><br>\n')
            form_textbox(request, 'colorsub', 10, str(self.colorsub))
	
        # orderby
        request.write(u"<td valign=top>\n")
	request.write(u"<u>" + _("Order by:") + u"</u><br>\n")
        types = sortShuffle(self.nodeattrs)

        form_optionlist(request, 'orderby', types, self.orderby, 
                        {'': _("no ordering"), '_hier': _("hierarchical")},True)
	
        if self.orderby:
	    request.write(u"<td valign=top>\n")
            request.write(u"<u>" + _("Order direction:") + u"</u><br>\n")
            request.write('<select name="dir">')
            for ord, name in zip(['TB', 'BT', 'LR', 'RL'],
                              [_('top to bottom'), _('bottom to top'),
                               _('left to right'), _('right to left')]):
                request.write('<option %s label="%s" value="%s">%s</option>\n'%
                              (self.dir == ord and 'selected' or '',
                               form_escape(ord), form_escape(ord), 
                               form_escape(name)))
            if self.orderby != '_hier':
                request.write(u'</select><br>\n<u>' + _('Order regexp:') +
                              u'</u><br>\n')

                form_textbox(request, 'orderreg', 10, str(self.orderreg))
                request.write(u'<u>' + _('substitution:') + '</u><br>\n')
                form_textbox(request, 'ordersub', 10, str(self.ordersub))

	request.write(u'</table>\n')
        request.write(u'</div>\n')


        request.write(u'<div class="showgraph-panel3">\n')
        # PANEL 3 
        request.write(u'<a href="javascript:toggle(\'tab2\')">' + 
                      u'Filters</a><br>\n')
        request.write(u'<td valign=top><table border="1" id="tab2"><tr>\n')

        # filter edges
        request.write(u'<td valign=top>\n<u>' + _('Edges:') + u'</u><br>\n')
        alledges = list(self.coloredges) + filter(self.oftype_p,
                                                  self.filteredges)
        alledges.sort()

        form_optionlist(request, 'filteredges', alledges, 
                        self.filteredges, {NO_TYPE: _("No type")})

	# filter categories
        if allcategories:
            request.write(u"<td valign=top>\n<u>" + 
                          _('Categories:') + u"</u><br>\n")
            
            form_optionlist(request, 'filtercats', allcategories, 
                            self.filtercats)

        # filter nodes (related to colorby)
        if self.colorby:
            request.write(u"<td valign=top>\n<u>" + 
                          _('Colored:') + u"</u><br>\n")

            allcolor = set(filter(self.oftype_p, self.filtercolor))
            allcolor.update(self.colorfiltervalues)
            allcolor = list(allcolor)
            allcolor.sort()

            form_optionlist(request, 'filtercolor', allcolor, 
                            self.filtercolor, {NO_TYPE: _("No type")})

	# filter nodes (related to orderby)
	if getattr(self, 'orderby', '_hier') != '_hier':
    	    request.write(u'<td valign=top>\n<u>' + 
                          _('Ordered:') + u'</u><br>\n')

            allorder = set(filter(self.oftype_p, self.filterorder))
            allorder.update(self.orderfiltervalues)
            allorder = list(allorder)
            allorder.sort()

            form_optionlist(request, 'filterorder', allorder, 
                            self.filterorder, {NO_TYPE: _("No type")})

        request.write(u"</table>\n</div>\n</div>\n")

        request.write(form_end % (_('Create'), _('Test'), _('Inline')))

    def generate_layout(self, outgraph):
        # Add all data to graph
        gr = GraphRepr(outgraph, self.graphengine)

        if self.orderby and self.orderby != '_hier':
            gr.order_graph(self.ordernodes, 
                           self.unordernodes,
                           self.request,
                           self.app_page,
                           self.orderby)

        return gr

    def get_layout(self, graphviz, format):
        tmp_fileno, tmp_name = mkstemp()
        graphviz.layout(file=tmp_name, format=format)
        f = file(tmp_name)
        data = f.read()
        os.close(tmp_fileno)
        os.remove(tmp_name)

        return data
    
    def send_graph(self, gr, map=False):
        img = self.get_layout(gr.graphviz, self.format)
        _ = self.request.getText

        if map:
            imgbase = "data:image/" + self.format + ";base64," + b64encode(img)

            page = ('<img src="%s" alt="%s" usemap="#%s">\n' % 
                    (imgbase, _('visualisation'), gr.graphattrs['name']))

            self.send_map(gr.graphviz)
        else:
            imgbase = "data:image/svg+xml;base64," + b64encode(img)
            
            page = ('<embed height=800 width=1024 src="%s" alt="%s">\n' %
                    (imgbase, _('visualisation')))

        self.request.write(page)

    def send_map(self, graphviz):
        mappi = self.get_layout(graphviz, 'cmapx')

        # Dot output is utf-8
        # XXX so why does this use config.charset?
        self.request.write(unicode(mappi, config.charset) + '\n')

    def send_gv(self, gr):
        gvdata = self.get_layout(gr.graphviz, 'dot')

        self.request.write(gvdata)

        legend = None
        if self.coloredges or self.colornodes:
            legend = self.make_legend()

        if legend:
            img = self.get_layout(legend, 'dot')
            self.request.write(img)

    def send_legend(self):
        _ = self.request.getText
        legend = None
        if self.coloredges or self.colornodes:
            legend = self.make_legend()

        if legend:
            img = self.get_layout(legend, self.format)
            
            if self.format == 'svg':
                imgbase = "data:image/svg+xml;base64," + b64encode(img)
                self.request.write('<embed width=800 src="%s">\n' % imgbase)
            else:
                imgbase = "data:image/" + self.format + \
                          ";base64," + b64encode(img)
                self.request.write('<img src="%s" alt="%s" usemap="#%s">\n' %
                                   (imgbase, _('visualisation'), legend.name))
                self.send_map(legend)
                                   
    def send_footer(self, formatter):
        if self.format != 'dot' or not gv_found:
            # End content
            self.request.write(formatter.endContent()) # end content div
            # Footer
            self.request.theme.send_footer(self.pagename)
            self.request.theme.send_closing_html()

    def send_headers(self):
        request = self.request
        pagename = self.pagename
        _ = request.getText

        if self.format != 'dot' or not gv_found:
            request.http_headers()
            # This action generate data using the user language
            request.setContentLanguage(request.lang)
  
            title = _(u'Wiki linkage as seen from') + \
                    '"%s"' % pagename

            request.theme.send_title(title, pagename=pagename)

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

    def traverse(self, outgraph, nodes):
        newnodes = nodes

        # Add startpages, even if unconnected
        for node in nodes:
            nodeitem = outgraph.nodes.add(node)
            oldnode = self.graphdata.nodes.get(node)
            if oldnode:
                nodeitem.update(oldnode)
    
        for n in range(1, self.depth+1):
            outgraph = self.traverse_one(outgraph, newnodes)
            newnodes = set(outgraph.nodes)
            # continue only if new pages were found
            newnodes = newnodes.difference(nodes)
            if not newnodes:
                break
            nodes.update(newnodes)

        return outgraph

    def browser_detect(self):
        if 'MSIE' in self.request.getUserAgent():
            self.parts = list()
            self.send_graph = self.send_graph_ie
            self.send_legend = self.send_legend_ie
            self.send_headers = self.send_headers_ie
            self.send_footer = self.send_footer_ie

    def fail_page(self, reason):
        formatter = self.send_headers()
        self.request.write(_sysmsg % ('error', reason))
        self.request.write(self.request.formatter.endContent())
        self.request.theme.send_footer(self.pagename)
        self.request.theme.send_closing_html()

    def edge_tooltips(self, outgraph):
        for edge in outgraph.edges:
            e = outgraph.edges.get(*edge)
            # Fix linktypes to strings
            linktypes = getattr(e, 'linktype', [NO_TYPE])
            lt = ', '.join(linktypes)

            e.linktype = lt

            # Make filter URL for edge
            filtstr = str()
            for lt in linktypes:
                filtstr += '&filteredges=%s' % url_escape(lt)
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

        self.browser_detect()

        # Bail out flag on if underlay page etc.
        if not self.request.page.isStandardPage(includeDeleted=False):
            self.fail_page(_("No graph data available."))
            return

        error = self.form_args()

        formatter = self.send_headers()

        if error:
            self.fail_page(error)
            return
            
        cl.start('build')
        self.build_graph_data()
        outgraph = self.build_outgraph()
        cl.stop('build')

        cl.start('traverse')
        nodes = set(self.startpages)
        # Traverse from startpages, filter as per args
        outgraph = self.traverse(outgraph, nodes)
        # Gather data needed in layout, filter lone pages is needed
        outgraph = self.gather_layout_data(outgraph)
        cl.stop('traverse')
        
        if gv_found:
            cl.start('layout')
            # Stylistic stuff: Color nodes, edges, bold startpages
            if self.colorby:
                outgraph = self.color_nodes(outgraph)
            outgraph = self.color_edges(outgraph)
            outgraph = self.edge_tooltips(outgraph)
            outgraph = self.circle_start_nodes(outgraph)

            # Fix URL:s
            outgraph = self.fix_node_urls(outgraph)

            # Do the layout
            gr = self.generate_layout(outgraph)
            cl.stop('layout')

        cl.start('format')
        if self.help == 'inline':
            self.send_form()
            urladd = self.request.page.page_name + \
                     self.urladd.replace('&inline=Inline', '')
            urladd = urladd.replace('action=ShowGraph',
                                    'action=ShowGraphSimple')
            self.request.write('&lt;&lt;InlineGraph(%s)&gt;&gt;' % urladd)
        elif self.format in ['svg', 'dot', 'png']:
            if not gv_found:
                self.send_form()
                self.request.write(formatter.text(_(\
                    "ERROR: Graphviz Python extensions not installed. " +\
                    "Not performing layout.")))
            elif self.format == 'svg':
                self.send_form()
                self.send_graph(gr)
                self.send_legend()
            elif self.format == 'dot':
                self.send_gv(gr)
            elif self.format == 'png':
                self.send_form()
                self.send_graph(gr, True)
                self.send_legend()
        else:
            self.send_form()
            self.test_graph(outgraph)

        cl.stop('format')

        cl.stop('execute')
        # print cl.dump()

        self.send_footer(formatter)

    def test_graph(self, outgraph):
        _ = self.request.getText
        # Give some parameters about the graph, more could easily be added
        formatter = self.request.formatter
        self.request.write(formatter.paragraph(1))
        self.request.write(formatter.text("%s: " % _("Nodes in graph") +
                                          str(len(outgraph.nodes))))
        self.request.write(formatter.paragraph(0))

        self.request.write(formatter.paragraph(1))
        self.request.write(formatter.text("%s: " % _("Edges in graph") +
                                          str(len(outgraph.edges))))
        self.request.write(formatter.paragraph(0))

        if self.orderby and self.orderby != '_hier':
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

    # IE versions of some relevant functions

    def send_graph_ie(self, gr, map=False):
        _ = self.request.getText
        img = self.get_layout(gr.graphviz, self.format)
        filename = gr.graphattrs['name'] + "." + self.format

        if map:
            self.parts.append((filename,
                               'image/' + self.format,
                               b64encode(img)))
            
            page = ('<img src="%s" alt="%s" usemap="#%s">\n' %
                    (filename, _('visualisation'), gr.graphattrs['name']))
            self.send_map(gr.graphviz)
        else:
            self.parts.append((filename,
                               'image/svg+xml',
                               b64encode(img)))

            page = ('<embed height=800 width=1024 src="%s" alt=">\n' %
                    (filename, _('visualisation')))

        self.request.write(page)

    def send_legend_ie(self):
        _ = self.request.getText
        legend = None
        if self.coloredges or self.colornodes:
            legend = self.make_legend()

        if legend:
            img = self.get_layout(legend, self.format)
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
                self.send_map(legend)

    def send_parts_ie(self):
        for part in self.parts:
            self.request.write(add_mime_part(*part))        

    def send_headers_ie(self):
        request = self.request
        pagename = self.pagename

        if self.format != 'dot' or not gv_found:
            request.write(msie_header)
            _ = request.getText

            title = _('Wiki linkage as seen from') + \
                    '"%s"' % pagename
            request.theme.send_title(title, pagename=pagename)

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

    def send_footer_ie(self, formatter):
        if self.format != 'dot' or not gv_found:
            # End content
            self.request.write(formatter.endContent()) # end content div
            # Footer
            self.request.theme.send_footer(self.pagename)
            self.request.write('</body>\n</html>\n')
            self.send_parts_ie()
            self.request.write(msie_end)


def execute(pagename, request):
    graphshower = GraphShower(pagename, request)
    graphshower.execute()
