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
import re

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from tempfile import mkstemp
from random import choice, seed

from MoinMoin.action import cache
from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.formatter.text_html import Formatter as HtmlFormatter
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from MoinMoin.macro.Include import _sysmsg

from graphingwiki import gv_found, igraph_found, actionname, \
    url_escape, values_to_form, pil_found, pil_image

from graphingwiki.graph import Graph
from graphingwiki.graphrepr import GraphRepr, Graphviz, IGraphRepr

from graphingwiki.util import attachment_file, attachment_url, url_parameters,\
    get_url_ns, load_parents, load_children, nonguaranteeds_p, NO_TYPE, \
    form_escape, load_node, decode_page, template_regex, category_regex, \
    encode_page, make_tooltip, cache_exists, SPECIAL_ATTRS, cache_key, \
    xml_document, xml_node_id_and_text, geoip_init, geoip_get_coords
from graphingwiki.editing import ordervalue, verify_coordinates

import math
import colorsys

# The selection form ending
form_end = u"""<div class="showgraph-buttons">\n
<input type=submit name=graph value="%%s">
%s
<input type=submit name=test value="%%s">
<input type=submit name=inline value="%%s">
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
</script>""" % (igraph_found and 
                '<input type=submit name=overview value="%s">' or '')

graphvizshapes = ["box", "polygon", "egg", "triangle",
                  "diamond", "trapezium", "parallelogram",
                  "house", "pentagon", "septagon",
                  "octagon", "doublecircle", "doubleoctagon",
                  "tripleoctagon", "invtriangle", "invtrapezium",
                  "invhouse", "Mdiamond", "Msquare", "Mcircle",
                  "rectangle", "note", "tab", "box3d", "component"]

