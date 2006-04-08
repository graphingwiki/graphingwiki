from MoinMoin import config

from ShowGraph import *

header = """Content-type: message/rfc822

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

end = "\n--partboundary--\n\n"

class GraphShowerIE(GraphShower):

    def __init__(self, pagename, request, graphengine = "neato"):
        super(GraphShowerIE, self).__init__(pagename, request, graphengine)
        self.parts = []
        self.format = 'gif'

    def sendGraph(self, gr, map=False):
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

    def sendLegend(self):
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

    def sendParts(self):
        for part in self.parts:
            self.request.write(add_mime_part(*part))        

    def sendHeaders(self):
        request = self.request
        pagename = self.pagename

        if self.format != 'dot':
            request.write(header)

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

    def sendFooter(self, formatter):
        if self.format != 'dot':
            # End content
            self.request.write(formatter.endContent()) # end content div
            # Footer
            wikiutil.send_footer(self.request, self.pagename)
            self.request.write('</body></html>')
            self.sendParts()
            self.request.write(end)

        raise MoinMoinNoFooter

def execute(pagename, request):
    graphshower = GraphShowerIE(pagename, request)
    graphshower.execute()
