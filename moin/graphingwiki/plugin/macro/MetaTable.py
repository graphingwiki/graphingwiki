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
import string

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin import caching

from graphingwiki.patterns import GraphData, encode, nonguaranteeds_p, qstrip_p

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

def get_pages(macro):
    
    def filter(name):
        # aw crap, SystemPagesGroup is not a system page
        if name == 'SystemPagesGroup':
            return False
        return not wikiutil.isSystemPage(macro.request, name)
    # It seems to help avoiding problems that the query
    # is made by request.rootpage instead of request.page
    pages = set(url_quote(encode(x)) for x in
                macro.request.rootpage.getPageList(filter=filter))
    return pages
    
def execute(macro, args):
    # Category, Template matching regexps
    cat_re = re.compile(macro.request.cfg.page_category_regex)
    temp_re = re.compile(macro.request.cfg.page_template_regex)

    # Placeholder for list of all pages
    all_pages = []

    arglist = []
    keyspec = []

    # Flag: were there page arguments?
    pageargs = False

    # Regex preprocessing
    for arg in (x.strip() for x in args.split(',') if x.strip()):
        # Metadata regexp, move on
        if '=' in arg:
            arglist.append(arg)
            continue

        # key spec, move on
        if arg.startswith('||') and arg.endswith('||'):
            # take order, strip empty ones
            keyspec = [url_quote(encode(x)) for x in arg.split('||') if x]
            continue

        # Ok, we have a page arg, i.e. a page or page regexp in args
        pageargs = True

        # Normal pages, encode and move on
        if not regexp_re.match(arg):
            arglist.append(url_quote(encode(arg)))
            continue

        # Ok, it's a page regexp

        # if there's something wrong with the regexp, ignore it and move on
        try:
            page_re = re.compile("%s" % arg[1:-1])
        except:
            continue

        # Get all pages, check which of them match to the supplied regexp
        all_pages = get_pages(macro)
        for page in all_pages:
            if page_re.match(page):
                arglist.append(encode(page))

    globaldata = GraphData(macro.request)

    pages = set([])
    metakeys = set([])
    limitregexps = {}

    for arg in arglist:
        if cat_re.search(arg):
            # Nonexisting categories
            try:
                page = globaldata.getpage(arg)
            except KeyError:
                continue

            if not page.has_key('in'):
                # no such category
                continue
            for type in page['in']:
                for newpage in page['in'][type]:
                    if not (cat_re.search(newpage) or
                            temp_re.search(newpage)):
                        pages.add(encode(newpage))
        elif '=' in arg:
            data = arg.split("=")
            key = url_quote(encode(data[0]))
            val = encode('='.join(data[1:]))
            # If val starts and ends with /
            if len(val) > 1 and val[::len(val)-1] == '//':
                val = val[1:-1]
            limitregexps.setdefault(key, set()).add(re.compile(val))
        elif arg:
            # Nonexisting pages
            try:
                page = globaldata.getpage(arg)
            except KeyError:
                continue
            
            pages.add(arg)

    # If there were no page args, get all non-system pages
    if not pageargs and not pages:
        if not all_pages:
            pages = get_pages(macro)
        else:
            pages = all_pages

    pagelist = set([])

    for page in pages:
        clear = True
        # Filter by regexps (if any)
        if limitregexps:
            for key in limitregexps:
                if not clear:
                    break
                
                data = string.join(getvalues(globaldata, page, key), ', ')

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

    if not keyspec:
        for name in pagelist:
            # At this point, the names should be checked already
            page = globaldata.getpage(name)
            for key in nonguaranteeds_p(page.get('meta', {})):
                # One further check, we probably do not want
                # to see categories in our table by default
                if key != 'WikiCategory':
                    metakeys.add(key)

        metakeys = sorted(metakeys, key=str.lower)
    else:
        metakeys = keyspec
        
    # No data -> bail out quickly, Scotty
    if not pagelist:
        out += t_cell(macro, "Empty MetaTable: " + args)
        out += macro.formatter.table(0)

        globaldata.closedb()
        return out
    
    # Give a class to headers to make it customisable
    out += macro.formatter.table_row(1, {'rowclass': 'meta_header'})
    out += t_cell(macro, '')
    for key in metakeys:
        out = out + t_cell(macro, key)
    out += macro.formatter.table_row(0)

    pagelist = sorted(pagelist)

    tocache = []
    for page in pagelist:
        out = out + macro.formatter.table_row(1)
        out = out + t_cell(macro, page, head=1)
        for key in metakeys:
            vals = getvalues(globaldata, page, key)
            data = qstrip_p(vals).strip('"')
            out = out + t_cell(macro, data)
            tocache.append((page, key, vals))
        out += macro.formatter.table_row(0)
    out += macro.formatter.table(0)
    ce = caching.CacheEntry(macro.request, macro.request.page, 'MetaTable')
    ce.update(repr(tocache))

    globaldata.closedb()

    return out

def getvalues(globaldata, name, key):
    page = globaldata.getpage(name)
    return page.get('meta', {}).get(key, [])
