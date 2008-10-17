# -*- coding: utf-8 -*-"
"""
    ShowGraphSimple action plugin to MoinMoin
     - Simple and slow version of ShowGraph for enhanced compatibility

    @copyright: 2005 by Juhani Eronen <exec@iki.fi>
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

from urllib import quote as url_quote

from MoinMoin.wikiutil import unquoteWikiname
from MoinMoin.request.request_modpython import Request as RequestModPy
from MoinMoin.request.request_standalone import Request as RequestStandAlone
from MoinMoin.action import AttachFile

from graphingwiki.graphrepr import gv_found
from ShowGraph import *

class GraphShowerSimple(GraphShower):
    def __init__(self, pagename, request, **kw):
        if not kw.has_key('graphengine'):
            self.graphengine = 'neato'
        else:
            self.graphengine = kw['graphengine']

        super(GraphShowerSimple, self).__init__(pagename, request,
                                                self.graphengine)
        # URL addition
        self.image = 0
        self.urladd = ''
        self.available_formats = ['png', 'svg', 'dot', 'zgr']
        self.do_form = kw['do_form']
    
    def sendGraph(self, gr):
        img = self.getLayoutInFormat(gr.graphviz, self.format)
        self.request.write(img)

    def sendLegend(self):
        legend = None
        if self.coloredges or self.colornodes:
            legend = self.makeLegend()

        if legend:
            img = self.getLayoutInFormat(legend, self.format)
            self.request.write(img)

    def execute_page(self):
        formatter = self.sendHeaders()
        _ = self.request.getText

        if self.isstandard:
            self.request.write(formatter.text(
                _("No graph data available.")))
            self.request.write(formatter.endContent())
            self.request.theme.send_footer(self.pagename)
            return

        self.execute_graphs()

        self.sendFooter(formatter)


    def execute_graphs(self, urladd=None):
        _ = self.request.getText
        if urladd:
            self.urladd = urladd

        # Init WikiNode-pattern
        self.globaldata = WikiNode(request=self.request,
                                   urladd=self.urladd,
                                   startpages=self.startpages).graphdata


        # The working with patterns goes a bit like this:
        # First, get a sequence, add it to outgraph
        # Then, match from outgraph, add graphviz attrs

        outgraph = self.get_graph()

        if self.format and gv_found:
            gr = self.generateLayout(outgraph)

        if self.do_form:
            if self.format == 'dot':
                self.sendGv(gr)
                # Cleanup
            else:
                self.sendForm()

        img_url = self.request.getQualifiedURL() + \
                  self.request.request_uri + "&image="

        legend = None
        if (self.coloredges or self.colornodes) and gv_found:
            legend = self.makeLegend()

        if self.help == 'inline':
            urladd = self.request.page.page_name + \
                     self.urladd.replace('&inline=Inline', '')
            urladd = urladd.replace('action=ShowGraph',
                                    'action=ShowGraphSimple')
            self.request.write('[[InlineGraph(%s)]]' % urladd)
        elif not self.format:
            formatter = self.request.formatter
            self.request.write(formatter.paragraph(1))
            self.request.write(formatter.text(_("Nodes in graph") + ": " +
                                                str(len(
                outgraph.nodes.getall()))))
            self.request.write(formatter.paragraph(0))
            self.request.write(formatter.paragraph(1))
            self.request.write(formatter.text(_("Edges in graph") + ": " +
                                              str(len(
                outgraph.edges.getall()))))
            self.request.write(formatter.paragraph(0))
            if getattr(self, 'orderby', '_hier') != '_hier':
                self.request.write(formatter.paragraph(1))
                self.request.write(formatter.text(_("Order levels") + ": " +
                                                  str(len(
                    self.ordernodes.keys()))))
                self.request.write(formatter.paragraph(0))
        elif not gv_found:
            self.request.write(self.request.formatter.text(_(\
                    "ERROR: Graphviz Python extensions not installed. " +\
                    "Not performing layout.")))
        elif self.format == 'zgr':
            if not self.height:
                self.height = "600"
            if not self.width:
                self.width = "100%"

            self.request.write(
                '<applet code="net.claribole.zgrviewer.ZGRApplet.class" ' +\
                'archive="%s/zvtm.jar,%s/zgrviewer.jar" ' % \
                (self.request.cfg.url_prefix, self.request.cfg.url_prefix)+\
                'width="%s" height="%s">' % (self.width, self.height)+\
                '<param name="type" ' +\
                'value="application/x-java-applet;version=1.4" />' +\
                '<param name="scriptable" value="false" />' +\
                '<param name="svgURL" value="%s" />' % (img_url + "1") +\
                '<param name="title" value="ZGRViewer - Applet" />'+\
                '<param name="appletBackgroundColor" value="#DDD" />' +\
                '<param name="graphBackgroundColor" value="#DDD" />' +\
                '<param name="highlightColor" value="red" />' +\
                ' </applet><br>\n')

            img_url = img_url.replace('&format=zgr', '&format=png')
            if legend:
                self.request.write('<img src="%s" alt="legend"><br>\n' %
                                   (img_url + "2"))
        elif self.format == 'svg':
            self.request.write('<img src="%s" alt="graph">\n' %
                               (img_url + "1"))
            if legend:
                self.request.write('<img src="%s" alt="legend">' %
                                   (img_url + "2"))
        else:
            self.request.write('<img src="%s" alt="%s" usemap="#%s">\n'%
                               (img_url + "1", _('graph'),
                                gr.graphattrs['name']))
            self.sendMap(gr.graphviz)
            if legend:
                self.request.write('<img src="%s" alt="%s" usemap="#%s">'%
                                   (img_url + "2", _('legend'), legend.name))
                self.sendMap(legend)

    def get_graph(self):
        # First, let's get do the desired traversal, get outgraph
        graphdata = self.buildGraphData()
        # Stupid ugly hack:
        # after saving page, the code execution seems to
        # go pretty erratic, buildgraphdata is somehow
        # executed two times over (??), leaving the
        # db closed - hence opening the db again
        # here seems to do the trick?
        if not self.globaldata.opened:
            self.globaldata.opendb()
        outgraph = self.buildOutGraph()

        # Fixes some weird problems with transparency
        if self.format == 'svg':
            outgraph.bgcolor = 'white'

        nodes = set(self.startpages)
        outgraph = self.doTraverse(graphdata, outgraph, nodes)

        # Stylistic stuff: Color nodes, edges, bold startpages
        if self.colorby:
            outgraph = self.colorNodes(outgraph)
        outgraph = self.colorEdges(outgraph)
        outgraph = self.edgeTooltips(outgraph)
        outgraph = self.circleStartNodes(outgraph)

        # Fix URL:s
        outgraph = self.fixNodeUrls(outgraph)

        if self.format == 'zgr':
            self.origformat = True

        # To fix links with zgrviewer
        if hasattr(self, 'origformat'):
            src = self.request.getQualifiedURL() + '/'
            for node, in outgraph.nodes.getall():
                node = outgraph.nodes.get(node)

                # To fix some weird problems with transparency
                nstyle = getattr(node, 'gwikistyle', None)
                if not nstyle:
                    node.gwikistyle = 'filled'
                elif not 'filled' in nstyle:
                    node.gwikistyle += ', filled'
                if not hasattr(node, 'gwikifillcolor'):
                    node.gwikifillcolor = 'white'

                # Fix shapefile from file path to URL
                if hasattr(node, 'gwikishapefile'):
                    page, file = node.gwikishapefile.split('/attachments/')
                    page = unquoteWikiname(page.split('/')[-1])
                    shapefile = AttachFile.getAttachUrl(page, file,
                                                        self.request)
                    shapefile = self.request.getQualifiedURL(shapefile)
                    node.gwikishapefile = shapefile

                # Quoting fix
                if 'action=AttachFile' in node.gwikiURL:
                    pagepart, args = node.gwikiURL[1:].split('?')
                    node.gwikiURL = src + url_quote(pagepart) + '?' + args

                # Fix other node URL:s
                if node.gwikiURL.startswith('..'):
                    node.gwikiURL = src + node.gwikiURL[2:]
                elif node.gwikiURL[0] == '.':
                    node.gwikiURL = src + node.gwikiURL[1:]
                elif node.gwikiURL[0] == '/':
                    node.gwikiURL = src + node.gwikiURL
                node.gwikiURL = node.gwikiURL.replace('&image=1', '')

            src = self.request.getQualifiedURL()
            for edge in outgraph.edges.getall():
                edge = outgraph.edges.get(*edge)

                # Quoting fix
                tooltip = edge.tooltip.split('>')
                edge.tooltip = '>'.join(url_unquote(x) for x in tooltip)

                # Fix edge URL:s
                if edge.URL.startswith('..'):
                    edge.URL = src + edge.URL[2:]
                elif edge.URL[0] == '.':
                    edge.URL = src + edge.URL[1:]
                elif edge.URL[0] == '/':
                    edge.URL = src + edge.URL
                edge.URL = edge.URL.replace('&image=1', '')

        return outgraph

    def execute_image(self):
        if not gv_found:
            self.request.setHttpHeader('Content-type: text/plain')
            self.request.write(formatter.text(_(\
                        "ERROR: Graphviz Python extensions not installed. " +\
                        "Not performing layout.")))
        
        # Init WikiNode-pattern
        self.globaldata = WikiNode(request=self.request,
                                   urladd=self.urladd,
                                   startpages=self.startpages).graphdata

        formatcontent = self.format

        if self.format == 'zgr':
            self.origformat = True
        
        if self.format in ['zgr', 'svg']:
            self.format = 'svg'
            formatcontent = 'svg+xml'

        if isinstance(self.request, RequestModPy):
            self.request.setHttpHeader('Content-type: image/%s' % formatcontent)
            del self.request.mpyreq.headers_out['Vary']
        elif not isinstance(self.request, RequestStandAlone):
            # Do not send content type in StandAlone
            self.request.write("Content-type: image/%s\n\n" % formatcontent)

        if self.image == 1:
            outgraph = self.get_graph()
            gr = self.generateLayout(outgraph)
            self.sendGraph(gr)
            # Cleanup
        else:
            outgraph = self.get_graph()
            gr = self.generateLayout(outgraph)
            self.sendLegend()
            # Cleanup

    def execute(self):
        self.formargs()

        # Whether to do print the page frame or the image
        if self.request.form.has_key('image'):
            try:
                self.image = int(''.join(self.request.form['image']))
            except:
                self.image = 1

        if self.image:
            self.execute_image()
        else:
            self.execute_page()

def execute(pagename, request):
    # defaults
    kw = {'do_form': True, 'graphengine': 'neato'}
    graphshower = GraphShowerSimple(pagename, request, **kw)
    graphshower.execute()

def execute_graphs(pagename, request, **kw):
    # Default
    kw['do_form'] = False
    kw['graphengine'] = 'neato'
    urladd = kw['urladd']

    graphshower = GraphShowerSimple(pagename, request, **kw)
    graphshower.formargs()
    graphshower.execute_graphs(urladd=urladd)