# -*- coding: iso-8859-1 -*-
"""
    ViewDot action for Graphingwiki
     - Shows dot files as png images, as svg images or with the ZGR applet

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
import os
from tempfile import mkstemp
from base64 import b64encode
from urllib import quote as url_quote

from MoinMoin import wikiutil
from MoinMoin.formatter.text_html import Formatter as HtmlFormatter
from MoinMoin.action import AttachFile
from MoinMoin.request import RequestModPy
from MoinMoin.util import MoinMoinNoFooter

from graphingwiki.graphrepr import Graphviz

from ShowGraph import quotetoshow
from savegraphdata import encode

class ViewDot(object):
    def __init__(self, pagename, request, **kw):
        self.request = request
        self.pagename = pagename

        self.available_formats = ['png', 'svg', 'zgr']
        self.format = 'png'

        self.available_graphengines = ['dot', 'neato']
        self.graphengine = kw['graphengine']

        self.dotfile = ""
        self.attachment = ""
        
        self.inline = True
        self.help = False

        self.height = ""
        self.width = ""
        for key in kw:
            if key == 'height':
                self.height = kw['height']
            elif key == 'width':
                self.width = kw['width']

    def formargs(self):
        request = self.request

        # format
        if request.form.has_key('format'):
            format = [encode(x) for x in request.form['format']][0]
            if format in self.available_formats:
                self.format = format

        # format
        if request.form.has_key('view'):
            if ''.join([x for x in request.form['view']]).strip():
                self.inline = False

        # format
        if request.form.has_key('help'):
            if ''.join([x for x in request.form['help']]).strip():
                self.help = True

        # graphengine
        if request.form.has_key('graphengine'):
            graphengine = [encode(x) for x in request.form['graphengine']][0]
            if graphengine in self.available_graphengines:
                self.graphengine = graphengine

        # format
        if request.form.has_key('attachment'):
            self.attachment = ''.join([x for x in request.form['attachment']])

    def sendForm(self):
        request = self.request

        # Form fix for subpages
        pagename = '../' * self.pagename.count('/') + self.pagename

        ## Begin form
        request.write(u'<form method="GET" action="%s">\n' %
                      pagename)
        request.write(u'<input type=hidden name=action value="ViewDot">')

        request.write(u"<table>\n<tr>\n")

        # format
        request.write(u"<td>\nOutput format:<br>\n")
        for type in self.available_formats:
            request.write(u'<input type="radio" name="format" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.format and " checked>" or ">",
                           type))

        # graphengine
        request.write(u"<td>\nOutput graphengine:<br>\n")
        for type in self.available_graphengines:
            request.write(u'<input type="radio" name="graphengine" ' +
                          u'value="%s"%s%s<br>\n' %
                          (type,
                           type == self.graphengine and " checked>" or ">",
                           type))

        # dotfile
        dotfile = self.dotfile
        request.write(u"Dot file:<br>\n" +
                      u'<select name="attachment">\n')
        for page in self.request.page.getPageList():
            files = AttachFile._get_files(self.request, page)
            for file in files:
                if file.endswith('.dot'):
                    request.write('<option label="%s" value="%s">%s</option>\n' % \
                                  (file, "attachment:%s/%s" % (page, file),
                                   "%s/%s" % (page, file)))
        request.write('</select>\n</table>\n')
        request.write(u'<input type=submit name=view ' +
                      'value="View">\n')
        request.write(u'<input type=submit name=help ' +
                      'value="Inline"><br>\n')
        request.write(u'</form>\n')

    def fail(self):
        self.request.write('Content-type: text/plain\n\n')
        raise MoinMoinNoFooter

    def execute(self):
        self.formargs()
        request = self.request

        if self.help or not self.attachment:
            # fix for moin 1.3.5
            if not hasattr(request, 'formatter'):
                formatter = HtmlFormatter(request)
            else:
                formatter = request.formatter

            request.http_headers()
            # This action generate data using the user language
            request.setContentLanguage(request.lang)

            title = request.getText('View .dot attachment')

            # Start content - IMPORTANT - without content div, there is no
            # direction support!
            request.write(formatter.startContent("content"))
            formatter.setPage(request.page)

            wikiutil.send_title(request, title, pagename=self.pagename)

            self.sendForm()

            if self.help:
                # This is the URL addition to the nodes that have graph data
                self.urladd = '?'
                for key in request.form:
                    if key == 'help':
                        continue
                    for val in request.form[key]:
                        self.urladd = (self.urladd + url_quote(encode(key)) +
                                       '=' + url_quote(encode(val)) + '&')
                self.urladd = self.urladd[:-1]
                request.write('[[ViewDot(' + \
                              self.request.page.page_name + \
                              self.urladd + ')]]')

            # End content
            self.request.write(formatter.endContent()) # end content div
            # Footer
            wikiutil.send_footer(request, self.pagename)
            return 

        if not self.attachment[:10].lower() == 'attachment':
            self.fail()
        self.attachment = self.attachment[11:]
        pagename, filename = AttachFile.absoluteName(self.attachment,
                                                     self.pagename)
        fname = wikiutil.taintfilename(filename)
        fpath = AttachFile.getFilename(request, pagename, fname)

        try:
            data = file(fpath, 'r').read()
        except IOError:
            self.fail()

        graphviz = Graphviz(engine=self.graphengine, string=data)
        data = self.getLayoutInFormat(graphviz, self.format)

        if self.format in ['zgr', 'svg']:
            formatcontent = 'svg+xml'
        else:
            formatcontent = self.format

        if not self.inline:
            if self.format == 'zgr':
                request.http_headers()
                request.write('<html><body>')
            elif isinstance(self.request, RequestModPy):
                request.setHttpHeader('Content-type: image/%s' %
                                           formatcontent)
                del request.mpyreq.headers_out['Vary']
            else:
                request.write("Content-type: image/%s\n\n" % formatcontent)

        if self.format == 'zgr':
            img_url = request.request_uri.replace('zgr', 'svg') + '&view=View'
            img_url = self.request.getQualifiedURL(img_url)
                      
            if not self.height:
                self.height = "600"
            if not self.width:
                self.width = "100%"

            request.write(
                '<applet code="net.claribole.zgrviewer.ZGRApplet.class" ' +\
                'archive="%s/zvtm.jar,%s/zgrviewer.jar" ' % \
                (self.request.cfg.url_prefix, self.request.cfg.url_prefix)+\
                'width="%s" height="%s">' % (self.width, self.height)+\
                '<param name="type" ' +\
                'value="application/x-java-applet;version=1.4" />' +\
                '<param name="scriptable" value="false" />' +\
                '<param name="svgURL" value="%s" />' % img_url +\
                '<param name="title" value="ZGRViewer - Applet" />'+\
                '<param name="appletBackgroundColor" value="#DDD" />' +\
                '<param name="graphBackgroundColor" value="#DDD" />' +\
                '<param name="highlightColor" value="red" />' +\
                ' </applet><br>\n')
        elif self.inline:
            imgbase = "data:image/" + self.format + ";base64," + \
                      b64encode(data)
            params = ""
            if self.height:
                params += 'height="%s" ' % self.height
            if self.width:
                params += 'width="%s"' % self.width

            page = ('<img src="' + imgbase +
                    '" %s alt="visualisation"><br>\n' % params)
            request.write(page)
        else:
            request.write(data)

        if not self.inline and self.format == 'zgr':
            request.write('</html></body>')
        elif self.inline:
            return
        else:
            raise MoinMoinNoFooter

    def getLayoutInFormat(self, graphviz, format):
        tmp_fileno, tmp_name = mkstemp()
        graphviz.layout(file=tmp_name, format=format)
        f = file(tmp_name)
        data = f.read()
        os.close(tmp_fileno)
        os.remove(tmp_name)

        return data

def execute(pagename, request, **kw):
    if not kw.has_key('graphengine'):
        kw['graphengine'] = 'neato'
    viewdot = ViewDot(pagename, request, **kw)
    viewdot.execute()
