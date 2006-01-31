# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - ShowGraph action

    @copyright: 2005 by Juhani Eronen <exec@ee.oulu.fi>
    @license: GNU GPL, see COPYING for details.
"""
    
import os, cPickle, tempfile

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.formatter.text_html import Formatter 
from MoinMoin.parser.wiki import Parser

# cpe imports
import graph
import graphrepr

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

    try:
        gf = file(gfn)
        graphdata = cPickle.load(gf)
        gr = graphrepr.GraphRepr(graphdata)

        # Set proto attributes before the data is loaded, because
        # currently proto attributes affect only items added after
        # adding the proto!
        gr.dot.set(proto='edge', len='3')
        graphdata.commit()

        from base64 import b64encode

        tmp_fileno, tmp_name = tempfile.mkstemp()
        gr.dot.engine = 'neato'
        gr.dot.format = 'png'
        gr.dot.write(file=tmp_name)
        f = file(tmp_name)
        img = f.read()

        gr.dot.format = 'cmapx'
        gr.dot.write(file=tmp_name)
        f = file(tmp_name)
        mappi = f.read()

        imgbase = "data:image/png;base64," + b64encode(img)

        page = ('<img src="' + imgbase +
                '" alt="visualisation" usemap="#' +
                gr.graphattrs['name'] + '">\n' + mappi + "\n")

        request.write(page)

        request.write(formatter.preformatted(1))
        request.write(formatter.text(mappi))
        request.write(formatter.preformatted(0))

        # Tähäns nyt sitten eri linktypet eri väreillä ja legend

        # debug:
        # just to get the graph data out 
        gr.dot.format = 'dot'
        gr.dot.write(file=tmp_name)
        f = file(tmp_name)
        gtext = f.read()
        os.close(tmp_fileno)
        
        request.write(formatter.preformatted(1))
        request.write(formatter.text(gtext))
        request.write(formatter.preformatted(0))

        # args = filter(lambda x: x != 'action', request.form.keys())
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
