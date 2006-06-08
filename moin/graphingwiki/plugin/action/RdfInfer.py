# -*- coding: iso-8859-1 -*-
"""
    RdfInfer action to MoinMoin
     - Does inference based on the semantic data on pages

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
from urllib import quote as url_quote
from savegraphdata import encode

import os

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.formatter.text_html import Formatter 
from MoinMoin.Page import Page

from euler import run_called as run_inference
from MoinMoin.util import MoinMoinNoFooter
from unifier import Unifier

def execute(pagename, request):
    request.http_headers(["Content-type: text/plain;charset=%s" %
                          config.charset])

    infer = Unifier(request)
    for x in infer.solve_term(infer.instantiate_terms(
        ['FrontPage', 'Propertyyear', '?x'])):
        print x

    print "Trying out the rest"
    
    for x in infer.solve_term(infer.instantiate_terms(
        ['?y', 'Propertyyear', '?z'])):
        print x

#['FrontPage', 'Propertyyear', '1234']

    raise MoinMoinNoFooter

def execute_old(pagename, request):
    request.http_headers()

    # This action generate data using the user language
    request.setContentLanguage(request.lang)

    wikiutil.send_title(request, request.getText('Inference'),
                        pagename=pagename)

    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    formatter = Formatter(request)
    request.write(formatter.startContent("content"))

    infer = ''
    if request.form.has_key('infer'):
        infer = ''.join(request.form['infer'])

    request.write(u'<form method="GET" action="%s">\n' % pagename)
    request.write(u'<input type=hidden name=action value="%s">' %
                  ''.join(request.form['action']))

    request.write(u'<textarea name="infer" rows=10 cols=80>%s</textarea>' %
                  infer)
    request.write(u'<input type=submit value="Submit!">\n</form>\n')

    if infer:
        pageobj = Page(request, pagename)
        pagedir = pageobj.getPagePath()

        rdfdump = wikiutil.importPlugin(request.cfg, 'action',
                                        'N3Dump', 'n3dump')

        n3data = rdfdump(request, [pagename])

#         request.write(formatter.preformatted(1))
#         request.write(n3data + infer)
#         request.write(formatter.preformatted(0))

        data = run_inference(n3data + infer)
        request.write(formatter.preformatted(1))
        request.write(data)
        request.write(formatter.preformatted(0))
        
#     args = [x for x in request.form if x != 'action']
#     if args:
#         request.write(formatter.preformatted(1))
#         for arg in args:
#             request.write(arg)
#             for val in request.form[arg]:
#                 request.write(" " + val)
#             request.write("\n")
#         request.write(formatter.preformatted(0))

    # End content
    request.write(formatter.endContent()) # end content div
    # Footer
    wikiutil.send_footer(request, pagename)
