# -*- coding: utf-8 -*-"
"""
    LinkedIn macro plugin to MoinMoin/Graphingwiki
     - Shows pages in which the current page has been linked in

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
from urllib import unquote as url_unquote
from codecs import getencoder

from MoinMoin import config
from MoinMoin.logfile import editlog
from MoinMoin.Page import Page
from MoinMoin.wikiutil import importPlugin,  PluginMissingError

from graphingwiki.patterns import encode, GraphData
from graphingwiki.editing import getkeys

from MetaTable import construct_table

Dependencies = ['metadata']

def execute(macro, args):
    request = macro.request
    _ = macro.request.getText

    # save to graph file, if plugin available
    parse_text = importPlugin(request.cfg,
                              'action',
                              'savegraphdata',
                              'parse_text')
    
    alldata = dict()
    revisions = dict()

    if args:
        pagename = args
        page = Page(request, args)
    else:
        pagename = macro.formatter.page.page_name
        page = request.page

    quotedname = url_quote(encode(pagename))

    for rev in page.getRevList():
        revpage = Page(request, pagename, rev=rev)
        text = revpage.get_raw_body()
        alldata, pagegraph = parse_text(request, alldata, revpage, text)
        revlink = '%s?action=recall&rev=%d' % (encode(pagename), rev)
        alldata[revlink] = alldata[quotedname]
        # So that new values are appended rather than overwritten
        del alldata[quotedname]
        alldata[revlink]['meta']['#rev'] = [str(rev)]
        revisions[rev] = revlink

    class GraphData(object):
        def __init__(self, globaldata):
            self.globaldata = globaldata

        def getpage(self, pagename):
            return self.globaldata.get(pagename, {})

    globaldata = GraphData(alldata)

    pagelist = [revisions[x] for x in sorted(revisions.keys(), reverse=True)]

    metakeys = set()
    for page in pagelist:
        for key in getkeys(globaldata, page):
            metakeys.add(key)
    metakeys = sorted(metakeys, key=str.lower)

    return construct_table(macro, globaldata, pagelist,
                           metakeys, 'Meta by Revision')