def url_reconstruct(environ):
    # Code from PEP 333
    url = environ['wsgi.url_scheme']+'://'

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']

        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
               url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
               url += ':' + environ['SERVER_PORT']

    url += environ.get('SCRIPT_NAME', '')
    url += decode_page(environ.get('PATH_INFO', ''))
    if environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']
    return url

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
    actionname = 'ShowGraph'
  
    def __init__(self, pagename, request, graphengine = "neato", 
                 urladd='', app_page='', inline=''):
        self.hashcolor = self.wrap_color_func(self.hashcolor)
        self.gradientcolor = self.wrap_color_func(self.gradientcolor)
    
        # Fix for mod_python, globals are bad
        self.used_colors = dict()

        self.inline = inline

        self.pagename = pagename
        # app_page for inline graphs
        if not app_page:
            self.app_page = pagename
        # If we appear on a subpage, links may be screwed - 
        # app_page retains knowledge on the page graph appears in
        else:
            self.app_page = app_page

        self.request = request
        self.graphengine = graphengine
        self.available_formats = ['png', 'svg', 'dot', 'zgr', 'kml']
        self.nonwrapped_formats = ['dot', 'kml']
        self.format = 'png'
        self.limit = ''
        self.unscale = 0
        self.hidedges = 0
        self.edgelabels = 0
        self.noloners = 0
        self.imagelabels = 0
        self.fillshapes = 1

        self.legend = 'bottom'
        self.legend_positions = ['off', 'top', 'bottom', 'left', 'right']

        self.categories = list()
        self.otherpages = list()
        self.startpages = list()

        self.invisnodes = list()
        self.neighbours = list()

        self.depth = 1
        self.orderby = ''
        self.ordershape = ''
        self.colorby = ''
        self.shapeby = ''

        self.orderreg = ""
        self.ordersub = ""
        self.colorreg = ""
        self.colorsub = ""
        self.shapereg = ""
        self.shapesub = ""

        # Lists for the graph layout
        self.nodes_in_edge = set()
        self.allcategories = set()
        self.filteredges = set()
        self.filterorder = set()
        self.filtercolor = set()
        self.filtershape = set()
        self.filtercats = set()
        self.dir = 'LR'
        self.nostartnodes = 0
        self.noorignode = 0

        # Lists for the filter values for the form
        self.orderfiltervalues = set()
        self.colorfiltervalues = set()
        self.shapefiltervalues = set()

        # What to add to node URL:s in the graph
        if urladd:
            self.urladd = urladd
        else:
            self.urladd = ''

        # Selected colorfunction used and postprocessing function
        self.colorfunc = self.hashcolor
        self.colorscheme = 'random'

        # link/node attributes that have been assigned colors
        self.coloredges = set()
        self.colornodes = set()

        # node attributes that have been assigned shapes
        self.used_shapenodes = dict()
        # node attribute values that would need shapes
        self.shapenodes = dict()

        # node attributes
        self.nodeattrs = set()
        # nodes that do and do not have the attribute designated with orderby
        self.ordernodes = dict()
        self.unordernodes = set()

        # Hashes of shapefiles stored for caching
        self.shapefiles = dict()
        self.cache_key = ''

        # SVG shapefiles need some extra work
        self.shapefiles_svg = dict()

        # For test, inline
        self.help = ""

        self.height = 0
        self.width = 0
        self.size = ''

        # Node filter of an existing type
        self.oftype_p = lambda x: x != NO_TYPE
 
        # Category, Template matching regexps
        self.cat_re = category_regex(request)
        self.temp_re = template_regex(request)

        # Threshold of making an automatic overview of graph
        self.overview_threshold = getattr(request.cfg,
                                          'gwiki_overview_threshold', 
                                          150)
        self.no_overview = 0

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

    def select_shape(self, value):
        # Try to select a random shape, but the same for the same value
        seed(value)

        chosen = False
        while not chosen:
            rand_shape = choice(graphvizshapes)
            chosen = True

            # If the shape is chosen for a value, it's ok ..
            if rand_shape in self.used_shapenodes:
                # .. unless the shape is spoken for another value
                if not value == self.used_shapenodes[rand_shape]:
                    chosen = False
            else:
                # If the attr is unallocated, proceed to do so
                self.used_shapenodes[rand_shape] = value

        return rand_shape

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

        if not self.inline:
            # Get categories for current page, for the category form
            self.allcategories.update(request.page.getCategories(request))
        
        # depth
        if request.values.has_key('depth'):
            depth = request.values['depth']
            try:
                depth = int(depth)
                if depth >= 1:
                    self.depth = depth
            except ValueError:
                self.depth = 1

        # When to to do overview?
        if request.values.has_key('overview_threshold'):
            thr = request.values['overview_threshold']
            try:
                thr = int(thr)
                if thr >= 1:
                    self.overview_threshold = thr
            except ValueError:
                # Settle for config limit or default
                pass

        # format
        if request.values.has_key('format'):
            format = request.values['format']
            if format in self.available_formats:
                self.format = format

        # legend
        if request.values.has_key('legend'):
            legend = request.values['legend']
            if legend in self.legend_positions:
                self.legend = legend

        # legend
        if request.values.has_key('ordershape'):
            shape = request.values['ordershape']
            if shape in graphvizshapes + ['none']:
                self.ordershape = shape

        # Categories
        if request.values.has_key('categories'):
            self.categories = request.values.getlist('categories')

        # List arguments of pages
        for arg in ['otherpages', 'invisnodes', 'neighbours']:
            if request.values.has_key(arg):
                setattr(self, arg, [x.strip() for x in 
                                    request.values[arg].split(',') 
                                    if x.strip()])

        # String arguments, only include non-empty
        for arg in ['limit', 'dir', 'orderby', 'colorby', 'colorscheme',
                    'orderreg', 'ordersub', 'colorreg', 'colorsub',
                    'shapeby', 'shapereg', 'shapesub']:
            if request.values.get(arg):
                setattr(self, arg, request.values[arg])

        # Toggle arguments 
        for arg in ['unscale', 'hidedges', 'edgelabels', 'imagelabels',
                    'noloners', 'nostartnodes', 'noorignode', 'fillshapes', 
                    'no_overview']:
            if request.values.has_key(arg):
                setattr(self, arg, 1)

        # Set attributes
        for arg in ['filteredges', 'filtercats', 'filterorder']:
            if request.values.has_key(arg):
                data = getattr(self, arg)
                data.update(request.values.getlist(arg))

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

        if self.shapesub and self.shapereg:
            try:
                self.re_shape = re.compile(self.shapereg)
            except:
                error = "Erroneus regexp: s/%s/%s/" % (self.shapereg,
                                                       self.shapesub)

        # Update filters only if needed
        if self.orderby and request.values.has_key('filterorder'):
            self.filterorder.update(request.values.getlist('filterorder'))
        if self.colorby and request.values.has_key('filtercolor'):
            self.filtercolor.update(request.values.getlist('filtercolor'))
        if self.shapeby and request.values.has_key('filtershape'):
            self.filtershape.update(request.values.getlist('filtershape'))

        # This is the URL addition to the nodes that have graph data
        if not self.urladd:
            self.urladd = url_parameters(values_to_form(request.values))

        # Disable output if testing graph
        if request.values.has_key('test'):
            self.format = ''
            self.help = 'test'

        # Show inline graph
        if request.values.has_key('inline'):
            self.help = 'inline'

        # Show inline graph
        if request.values.has_key('overview'):
            self.format = 'igraph'

        # Height and Width
        for attr in ['height', 'width']:
            if request.values.has_key(attr):
                val = request.values[attr]
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
        if self.inline:
            return

        self.allcategories.update(cats)

    def build_graph_data(self):
        self.graphdata = Graph()

        pagename = self.pagename

        def get_categories(nodename):
            pagedata = self.request.graphdata.get_out(
                nodename).get('gwikicategory', list())

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
            cat_in = self.request.graphdata.get_in(cat)
            for type in cat_in.keys():
                for newpage in cat_in[type]:
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
            outgraph.overlap = 'scalexy'
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
            # Filtering by edges == filtering by in-links
            if ((type in self.filteredges) or 
                (self.orderby == 'gwikiinlinks' and type in self.filterorder)):
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

            obj = self.node_filters(obj)

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
            orig_obj = self.graphdata.nodes.get(objname)

            # List loner pages to be filtered
            if self.noloners:
                if objname not in self.nodes_in_edge:
                    delete.add(objname)
                    continue

            # Startnodes to be filtered, either all startnodes or just
            # the page from where the action is called.
            if self.nostartnodes:
                if objname in self.startpages:
                    delete.add(objname)
                    continue

            if self.noorignode:
                if objname == self.request.page.page_name:
                    delete.add(objname)
                    continue

            # update nodeattrlist with non-graph/sync ones
            self.nodeattrs.update(decode_page(x) 
                                  for x in nonguaranteeds_p(orig_obj))
            obj = outgraph.nodes.get(objname)
            obj.update(orig_obj)

            # User rights have been checked before, at traverse
            pagedata = self.request.graphdata.getpage(objname)

            # Add page categories to selection choices in the form
            # (for local pages only, ie. existing and saved)
            if self.request.graphdata.is_saved(objname):
                if hasattr(orig_obj, 'gwikicategory'):
                    self.categories_add(orig_obj.gwikicategory)

            tooldata = make_tooltip(self.request, objname, self.format)
            if tooldata and not hasattr(orig_obj, 'gwikitooltip'):
                obj.gwikitooltip = '%s\n%s' % (objname, tooldata)

            # Shapefiles
            if not objname in self.invisnodes and \
                    getattr(orig_obj, 'gwikishapefile', None):
                # Enter file path for attachment shapefiles
                value = orig_obj.gwikishapefile[13:-2]
                components = value.split('/')
                if len(components) == 1:
                    page = objname
                else:
                    page = '/'.join(components[:-1])
                fname = components[-1]
                fname = fname.split('|')[0]
                imgwidth = None
                imgheight = None
                if '|' in components[-1]:
                    try:
                        if 'height=' in components[-1]:
                            imgheight = components[-1].split('height=')[-1]
                            if imgheight:
                                imgheight = float(imgheight)
                        if 'width=' in components[-1]:
                            imgwidth = components[-1].split('width=')[-1]
                            if imgwidth:
                                imgwidth = float(imgwidth)
                    except ValueError:
                        pass
                
                shapefile, exists = attachment_file(self.request, page, fname)

                # get attach file path, empty label

                if exists:
                    if pil_found:
                        ckey = cache_key(self.request, (page, value))
                        if cache_exists(self.request, ckey):
                            shapefile = cache._get_datafile(self.request, ckey)
                        else:
                            self.request.write("here")
                            img = pil_image.open(shapefile)
                            save_needed = False
                            if imgwidth or imgheight:
                                save_needed = True
                                w, h = img.size
                                if imgwidth:
                                    ratio = imgwidth / w
                                    w = imgwidth
                                    h = ratio * h
                                if imgheight:
                                    ratio = imgheight / h
                                    h = imgheight
                                    w = ratio * w
                                size = (int(w), int(h))
                                img.thumbnail(size, pil_image.ANTIALIAS)
                            if img.format != "PNG":
                                save_needed = True
                            if save_needed:
                                tmp_fileno, tmp_name = mkstemp('.png')
                                img.save(tmp_name, 'PNG')
                                f = file(tmp_name)
                                data = f.read()
                                os.close(tmp_fileno)
                                os.remove(tmp_name)
                                cache.put(self.request, ckey, data, 
                                          content_type="image/png")
                                shapefile = cache._get_datafile(self.request, 
                                                                ckey)._filename()
                                self.request.write(shapefile)

                    # No sense to present shapefile path with dot output
                    if self.format == 'dot':
                        obj.gwikiimage = fname
                    else:
                        filedata = md5(file(shapefile).read()).hexdigest()
                        self.shapefiles[objname] = filedata

                        if self.format in ['svg', 'zgr']:
                            # Save attachment URL:s for later editing
                            self.shapefiles_svg[shapefile] = \
                                attachment_url(self.request, page, fname)

                            obj.gwikilabel = '<<TABLE BORDER="0" '+\
                                'CELLSPACING="0" CELLBORDER="0"><TR><TD>'+\
                                '<IMG SRC="%s"/></TD></TR></TABLE>>' % \
                                (shapefile)
                        # Present shapefile URL:s in a different way to KML
                        elif self.format == 'kml':
                            obj.gwikiimage = attachment_url(self.request, 
                                                            page, fname)
                        else:
                            obj.gwikiimage = shapefile

                    if self.imagelabels:
                        name = getattr(orig_obj, 'gwikilabel', objname)
                        obj.gwikilabel = '<<TABLE BORDER="0" '+\
                            'CELLSPACING="0" CELLBORDER="0"><TR><TD>'+\
                            '<IMG SRC="%s"/></TD></TR>' % (shapefile)+\
                            '<TR><TD>%s</TD></TR></TABLE>>' % (name)
                        if not self.format in ['svg', 'zgr']:
                            del obj.gwikiimage
                    elif not self.format in ['svg', 'zgr']:
                        # Stylistic stuff: label, borders
                        obj.gwikilabel = ' '
                        obj.gwikistyle = 'filled'
                        obj.gwikifillcolor = 'transparent'

                    # "Note that user-defined shapes are treated as a form
                    # of box shape, so the default peripheries value is 1
                    # and the user-defined shape will be drawn in a
                    # bounding rectangle. Setting peripheries=0 will turn
                    # this off."
                    # http://www.graphviz.org/doc/info/attrs.html#d:peripheries
                    obj.gwikiperipheries = '0'

                del obj.gwikishapefile
                

            # Add data on types of edges for which obj is child
            for parent in outgraph.edges.parents(objname):
                if not self.request.user.may.read(parent):
                    continue
                edgeobj = outgraph.edges.get(parent, objname)
                inlinks = set(getattr(obj, 'gwikiinlinks', list()))
                inlinks.update(getattr(edgeobj, 'linktype'))
                setattr(obj, 'gwikiinlinks', list(inlinks))

        # Delete the loner pages
        for page in delete:
            outgraph.nodes.delete(page)

        # Ordernodes setup
        for objname in outgraph.nodes:
            obj = outgraph.nodes.get(objname)

            if self.orderby and self.orderby != '_hier':
                value = getattr(obj, encode_page(self.orderby), None)

                if value:
                    # Add to filterordervalues in the nonmodified form
                    self.orderfiltervalues.update(value)
                    # Add to self.ordernodes by combined value of metadata
                    value = ', '.join(sorted(value))

                    re_order = getattr(self, 're_order', None)
                    if re_order:
                        value = re_order.sub(self.ordersub, value)

                    # Graphviz attributes must be strings
                    obj.gwikiorder = value

                    # Internally, some values are given a special treatment
                    value = ordervalue(value)

                    self.ordernodes.setdefault(value, set()).add(objname)
                else:
                    self.unordernodes.add(objname)        

        return outgraph

    def traverse_one(self, outgraph, nodes):
        # self.graphdata is the 'in' graph extended and traversed

        request = self.request
        urladd = self.urladd

        # This traverses 1 to parents
        for node in nodes:
            parents = load_parents(request, self.graphdata, node, urladd)
            nodeitem = self.graphdata.nodes.get(node)
            for parent in parents:
                parentitem = self.graphdata.nodes.get(parent)
                self.graph_add_filtered(outgraph, parentitem, nodeitem)

        # This traverses 1 to children
        for node in nodes:
            children = load_children(request, self.graphdata, node, urladd)
            nodeitem = self.graphdata.nodes.get(node)
            for child in children:
                childitem = self.graphdata.nodes.get(child)
                self.graph_add_filtered(outgraph, nodeitem, childitem)

        return outgraph

    def color_nodes(self, outgraph):
        colorby = self.colorby

        # If we should color nodes, gather nodes with attribute from
        # the form (ie. variable colorby) and change their colors, plus
        # gather legend data
        def getcolors(obj):
            rule = getattr(obj, encode_page(colorby), None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                self.colorfiltervalues.update(rule)
                rule = ', '.join(sorted(rule))
                re_color = getattr(self, 're_color', None)
                # Add to filtercolorvalues in the nonmodified form
                if re_color:
                    rule = re_color.sub(self.colorsub, rule)
                self.colornodes.add(rule)

        def updatecolors(obj):
            rule = getattr(obj, encode_page(colorby), None)
            color = getattr(obj, 'fillcolor', None)
            if rule and not color:
                rule = ', '.join(sorted(rule))
                re_color = getattr(self, 're_color', None)
                if re_color:
                    rule = re_color.sub(self.colorsub, rule)
                if (not hasattr(obj, 'gwikiimage') or
                    (hasattr(obj, 'gwikiimage') and self.fillshapes)):
                    obj.gwikifillcolor = self.colorfunc(rule)
                    obj.gwikicolor = self.colorfunc(rule, self.FRINGE_DARKNESS)
                    obj.gwikistyle = 'filled'

        nodes = filter(lambda x: hasattr(x, encode_page(colorby)), 
                       map(outgraph.nodes.get, outgraph.nodes))
        for obj in nodes:
            getcolors(obj)

        for obj in nodes:
            updatecolors(obj)

        return outgraph

    def shape_nodes(self, outgraph):
        _ = self.request.getText
        shapeby = self.shapeby

        # If we should shape nodes, gather nodes with attribute from
        # the form (ie. variable shapeby)
        def getshapes(obj):
            rule = getattr(obj, encode_page(shapeby), None)
            shape = getattr(obj, 'fillshape', None)
            if rule and not shape:
                self.shapefiltervalues.update(rule)
                rule = ', '.join(sorted(rule))
                re_shape = getattr(self, 're_shape', None)
                # Add to filterordervalues in the nonmodified form
                if re_shape:
                    rule = re_shape.sub(self.shapesub, rule)
                self.shapenodes.setdefault(rule, list()).append(obj)

        nodes = filter(lambda x: hasattr(x, encode_page(shapeby)), 
                       map(outgraph.nodes.get, outgraph.nodes))

        for obj in nodes:
            getshapes(obj)

        if len(self.shapenodes) >= len(graphvizshapes):
            return outgraph, _('Shape by: Not enough shapes for value set')

        for key in self.shapenodes.keys():
            for obj in self.shapenodes[key]:
                setattr(obj, 'gwikishape', self.select_shape(key))

        return outgraph, ''

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

            # Invisible nodes do not get label, or much anything else
            if name in self.invisnodes:
                node.gwikistyle = 'invis'
                node.gwikilabel = ''
                node.gwikitooltip = ''
                node.gwikishape = 'point'
                node.gwikiimage = ''
                continue

            if not hasattr(node, 'gwikilabel'):
                node.gwikilabel = name

            # local full-path relative links
            if node.gwikiURL[0] == '/':
                continue
            # local relative links
            elif node.gwikiURL[0] == '.':
                node.gwikiURL = self.request.script_root + \
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

        # Special emphasis on neighbour nodes
        for edge in outgraph.edges:
            if edge[0] in self.neighbours:
                neighbour = edge[1]
            elif edge[1] in self.neighbours:
                neighbour = edge[0]
            else:
                continue

            node = outgraph.nodes.get(neighbour)
            style = getattr(node, 'gwikistyle', '')
            if 'bold' in style:
                style = style.replace('bold', 'setlinewidth(6)')
            elif style:
                style = style + ',setlinewidth(6)'
            else:
                style = 'setlinewidth(6)'

            node.gwikistyle = style

        return outgraph

    def make_legend(self, key):
        _ = self.request.getText
        # Make legend
        if self.size:
            legendgraph = Graphviz(key, rankdir='LR', constraint='false',
                                   **{'size': self.size})

        else:
            legendgraph = Graphviz(key, rankdir='LR', constraint='false')
        legend = legendgraph.subg.add("clusterLegend",
                                      label=_('Legend'))
        subrank = self.pagename.count('/')

        colorURL = get_url_ns(self.request, self.app_page, self.colorby)
        shapeURL = get_url_ns(self.request, self.app_page, self.shapeby)
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

        prev = ''
        per_row = 0

        for nodetype in self.used_shapenodes:
            cur = 'self.shapenodes: ' + nodetype

            legend.nodes.add(cur, shape=nodetype, URL=shapeURL,
                             label=self.used_shapenodes[nodetype])

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
                      actionname(request))
        request.write(u'<input type=hidden name=action value="%s">' %
                      self.actionname)

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

        request.write(_("Legend") + u"<br>\n")
        request.write(u'<select name="legend"><br>\n')
        for type in self.legend_positions:
            request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (form_escape(type),
                           type == self.legend and " selected>" or ">",
                           form_escape(type)))
        request.write(u'</select><br>\n')

        # Unscale
        form_checkbox(request, 'unscale', '0', self.unscale, _('Unscale'))
        request.write(u"<br>\n")

        # Igraph special - by default, 
        if igraph_found:
            form_checkbox(request, 'no_overview', '0', self.no_overview,
                          _('No automatic overview'))
            request.write(u'<br>\n' + _("Overview node threshold") + u"<br>\n")
            form_textbox(request, 'overview_threshold', 5, 
                         str(self.overview_threshold))

        # labels for shapefiles
        form_checkbox(request, 'imagelabels', '0', self.imagelabels, 
                      _('Shapefile labels'))

        # hide edges
        request.write(u"<br><u>" + _("Edges:") + u"</u><br>\n")
        form_checkbox(request, 'hidedges', '1', self.hidedges, _('Hide edges'))
        request.write(u'<br>\n')

        # show edge labels
        form_checkbox(request, 'edgelabels', '1', self.edgelabels, 
                      _('Edge labels'))

        request.write(u"<br><u>" + _("Pages:") + u"</u><br>\n")
        # filter the start page nodes
        form_checkbox(request, 'noorignode', '1', self.noorignode, 
                      _('Filter this page'))
        request.write(u"<br>\n")
        # filter startnodes nodes
        form_checkbox(request, 'nostartnodes', '1', self.nostartnodes, 
                      _('Filter all startpages'))
        request.write(u"<br>\n")
        # filter unconnected nodes
        form_checkbox(request, 'noloners', '1', self.noloners, 
                      _('Filter unlinked pages'))

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

        # invis nodes
        request.write(_("Invisible nodes:") + u"</u><br>\n")
        form_textbox(request, 'invisnodes', 20, ', '.join(self.invisnodes))

        # highlight neighbors
        request.write(_("Highlight neighbors:") + u"</u><br>\n")
        form_textbox(request, 'neighbours', 20, ', '.join(self.neighbours))

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
            if 'gwikiinlinks' in types:
                types.remove('gwikiinlinks')
            types.insert(0, 'gwikiinlinks')
            if 'gwikicategory' in types:
                types.remove('gwikicategory')
            types.insert(0, 'gwikicategory')
            return types

        request.write(u'<div class="showgraph-panel2">\n')
	# PANEL 2
        request.write(u'<a href="javascript:toggle(\'tab1\')">' +
                      u'Color, Order, Shape</a><br>\n')
        request.write(u'<table border="1" id="tab1"><tr>\n')

        # colorby
        request.write(u"<td valign=top>\n")
	request.write(u"<u>" + _("Color by:") + u"</u><br>\n")
        types = set([x for x in self.nodeattrs])
        if self.colorby:
            types.add(self.colorby)

        types = sortShuffle(types)

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
                          
            request.write(u'</select><br>\n<u>' + _('Color regexp:') + \
                              '</u><br>\n')
                          
            form_textbox(request, 'colorreg', 10, str(self.colorreg))
            request.write(u'<u>' + _('substitution:') + '</u><br>\n')
            form_textbox(request, 'colorsub', 10, str(self.colorsub))

            # Fill nodes with shapefiles
            form_checkbox(request, 'fillshapes', '1', self.fillshapes, 
                          _('Fill shapefiles?'))


        # shapeby
        request.write(u"<td valign=top>\n")
	request.write(u"<u>" + _("Shape by:") + u"</u><br>\n")
        types = set([x for x in self.nodeattrs])
        if self.shapeby:
            types.add(self.shapeby)

        types = sortShuffle(types)

        form_optionlist(request, 'shapeby', types, self.shapeby, 
                        {'': _("no shape")}, True)

        if self.colorby:
            request.write(u'</select><br>\n<u>' + _('Shape regexp:') + \
                              '</u><br>\n')
                          
            form_textbox(request, 'shapereg', 10, str(self.shapereg))
            request.write(u'<u>' + _('substitution:') + '</u><br>\n')
            form_textbox(request, 'shapesub', 10, str(self.shapesub))

        # orderby
        request.write(u"<td valign=top>\n")
	request.write(u"<u>" + _("Order by:") + u"</u><br>\n")
        types = set([x for x in self.nodeattrs])
        if self.orderby and self.orderby != '_hier':
            types.add(self.orderby)

        types = sortShuffle(types)

        form_optionlist(request, 'orderby', types, self.orderby, 
                        {'': _("no ordering"), '_hier': _("hierarchical")},True)

        request.write(_("Ordernode type") + u"<br>\n")
        request.write(u'<select name="ordershape"><br>\n')
        for type in graphvizshapes:
            request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (form_escape(type),
                           type == self.ordershape and " selected>" or ">",
                           form_escape(type)))

        addendum = {'': _("default"), 'none': _("none")}
        for val, pr in addendum.iteritems():
            request.write(u'<option value="%s"%s%s</option><br>\n' %
                          (form_escape(val),
                           val == self.ordershape and " selected>" or ">",
                           form_escape(pr)))
        request.write(u'</select><br>\n')
	
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
        request.write(u'<td valign=top>\n<u>' + _("Edges:") + u'</u><br>\n')
        alledges = list(self.coloredges) + filter(self.oftype_p,
                                                  self.filteredges)
        alledges.sort()

        form_optionlist(request, 'filteredges', alledges, 
                        self.filteredges, {NO_TYPE: _("No type")})

	# filter categories
        if allcategories:
            request.write(u"<td valign=top>\n<u>" + 
                          _("Categories:") + u"</u><br>\n")
            
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

        # filter nodes (related to shapeby)
        if self.shapeby:
            request.write(u"<td valign=top>\n<u>" + 
                          _('Shaped:') + u"</u><br>\n")

            allshape = set(filter(self.oftype_p, self.filtershape))
            allshape.update(self.shapefiltervalues)
            allshape = list(allshape)
            allshape.sort()

            form_optionlist(request, 'filtershape', allshape, 
                            self.filtershape, {NO_TYPE: _("No type")})

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

        if igraph_found:
            request.write(form_end % (_('Create'), _('Overview'),
                                      _('Test'), _('Inline')))
        else:
            request.write(form_end % (_('Create'), _('Test'), _('Inline')))

    def generate_layout(self, outgraph):
        # Add all data to graph
        gr = GraphRepr(outgraph, self.graphengine)

        if self.orderby and self.orderby != '_hier':
            gr.order_graph(self.ordernodes, 
                           self.unordernodes,
                           self.request,
                           self.app_page,
                           self.orderby,
                           self.ordershape)

        return gr

    def get_layout(self, grapheng, format, addon=''):
        tmp_fileno, tmp_name = mkstemp(addon)
        grapheng.layout(fname=tmp_name, format=format, 
                        height=self.height, width=self.width)
        f = file(tmp_name)
        data = f.read()
        os.close(tmp_fileno)
        os.remove(tmp_name)

        return data
    
    def get_gv_format(self):
        if self.format in ['zgr', 'svg']:
            return 'svg'

        return self.format

    def send_graph(self, grapheng, key='', text='visualisation'):
        _ = self.request.getText

        self.request.write('<div class="%s-%s">' % (text, self.legend))
        
        if not key:
            key = "%s-%s" % (self.cache_key, self.format)

        gvformat = self.get_gv_format()

        if self.format in ['zgr', 'svg', 'igraph']:
            # Display zgr graphs as applets, legends as per usual
            if self.format == 'zgr' and text != 'legend':
                image_p = lambda url, text, mappi: \
                    '<applet code="net.claribole.zgrviewer.ZGRApplet.class"'+ \
                    ' archive="%s/gwikicommon/zgrviewer/zvtm.jar,' % \
                    (self.request.cfg.url_prefix_static) + \
                    '%s/gwikicommon/zgrviewer/zgrviewer.jar" ' % \
                    (self.request.cfg.url_prefix_static) + \
                    'width="%s" height="%s">' % (self.width, self.height)+\
                    '<param name="type" ' + \
                    'value="application/x-java-applet;version=1.4" />' + \
                    '<param name="scriptable" value="false" />' + \
                    '<param name="svgURL" value="%s" />' % (url) + \
                    '<param name="title" value="ZGRViewer - Applet" />'+ \
                    '<param name="appletBackgroundColor" value="#DDD" />' + \
                    '<param name="graphBackgroundColor" value="#DDD" />' + \
                    '<param name="highlightColor" value="red" />' + \
                    ' </applet><br>\n'
            else:
                image_p = lambda url, text, mappi: \
                    '<object data="%s" alt="%s" ' % (url, text) + \
                    'type="image/svg+xml">\n' + \
                    '<embed src="%s" alt="%s" ' % (url, text) + \
                    'type="image/svg+xml"/>\n</object>'

            mime_type = 'image/svg+xml'
            mappi = ''
        else:
            image_p = lambda url, text, mappi: \
                '<img src="%s" alt="%s"%s\n' % (url, text, mappi)
            mime_type = 'image/%s' % (self.format)
            mappi = unicode(self.send_map(grapheng, key), 'utf-8')
            mappi = ' usemap="#%s">\n%s' % (key, mappi)

        if not cache_exists(self.request, key):
            if self.format == 'igraph':
                img = self.get_layout(grapheng, '', '.svg')
            else:
                img = self.get_layout(grapheng, gvformat)

                # Firefox does not understand point size fonts. Graphviz
                # only provides point-size fonts, so px-size fonts must be
                # set manually. This works also in Inkscape, and when the
                # graph is scaled, as scaling is done with graph attributes.
                #
                # http://groups.google.com/group/mozilla.dev.tech.svg/browse_thread/thread/1d574c2690e37c7b
                # http://www.nabble.com/SVG-font-size-difference-between-Firefox-and-Adobe-SVGviewer-td21502117.html
                # https://mailman.research.att.com/pipermail/graphviz-interest/2007q1/004288.html
                # Firefox 3 barfs on font-weight, so I'm not using it.
                if gvformat == 'svg':
                    img = img.replace(\
                        "font-family:Times New Roman;font-size:14.00;",
                        "font-family:serif;font-size:12px;")

                    # Graphviz does not get it if you try to give it URL:s
                    # as shapefiles. We mitigate this by first giving it
                    # filenames, and then renaming them as URL:s here
                    for fname in self.shapefiles_svg:
                        img = img.replace(fname, 
                                          form_escape(
                                self.shapefiles_svg[fname]))

            cache.put(self.request, key, img, content_type=mime_type)

        image_uri = cache.url(self.request, key)

        self.request.write(image_p(image_uri, _(text), mappi))
        self.request.write(
            u'<a href="%s" id="footer" class="graph-link">[%s]</a>\n' % \
                (image_uri, _('download')) + u'</div>')

    def send_legend(self):
        legend = None

        # If form choice is no legend
        if self.legend == 'off':
            return

        key = "%s-legend-%s" % (self.cache_key, encode_page(self.format))

        if self.coloredges or self.colornodes:
            legend = self.make_legend(key)

        if not legend:
            return

        self.send_graph(legend, key=key, text='legend')

    def send_map(self, graphviz, key):
        key = key + '-cmapx'

        if not cache_exists(self.request, key):
            mappi = self.get_layout(graphviz, 'cmapx')
            cache.put(self.request, key, mappi, content_type="text/html")
        else:
            mappifile = cache._get_datafile(self.request, key)
            mappi = mappifile.read()
            mappifile.close()

        return mappi

    def make_kml(self, outgraph):
        xml, top = xml_document('kml')
        top.setAttribute('xmlns', "http://www.opengis.net/kml/2.2")

        doc = xml_node_id_and_text(xml, top, 'Document')

        for node in outgraph.nodes:
            description = ''
            image = ''
            coords = ''

            # Make a 
            nodeobj = outgraph.nodes.get(node)
            for i, rest in nodeobj:
                if not rest:
                    continue
                if i in SPECIAL_ATTRS:
                    # Insert image as URL
                    if i == 'gwikiimage':
                        image = '<img src= %s>' % \
                            (form_escape(self.request.getQualifiedURL(rest)))
                    # Get any coordinates manually inserted
                    elif i == 'gwikicoordinates':
                        coords = verify_coordinates(rest)
                    continue
                description += '<dt>%s</dt>' % (form_escape(i))

                for j in rest:
                    description += '<dd>%s</dd>' % (form_escape(j))

            # If coordinates on page, get them from geoip
            if not coords:
                coords = geoip_get_coords(self.GEO_IP, node)

            # No coordinates? Do not enter this page to the KML at all
            if not coords:
                continue

            place = xml_node_id_and_text(xml, doc, 'Placemark')
            xml_node_id_and_text(xml, place, 'name', node)

            if description:
                description = '<dl>%s</dl>' % (description)

            description = image + description

            if description:
                desc = xml_node_id_and_text(xml, place, 'description')
                desc.appendChild(xml.createCDATASection(description))

            point = xml_node_id_and_text(xml, place, 'Point')
            xml_node_id_and_text(xml, point, 'coordinates', coords)
        
