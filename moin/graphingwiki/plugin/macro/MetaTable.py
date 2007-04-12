# -*- coding: iso-8859-1 -*-
"""
    MetaTable macro plugin to MoinMoin/Graphingwiki
     - Shows in tabular form the Metadata of desired pages

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
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
import re

from urllib import quote as url_quote
from urllib import unquote as url_unquote
from codecs import getencoder

from MoinMoin import config
from MoinMoin import Page

from graphingwiki.patterns import GraphData
from graphingwiki.patterns import encode

Dependencies = ['metadata']

regexp_re = re.compile('^/.+/$')

def t_cell(macro, data, head=0):
    if head:
        out = macro.formatter.table_cell(1, {'class': 'meta_page'})
    else:
        out = macro.formatter.table_cell(1, {'class': 'meta_cell'})
    data = url_unquote(data)
    if not isinstance(data, unicode):
        data = unicode(data, config.charset)

    if head:
        out = out + macro.formatter.pagelink(1, data)
    
    out = out + macro.formatter.text(data)

    if head:
        out = out + macro.formatter.pagelink(0)

    return out
    
def execute(macro, args):
    all_pages = []

    arglist = []

    # Regex preprocessing
    for arg in (x.strip() for x in args.split(',')):
        # Normal pages, just move on
        if not regexp_re.match(arg):
            arglist.append(arg)
            continue

        # load pagelist only if necessary
        if not all_pages:
            all_pages = macro.request.page.getPageList()

        # if there's something wrong with the regexp, ignore it and move on
        try:
            page_re = re.compile("%s" % arg[1:-1])
        except:
            continue
        # Check which pages match to the supplied regexp
        for page in all_pages:
            if page_re.match(page):
                arglist.append(url_quote(encode(page)))

    globaldata = GraphData(macro.request).globaldata

    pages = set([])
    metakeys = set([])
    limitregexps = {}

    for arg in arglist:
        if arg.startswith('Category'):
            if not globaldata['in'].has_key(arg):
                # no such category
                continue
            for newpage in globaldata['in'][arg]:
                if not (newpage.endswith('Template') or
                        newpage.startswith('Category')):
                    pages.add(newpage)
        elif '=' in arg:
            data = arg.split("=")
            key = data[0]
            val = '='.join(data[1:])
            # If val starts and ends with /
            if val[::len(val)-1] == '//':
                val = val[1:-1]
            limitregexps.setdefault(key, set()).add(re.compile(val))
        else:
            pages.add(arg)

    pagelist = set([])

    for page in pages:
        clear = True
        # Filter by regexps (if any)
        if limitregexps:
            for key in limitregexps:
                if not clear:
                    break

                data = ', '.join(globaldata['meta'].get(page, {}).get(key, ""))

                # If page does not have the required key, do not add page
                if not data:
                    clear = False
                    break

                # If the found key does not match, do not add page
                for re_limit in limitregexps[key]:
                    if not re_limit.search(data):
                        clear = False
                        break

        # Add page if all the regexps have matched
        if clear:
            pagelist.add(page)

    out = '\n' + macro.formatter.table(1)
    for page in pagelist:
        for key in globaldata['meta'].get(page, {}).keys():
            metakeys.add(key)

    metakeys = sorted(metakeys, key=str.lower)
    # Give a class to headers to make it customisable
    out = out + macro.formatter.table_row(1, {'rowclass': 'meta_header'})
    out = out + t_cell(macro, '')
    for key in metakeys:
        out = out + t_cell(macro, key)
    out = out + macro.formatter.table_row(0)

    pagelist = sorted(pagelist)

    for page in pagelist:
        out = out + macro.formatter.table_row(1)
        out = out + t_cell(macro, page, head=1)
        for key in metakeys:
            data = ', '.join(globaldata['meta'].get(page, {}).get(key, ""))
            out = out + t_cell(macro, data)
            
        out = out + macro.formatter.table_row(0)

    out = out + macro.formatter.table(0)

    return out

#         keyhits = set([])
#         keys = set([])
#         for key in keys_on_pages:
#             if q:
#                 if key == url_quote(encode(q)):
#                     keyhits.update(keys_on_pages[key])
#                     keys.add(unicode(url_unquote(key), config.charset))
#             else:
#                 if page_re.match(unicode(url_unquote(key), config.charset)):
#                     keyhits.update(keys_on_pages[key])
#                     keys.add(unicode(url_unquote(key), config.charset))

#         valhits = set([])
#         vals = set([])
#         for val in vals_on_pages:
#             if q:
#                 if val == encode(q):
#                     valhits.update(vals_on_pages[val])
#                     vals.add(unicode(val, config.charset))
#             else:
#                 if page_re.match(unicode(val, config.charset)):
#                     valhits.update(vals_on_pages[val])
#                     vals.add(unicode(val, config.charset))
