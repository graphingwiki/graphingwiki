# -*- coding: utf-8 -*-"
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

from MoinMoin import wikiutil
from MoinMoin.action import AttachFile
from MoinMoin.action import cache

from graphingwiki import gv_found, actionname, values_to_form
from graphingwiki.graphrepr import Graphviz
from graphingwiki.util import enter_page, exit_page, url_parameters, \
    encode_page, cache_exists, cache_key, form_escape

class ViewDot(object):
    def __init__(self, pagename, request, **kw):
        self.request = request
        self.pagename = pagename

        self.available_formats = ['png', 'svg', 'zgr']
        self.format = 'png'

        self.available_graphengines = ['dot', 'neato']
        self.graphengine = kw['graphengine']

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

    def formargs(self, form):
        request = self.request

        # format
        if form.has_key('format'):
            format = form['format'][0]
            if format in self.available_formats:
                self.format = format

        if form.has_key('view'):
            if form['view'][0].strip():
                self.inline = False

        if form.has_key('help'):
            if form['help'][0].strip():
                self.help = True

        if form.has_key('graphengine'):
            graphengine = encode_page(form['graphengine'][0])
            if graphengine in self.available_graphengines:
                self.graphengine = graphengine

        if form.has_key('attachment'):
            self.attachment = form['attachment'][0]

    def sendForm(self):
        request = self.request
        _ = request.getText

        ## Begin form
        request.write(u'<form method="GET" action="%s">\n' %
                      actionname(request))
        request.write(u'<input type=hidden name=action value="ViewDot">')

        request.write(u"<table>\n<tr>\n")

        # format
        request.write(u"<td>\n" + _('Output format') + u"<br>\n")
        for type in self.available_formats:
            request.write(u'<input type="radio" name="format" ' +
                          u'value="%s"%s%s<br>\n' %
                          (form_escape(type),
                           type == self.format and " checked>" or ">",
                           wikiutil.escape(type)))

        # graphengine
        request.write(u"<td>\n" + _('Output graphengine') + u"<br>\n")
        for type in self.available_graphengines:
            request.write(u'<input type="radio" name="graphengine" ' +
                          u'value="%s"%s%s<br>\n' %
                          (form_escape(type),
                           type == self.graphengine and " checked>" or ">",
                           wikiutil.escape(type)))

        request.write(_("Dot file") + "<br>\n" +
                      u'<select name="attachment">\n')

        # Use request.rootpage, request.page has weird failure modes
        for page in request.rootpage.getPageList():
            files = AttachFile._get_files(request, page)
            for file in files:
                if file.endswith('.dot') or file.endswith('.gv'):
                    request.write('<option label="%s" value="%s">%s</option>\n'
                                  % (form_escape(file), form_escape("attachment:%s/%s" % (page, file)),
                                     wikiutil.escape("%s/%s" % (page, file))))
        request.write('</select>\n</table>\n')
        request.write(u'<input type=submit name=view ' +
                      'value="%s">\n' % form_escape(_('View')))
        request.write(u'<input type=submit name=help ' +
                      'value="%s"><br>\n' % form_escape(_('Inline')))
        request.write(u'</form>\n')

    def execute(self):
        request = self.request
        _ = request.getText
        pagename = request.page.page_name

        form = values_to_form(request.values)
        self.formargs(form)

        if self.help or not self.attachment:
            formatter = request.formatter

            enter_page(request, pagename, 'View .gv attachment')

            self.sendForm()

            if self.help:
                # This is the URL addition to the nodes that have graph data
                self.urladd = url_parameters(form)
                self.urladd = self.urladd.replace('&help=Inline', '')
                request.write('&lt;&lt;ViewDot(' + self.urladd + ')&gt;&gt;')

            exit_page(request, pagename)
            return

        if not self.attachment[:10].lower() == 'attachment':
            fault = _(u'No attachment defined') + u'\n'
            if self.inline:
                request.write(request.formatter.text(fault))
                return
            request.content_type = 'text/plain'
            request.write(fault)
            return

        self.attachment = self.attachment[11:]

        pagename, filename = AttachFile.absoluteName(self.attachment,
                                                     self.pagename)

        fname = wikiutil.taintfilename(filename)
        fpath = AttachFile.getFilename(request, pagename, fname)

        try:
            data = file(fpath, 'r').read()
        except IOError:
            fault = _(u'Attachment not found at') + u' %s\n' % repr(fpath)
            if self.inline:
                request.write(request.formatter.text(fault))
                return
            request.content_type = 'text/plain'
            request.write(fault)
            return

        if not gv_found:
            fault = _(u"ERROR: Graphviz Python extensions not installed. " +\
                      u"Not performing layout.")
            if self.inline:
                request.write(request.formatter.text(fault))
                return
            request.content_type = 'text/plain'
            request.write(fault)
            return

        self.cache_key = cache_key(self.request,
                                   [data, self.graphengine, self.format])
        key = "%s-%s" % (self.cache_key, self.format)

        if self.format in ['zgr', 'svg']:
            formatcontent = 'svg+xml'
        else:
            formatcontent = self.format

        if not cache_exists(request, key):
            graphviz = Graphviz(engine=self.graphengine, string=data)
            data = self.getLayoutInFormat(graphviz, self.format)

            cache.put(self.request, key, data, content_type=formatcontent)

        if self.format in ['zgr', 'svg']:
            # Display zgr graphs as applets
            if self.format == 'zgr':
                image_p = lambda url, text: \
                    '<applet code="net.claribole.zgrviewer.ZGRApplet.class"'+ \
                    ' archive="%s/gwikicommon/zgrviewer/zvtm.jar,' % \
                    (self.request.cfg.url_prefix_static) + \
                    '%s/gwikicommon/zgrviewer/zgrviewer.jar" ' % \
                    (self.request.cfg.url_prefix_static) + \
                    'width="%s" height="%s">' % (form_escape(self.width), form_escape(self.height))+\
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
                image_p = lambda url, text: \
                    '<object data="%s" alt="%s" ' % (url, text) + \
                    'type="image/svg+xml">\n' + \
                    '<embed src="%s" alt="%s" ' % (url, text) + \
                    'type="image/svg+xml"/>\n</object>'
        else:
            image_p = lambda url, text: \
                '<img src="%s" alt="%s">\n' % (url, text)

        image_uri = cache.url(self.request, key)

        if not self.inline:
            if self.format == 'zgr':
                request.write('<html><body>')

        request.write(image_p(image_uri, _('visualisation')))

        if not self.inline and self.format == 'zgr':
            request.write('</html></body>')
        else:
            pass # No footer

    def getLayoutInFormat(self, graphviz, format):
        tmp_fileno, tmp_name = mkstemp()
        graphviz.layout(fname=tmp_name, format=format)
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