#        return xml.toxml('utf-8')
        return xml.toprettyxml(encoding='utf-8', indent='  ')

    def send_kml(self, outgraph):
        key = self.cache_key + '-kml'
        
        if not cache_exists(self.request, key):
            gvdata = self.make_kml(outgraph)

            cache.put(self.request, key, gvdata, 
                      content_type="text/vnd.graphviz")
        else:
            gvdatafile = cache._get_datafile(self.request, key)
            gvdata = gvdatafile.read()
            gvdatafile.close()

        self.request.write(gvdata)

    def send_gv(self, gr):
        key = self.cache_key + '-dot'

        if not cache_exists(self.request, key):
            gvdata = self.get_layout(gr.graphviz, 'dot')

            cache.put(self.request, key, gvdata, 
                      content_type="text/vnd.graphviz")
        else:
            gvdatafile = cache._get_datafile(self.request, key)
            gvdata = gvdatafile.read()
            gvdatafile.close()

        self.request.write(gvdata)

        key = self.cache_key + '-legend-dot'

        legend = None
        if self.coloredges or self.colornodes:
            legend = self.make_legend(key)

        if not legend:
            return

        if not cache_exists(self.request, key):
            gvdata = self.get_layout(legend, 'dot')

            cache.put(self.request, key, gvdata, 
                      content_type="text/vnd.graphviz")
        else:
            gvdatafile = cache._get_datafile(self.request, key)
            gvdata = gvdatafile.read()
            gvdatafile.close()

        self.request.write(gvdata)
                                   
    def send_footer(self, formatter):
        if self.format not in self.nonwrapped_formats or not gv_found:
            # End content
            self.request.write(formatter.endContent()) # end content div
            # Footer
            self.request.theme.send_footer(self.pagename)
            self.request.theme.send_closing_html()

    def send_headers(self):
        request = self.request
        pagename = self.pagename
        _ = request.getText

        # If we're inline, don't continue
        if self.inline:
            return request.formatter

        if self.format not in self.nonwrapped_formats or not gv_found:
            # This action generate data using the user language
            request.setContentLanguage(request.lang)
  
            title = _(u'Wiki linkage as seen from') + \
                    '"%s"' % pagename

            request.theme.send_title(title, pagename=pagename)

            formatter = request.formatter

            # fix for moin 1.8
            formatter.page = request.page

            # Start content - IMPORTANT - without content div, there is no
            # direction support!
            request.write(formatter.startContent("content"))
            formatter.setPage(self.request.page)
        else:
            if self.format == 'dot':
                request.content_type = "text/vnd.graphviz;charset=%s" % \
                    config.charset
            elif self.format == 'kml':
                request.content_type = \
                    "application/vnd.google-earth.kml+xml;charset=%s" % \
                    config.charset
            else:
                request.content_type = "text/plain;charset=%s" % \
                    config.charset
            formatter = TextFormatter(request)
            formatter.setPage(request.page)
 
        return formatter

    def node_filters(self, obj):
        # Node filters
        for filt, doby in [(self.filterorder, self.orderby),
                           (self.filtercolor, self.colorby),
                           (self.filtershape, self.shapeby)]:

            # If no filters, continue
            if not doby or not filt:
                continue

            # Filtering of untyped nodes
            if not getattr(obj, encode_page(doby), list()) and NO_TYPE in filt:
                obj.gwikiremove = True
                break
            # If filter is not relevant to this node
            elif not getattr(obj, encode_page(doby), list()):
                continue

            # Filtering by metadata values
            target = set(getattr(obj, encode_page(doby)))
            for rule in set(filt):

                if rule in target:
                    # Filter only the metadata values filtered
                    target.remove(rule)
                    setattr(obj, encode_page(doby), list(target))

            # If all values of object were filtered, filter object
            if not target:
                obj.gwikiremove = True
                break

        # If object marked as removed from graph while filtering
        if hasattr(obj, 'gwikiremove'):
            return obj

        # If not categories to filter, bail out
        if not hasattr(obj, 'gwikicategory'):
            return obj

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

        return obj

    def traverse(self, outgraph, nodes):
        newnodes = set()

        # Add startpages, even if unconnected
        for node in nodes:
            newnodes.add(node)

            # Make sure that startnodes get loaded
            load_node(self.request, self.graphdata, node, self.urladd)

            oldnode = self.graphdata.nodes.get(node)

            # Check that (existing) startnode are properly filtered
            if oldnode:
                oldnode = self.node_filters(oldnode)
                if hasattr(oldnode, 'gwikiremove'):
                    continue

            nodeitem = outgraph.nodes.add(node)
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

    def fail_page(self, reason):
        if not self.inline:
            formatter = self.send_headers()
        else:
            formatter = self.request.formatter

        self.request.write(_sysmsg % ('error', reason))
        self.request.write(formatter.endContent())

        if not self.inline:
            self.request.theme.send_footer(self.pagename)
            self.request.theme.send_closing_html()

    def edge_tooltips(self, outgraph):
        for edge in outgraph.edges:                
            e = outgraph.edges.get(*edge)

            # Edges from invisible nodes do not get attributes
            if (edge[0] in self.invisnodes or 
                edge[1] in self.invisnodes):
                e.color = ''
                e.decorate = ''
                e.label = ''
                e.style = 'invis'

            # Fix linktypes to strings
            linktypes = getattr(e, 'linktype', [NO_TYPE])
            lt = ', '.join(linktypes)

            e.linktype = lt

            # Make filter URL for edge
            filtstr = str()
            for lt in linktypes:
                filtstr += '&filteredges=%s' % url_escape(lt)
            e.URL = url_reconstruct(self.request.environ) + filtstr

            # For display cosmetics, don't show _notype
            # as it's a bit ugly
            ltdisp = ', '.join(x for x in linktypes if x != NO_TYPE)
            val = '%s>%s>%s' % (edge[0], ltdisp, edge[1])
            e.tooltip = val
            
        return outgraph

    def execute(self):
        _ = self.request.getText

        error = self.form_args()
        warnings = list()

        if self.format == 'kml':
            self.GEO_IP, geo_error = geoip_init(self.request)
            if geo_error:
                error += _sysmsg % ('error', geo_error)
                self.format = 'error'

        formatter = self.send_headers()
        
        if error:
            self.fail_page(error)
            return
            
        self.build_graph_data()
        outgraph = self.build_outgraph()

        nodes = set(self.startpages)
        # Traverse from startpages, filter as per args
        outgraph = self.traverse(outgraph, nodes)
        # Gather data needed in layout, filter lone pages is needed
        outgraph = self.gather_layout_data(outgraph)

        # Trigger automated overview of large graphs
        if (igraph_found and 
            not self.no_overview and 
            len(outgraph.nodes) >= self.overview_threshold):
            self.format = 'igraph'

        # kml generation considered a special case
        if self.format == 'kml' and not self.help:
            # Generate cache key
            self.cache_key = cache_key(self.request, [outgraph])
        # Perform layout if we have a layout engine and can use it for
        # the selected output
        elif (gv_found or 
              (igraph_found and 
               (self.format == 'igraph' or self.help == 'test'))):

            if (self.format == 'igraph' or 
                (igraph_found and self.help == 'test')):

                gr = IGraphRepr(outgraph)

                # Graph unique if the following are equal: edges
                key_parts = [gr.edges]

            # Stylistic stuff: Color nodes, edges, bold startpages
            if self.colorby:
                outgraph = self.color_nodes(outgraph)
            if self.shapeby:
                outgraph, warn = self.shape_nodes(outgraph)
                if warn:
                    warnings.append(warn)
            outgraph = self.color_edges(outgraph)
            outgraph = self.edge_tooltips(outgraph)
            outgraph = self.circle_start_nodes(outgraph)

            # Fix URL:s
            outgraph = self.fix_node_urls(outgraph)

            # Graph unique if the following are equal: content, layout
            # format, images, ordering
            key_parts = [outgraph, self.graphengine, 
                         self.shapefiles, self.orderby]

            # Generate cache key
            self.cache_key = cache_key(self.request, key_parts)

            outgraph.name = "%s-%s" % (self.cache_key, 
                                       encode_page(self.format))

            if (self.format == 'igraph' or 
                (igraph_found and self.help == 'test')):
                pass
            else:
                # Do the layout
                gr = self.generate_layout(outgraph)

        if self.format not in self.nonwrapped_formats and not self.inline:
            for reason in warnings:
                self.request.write(_sysmsg % ('warning', reason))
            self.send_form()

        if self.help == 'inline':
            urladd = self.request.page.page_name + \
                     self.urladd.replace('&inline=Inline', '')
            self.request.write('&lt;&lt;InlineGraph(%s)&gt;&gt;' % urladd)

        elif self.format == 'igraph' and not self.help:
            self.test_graph(gr, outgraph)
            self.send_graph(gr)

        elif self.format == 'kml' and not self.help:
            self.send_kml(outgraph)

        elif self.format in self.available_formats:
            if not gv_found:
                self.request.write(formatter.text(_(\
                    "ERROR: Graphviz Python extensions not installed. " +\
                    "Not performing layout.")))

            # XXX sometimes gr is not bound here -> crash on reference

            if self.format == 'dot':
                self.send_gv(gr)
            else:
                if self.legend == 'top':
                    self.send_legend()
                    self.send_graph(gr.graphviz)
                else:
                    self.send_graph(gr.graphviz)
                    self.send_legend()
        else:
            self.test_graph(gr, outgraph)

        if not self.inline:
            self.send_footer(formatter)

    def test_graph(self, gr, outgraph):
        formatter = self.request.formatter
        self.request.write('<div class="graph-info">')
        if igraph_found:
            self.request.write(formatter.preformatted(1))
            self.request.write(gr.summary(verbosity=1))
            self.request.write(formatter.preformatted(0))
        else:
            _ = self.request.getText
            # Give some parameters about the graph, more could easily be added
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
            if nronodes == 0 or (nronodes-1 == 0):
                self.request.write('0')
            else:
                self.request.write(str(nroedges / (nronodes*nronodes-1)))
            self.request.write(formatter.paragraph(0))
        self.request.write('</div>')

def execute(pagename, request, **kw):
    graphshower = GraphShower(pagename, request, **kw)
    graphshower.execute()
