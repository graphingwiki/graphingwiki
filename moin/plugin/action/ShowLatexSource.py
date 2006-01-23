# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - ShowTexSource action, shows page with LaTeX markup

    @copyright: 2005 by Juhani Eronen <exec@ee.oulu.fi>
    @license: GNU GPL, see COPYING for details.
"""
    
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin import config
from MoinMoin.util import MoinMoinNoFooter

def execute(pagename, request):
    # _ = request.getText
    request.http_headers(["Content-type: text/plain;charset=%s" %
                          config.charset])

    try:
        # try to load the formatter
        Formatter = wikiutil.importPlugin(request.cfg, 'formatter',
                                          'application_x_tex', "Formatter")
        if Formatter is None:
            raise "Plugin not found!"
        formatter = Formatter(request)
        # The proper exception classes seem to exist in documentation only
        #                raise wikiutil.PluginMissingError
        #         except wikiutil.PluginMissingError:
        #             request.write(formatter.text("Plugin not found"))
        #             urlformatter = formatter
        #         except wikiutil.PluginAttributeError:
        #             request.write(formatter.text(
        #                           "Something wrong with plugin"))
        #             urlformatter = formatter
    except:
        # default to plain 
        import sys
        del Formatter
        from MoinMoin.formatter.text_plain import Formatter
        formatter = Formatter(request)
        request.write(formatter.text("What error??" + str(sys.exc_info()[0])))

    Page(request, pagename, formatter=formatter).send_page(request)

    # Write args to end, reminder/debug
    args = filter(lambda x: x != 'action', request.form.keys())
    if args:
        request.write(formatter.preformatted(1))
        for arg in args:
            request.write(arg)
            for val in request.form[arg]:
                request.write(" " + val)
        request.write(formatter.preformatted(0))

    raise MoinMoinNoFooter
