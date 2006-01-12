# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - ShowGraph action

    @copyright: 2005 by Juhani Eronen <exec@ee.oulu.fi>
    @license: GNU GPL, see COPYING for details.
"""
    
import os, errno, codecs, sys, re
from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.formatter.text_html import Formatter 
from MoinMoin.parser.wiki import Parser

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
        gf = codecs.open(gfn, 'rb', config.charset)
        # gf = open(gfn)
        request.write(formatter.preformatted(1))

        data = gf.read()
        gf.close()
        
        try:
            urler = wikiutil.importPlugin(request.cfg, 'formatter', 'text_url', "Formatter")
            urlformatter = urler(request)

            if urlformatter is None:
                raise wikiutil.PluginMissingError

# those do not exist?!?
#         except wikiutil.PluginMissingError:
#             request.write(formatter.text("Plugin not found"))
#             urlformatter = formatter
#         except wikiutil.PluginAttributeError:
#             request.write(formatter.text("Something wrong with plugin"))
#             urlformatter = formatter
        except:
            request.write(formatter.text("What error??" + str(sys.exc_info()[0])))
            urlformatter = formatter

        urlparser = Parser(data, request)
        urlparser.formatter = urlformatter
        urlformatter.setPage(pageobj)

        dotdata = "digraph G {\n"
        # skip empty after last line break
        lines = data.split('\n')[:-1]

        # placeholder for links
        links = []

        for line, i in zip(lines, range(len(lines))):
            items = line.split(' ')
            # link type
            type = items[0]
            # strip the link type info
            value = ' '.join(items[1:])

            # get the function doing the link handling in formatter
            replace = getattr(urlparser, '_' + type + '_repl')
            attrs = replace(value)

            # Grab the link from attrs
            link = re.search(r'((?:(?:[^"])|(?:\\"))+?(?<!\\))"',
                             attrs).group(1)

            # if the link is unique, add to graph
            if link not in links:
                links.append(link)
                dotdata = (dotdata + '  ' + str(i) + " [" +
                           'URL=' + attrs + "]\n")
                dotdata = dotdata + '  ' + pagename + ' -> ' + str(i) + "\n"

        dotdata = dotdata + "}"

        request.write(formatter.text(dotdata))

        request.write(formatter.preformatted(0))

        from base64 import b64encode

        w,r = os.popen2("neato -Elen=3 -T cmap")
        w.write(dotdata)
        w.close()
        mappi = r.read()
        r.close()
        
        w,r = os.popen2("neato -Elen=3 -T png")
        w.write(dotdata)
        w.close()
        img = r.read()
        r.close()

        imgbase = "data:image/png;base64," + b64encode(img)

        page = ('<img border=0 src="' + imgbase +
                '" alt="visualisation" usemap="#G">' + "\n" +
                '<map id="G" name="G">' + mappi + '</map>')
             
        request.write(page)

        args = filter(lambda x: x != 'action', request.form.keys())
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
