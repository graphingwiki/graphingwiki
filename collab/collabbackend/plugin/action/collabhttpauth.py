# -*- coding: utf-8 -*-"
"""
    @copyright: 2009-2010 by Marko Laakso <fenris@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

from MoinMoin.Page import Page

def execute(pagename, request):
    _ = request.getText

    request.page = Page(request, 'ForgottenPassword')
    request.setHttpHeader('WWW-Authenticate: Basic realm="Password Required (cancel for help)"')
    request.setHttpHeader('Status: 401 Authorization required"')
    request.setHttpHeader("Content-Type: %s; charset=%s" % (request.page.output_mimetype, request.page.output_charset))
    request.emit_http_headers()
    request.page.send_page(emit_headers=0)
