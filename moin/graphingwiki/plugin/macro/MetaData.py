# -*- coding: iso-8859-1 -*-
"""
    MetaData macro plugin to MoinMoin
     - Formats the semantic data visually

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
from inspect import getargspec
from urllib import unquote as url_unquote

from MoinMoin import config

from graphingwiki.patterns import encode
from graphingwiki.patterns import WikiNode

Dependencies = ['metadata']

def execute(macro, args):
    arglist = [x.strip() for x in args.split(',') if x.strip()]

    # [[MetaData()]]
    if not arglist:
        return ""
    # Placeholders etc [[MetaData(a,)]]
    elif len(arglist) < 2:
        return ''

    key = arglist[0]
    val = ','.join(arglist[1:])

    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

    graphdata = WikiNode(request).graphdata
    
    if not hasattr(graphdata, 'keys_on_pages'):
        graphdata.reverse_meta()

    keys_on_pages = graphdata.keys_on_pages
    vals_on_pages = graphdata.vals_on_pages
    
    result = []

    # Fix for moin 1.3.5
    listmeta = {}
    keymeta = {}
    valmeta = {}
    if getargspec(formatter.definition_list)[2]:
        listmeta = {'class': 'meta_list'}
        keymeta = {'class': 'meta_key'}
        valmeta = {'class': 'meta_val'}

    result.append(formatter.definition_list(1, **listmeta))

    keylist = [unicode(url_unquote(x), config.charset)
               for x in sorted(keys_on_pages.get(key, ''))]
    if request.page.page_name in keylist:
        keylist.remove(request.page.page_name)
    kwkey = {'querystr': 'action=MetaSearch&q=' + key,
             'allowed_attrs': ['title', 'href', 'class'],
             'class': 'meta_search'}
    if keylist:
        if len(keylist) > 10:
            keylist = keylist[:9] + ['...']
        keylist = _('Key also on pages') + ':\n' + '\n'.join(keylist)
        kwkey['title'] = keylist

    vallist = [unicode(url_unquote(x), config.charset)
               for x in sorted(vals_on_pages.get(encode(val), ''))]
    if request.page.page_name in vallist:
        vallist.remove(request.page.page_name)
    kwval = {'querystr': 'action=MetaSearch&q=' + val,
             'allowed_attrs': ['title', 'href', 'class'],
             'class': 'meta_search'}
    if vallist:
        if len(vallist) > 10:
            vallist = vallist[:9] + ['...']
        vallist = _('Value also on pages') + ':\n' + '\n'.join(vallist)
        kwval['title'] = vallist

    result.extend([formatter.definition_term(1, **keymeta),
                   formatter.pagelink(1, request.page.page_name,
                                      request.page, **kwkey),
                   formatter.text(key),
                   formatter.pagelink(0),
                   formatter.definition_term(0),

                   formatter.definition_desc(1, **valmeta),
                   formatter.pagelink(1, request.page.page_name,
                                      request.page, **kwval),
                   formatter.text(val),
                   formatter.pagelink(0),
                   formatter.definition_desc(0)])

    arglist = arglist[2:]

    result.append(macro.formatter.definition_list(0))

    # Cleanup
    graphdata.closedb()

    return u'\n'.join(result)
