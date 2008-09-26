# -*- coding: utf-8 -*-"
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

import os
import re
from savegraphdata import encode

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.util import MoinMoinNoFooter
from MoinMoin.formatter.text_html import Formatter as HtmlFormatter

from graphingwiki.patterns import actionname, form_escape

from unifier import Unifier

# The necessary regexps
fact = ur'\s*([a-zA-Z_0-9\:\%\?]+)\s+' + \
       ur'([a-zA-Z_0-9\:\%\?]+)\s+([a-zA-Z_0-9\:\%\?]+)\s*\.'
lfact = ur'\s*([a-zA-Z_0-9\:\%\?]+)\s+' + \
        ur'([a-zA-Z_0-9\:\%\?]+)\s+([a-zA-Z_0-9\:\%\?]+)\s*\.?'

query = ur'\s*{' + lfact + ur'}\s*->\s*\[\]\s*\.\s*'
rule = ur'\s*{' + fact + "+" + lfact + ur'}\s*->\s*{' + lfact + ur'}\s*\.\s*'

def execute(pagename, request):
    request.http_headers()

    # This action generate data using the user language
    request.setContentLanguage(request.lang)

    wikiutil.send_title(request, request.getText('Inference'),
                        pagename=pagename)

    # fix for moin 1.3.5
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter

    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    request.write(formatter.startContent("content"))

    infer = ''
    if request.form.has_key('infer'):
        infer = ''.join(request.form['infer'])

    request.write(u'<form method="GET" action="%s">\n' %
                  actionname(request, pagename))
    request.write(u'<input type=hidden name=action value="%s">' %
                  ''.join(request.form['action']))

    request.write(u'<input type="text" name="infer" size=50 value="%s">' %
                  form_escape(infer))
    request.write(u'<input type=submit value="Infer from these pages">' + \
                  u'\n</form>\n')

    if infer:
        # Compile regexps
        fact_re = re.compile(fact)
        query_re = re.compile(query)
        rule_re = re.compile(rule)

        engine = Unifier(request)

        # grab data
        data = ""
        for name in infer.split(','):
            page = Page(request, name.strip())
            data = data + encode(page.get_raw_body())

        request.write(formatter.preformatted(1))

        # Start to handle data rows
        for line in data.split('\n'):
            line.strip()
            if not line.endswith('.'):
                continue
            elif '[]' in line:
                q = query_re.match(line)
                if q:
                    answers = set()
                    for heureka in engine.solve(list(q.groups())):
                        answers.add(' '.join(heureka[0]) + ".")
                    for once in answers:
                        request.write(form_escape(once))
            elif '->' in line:
                r = rule_re.match(line)
                if r:
                    rules = r.groups()
                    last = ['fact', list(rules[-3:])]
                    rules = rules[:-3]
                    while rules:
                        last.append(list(rules[:3]))
                        rules = rules[3:]
                    engine.add_rule(last)
            else:
                # normal fact
                ma = fact_re.search(line)
                if not ma:
                    continue
                engine.add_rule(['fact', list(ma.groups())])

        request.write(formatter.preformatted(0))

    # End content
    request.write(formatter.endContent()) # end content div
    # Footer
    wikiutil.send_footer(request, pagename)
