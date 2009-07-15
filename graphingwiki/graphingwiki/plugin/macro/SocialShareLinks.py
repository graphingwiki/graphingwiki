# -*- coding: iso-8859-1 -*-
"""
    @copyright: 2009 by Jani Kenttala <jansku@gmail.com> 
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

import StringIO, string
from MoinMoin import wikiutil

def formatSharelinks(formatter,url):
    result = ''
    linklist = {}
    linklist['[Twitter]'] = "http://twitthis.com/twit?url=%s" % ( url )
    linklist['[Facebook]'] = "http://www.facebook.com/share.php?u=%s" % (url )

    divfmt = {'class': 'SocialShareLinks'}
    result = formatter.div(1, **divfmt)

    result += formatter.text('Share at: ')

    for (site, shareulr) in linklist.iteritems():
        result += formatter.url(1, shareulr, style="SocialShareLink", target="_blank")
        result += formatter.text(site+ " ")
        result += formatter.url(0)

    result += formatter.div(0)
    return result

def execute(macro, args):

    url = wikiutil.escape(macro.request.getQualifiedURL())
    return formatSharelinks(macro.formatter, url)
