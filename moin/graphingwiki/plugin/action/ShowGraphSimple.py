# -*- coding: iso-8859-1 -*-
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
    
from ShowGraph import *

class GraphShowerSimple(GraphShower):
    def __init__(self, pagename, request, graphengine = "neato"):
        super(GraphShowerSimple, self).__init__(pagename, request,
                                                graphengine)
        # URL addition
        self.image = 0
        self.urladd = ''
        self.available_formats = ['png', 'svg', 'dot', 'zgr']
    
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

        if self.isstandard:
            self.request.write(formatter.text("No graph data available."))
            self.request.write(formatter.endContent())
            wikiutil.send_footer(self.request, self.pagename)
            return

        graphdata = self.buildGraphData()

        # The working with patterns goes a bit like this:
        # First, get a sequence, add it to outgraph
        # Then, match from outgraph, add graphviz attrs

        gr = self.get_graph()

        if self.format == 'dot':
            self.sendGv(gr)
            raise MoinMoinNoFooter
            return
        else:
            self.sendForm()

        img_url = self.request.getQualifiedURL() + \
                  self.request.request_uri + "&image="

        legend = None
        if self.coloredges or self.colornodes:
            legend = self.makeLegend()

        if self.format == 'zgr':
            print '<applet code="net.claribole.zgrviewer.ZGRApplet.class" ' +\
                  'archive="/zvtm.jar,/zgrviewer.jar"width="720" height="480">'+\
                  '<param name="type" ' +\
                  'value="application/x-java-applet;version=1.4" />' +\
                  '<param name="scriptable" value="false" />' +\
                  '<param name="width" value="720" />' +\
                  '<param name="height" value="480" />' +\
                  '<param name="svgURL" value="%s" />' % (img_url + "1") +\
                  '<param name="title" value="ZGRViewer - Applet" />'+\
                  '<param name="appletBackgroundColor" value="#DDD" />' +\
                  '<param name="graphBackgroundColor" value="#DDD" />' +\
                  '<param name="highlightColor" value="red" />' +\
                  ' </applet>'

        elif self.format == 'svg':
            print '<img src="%s" alt="graph">' % (img_url + "1")
            print
            if legend:
                print '<img src="%s" alt="legend">' % (img_url + "2")

        else:
            print '<img src="%s" alt="graph" usemap="#%s">' % \
                  (img_url + "1", gr.graphattrs['name'])
            print
            self.sendMap(gr.graphviz)
            if legend:
                print '<img src="%s" alt="legend" usemap="#%s">' % \
                      (img_url + "2", legend.name)
                self.sendMap(legend)

        self.sendFooter(formatter)

    def get_graph(self):
        # Init WikiNode-pattern
        WikiNode(request=self.request,
                 urladd=self.urladd,
                 startpages=self.startpages)

        # First, let's get do the desired traversal, get outgraph
        graphdata = self.buildGraphData()
        outgraph = self.buildOutGraph()

#        nodes = self.initTraverse()
        nodes = set(self.startpages)
        outgraph = self.doTraverse(graphdata, outgraph, nodes)

        # Stylistic stuff: Color nodes, edges, bold startpages
        if self.colorby:
            outgraph = self.colorNodes(outgraph)
        outgraph = self.colorEdges(outgraph)
        outgraph = self.circleStartNodes(outgraph)

        # Fix URL:s
        outgraph = self.fixNodeUrls(outgraph)

        # Do the layout
        gr = self.generateLayout(outgraph)

        return gr

    def execute_image(self):
        formatcontent = self.format
        
        if self.format in ['zgr', 'svg']:
            self.format = 'svg'
            format_content = 'svg+xml'

        print "Content-type: image/%s\n" % formatcontent

        if self.image == 1:
            gr = self.get_graph()
            self.sendGraph(gr)
            raise MoinMoinNoFooter
        else:
            gr = self.get_graph()
            self.sendLegend()
            raise MoinMoinNoFooter

    def execute(self):        
        self.formargs()

        # Whether to do print the page frame or the image
        if self.request.form.has_key('image'):
            self.image = int(''.join(self.request.form['image']))

        if self.image:
            self.execute_image()
        else:
            self.execute_page()

def execute(pagename, request):
    graphshower = GraphShowerSimple(pagename, request)
    graphshower.execute()
