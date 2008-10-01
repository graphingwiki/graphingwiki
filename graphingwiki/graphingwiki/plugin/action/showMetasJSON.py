# -*- coding: utf-8 -*-"
"""
    showMetasJson
      - Shows meta values in a metatable kind a fasion in JSON 

    @copyright: 2008  <therauli@ee.oulu.fi>
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

from graphingwiki.editing import metatable_parseargs, getmetas

def execute(pagename, request):
    request.http_headers()
    _ = request.getText

    args = request.form.get('args', [None])[0]
    if not args:
        request.write('No data')
        return

    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, args, get_all_keys=True)
    
    request.write('[ ')

    pagecount = 1
    for page in pagelist:
        request.write('"%s"' % page)
        request.write(' : ')
        request.write(' { ')
        metas = getmetas(request, globaldata, page, metakeys, display=False, checkAccess=True)
        metacount = 1
        for meta in metas:
            request.write('"%s"' % meta)
            request.write(' : ')
            request.write(' [ ')
            request.write(" , ".join(['"%s"' % x[0] for x in metas[meta]]))
            if metacount == len(metas):
                request.write(' ] ')
            else:
                request.write(' ], ')
            metacount += 1
            
        if pagecount == len(pagelist):
            request.write(' } ')
        else:
            request.write(' }, ')
        pagecount +=1

    request.write(' ] ')
