# -*- coding: utf-8 -*-"
"""
    Collection of utilities that are used from javascript

    @copyright: 2011 Lauri Pokka <larpo@clarifiednetworks.com>
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
from graphingwiki.util import format_wikitext
from graphingwiki.editing import get_properties

from MoinMoin import wikiutil
from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page

try:
    import simplejson as json
except ImportError:
    import json

def execute(pagename, request):
    request.emit_http_headers()

    util = request.form.get('util', [None])[0]

    if util == "format":
        txt = request.form.get('text', [None])[0]
        request.write(format_wikitext(request, txt))

    elif util == "getTemplate":
        template = request.form.get('name', [None])[0]
        template_page = wikiutil.unquoteWikiname(template)
        if request.user.may.read(template_page):
            editor = PageEditor(request, template_page)
            text = editor.get_raw_body()
            request.write(text)

    elif util == "newPage":
        page = request.form.get('page', [None])[0]
        content = request.form.get('content', [""])[0]

        if request.request_method != 'POST':
            return

        if not page:
            msg =  "Page name not defined!"
            json.dump(dict(status="error", msg=msg), request)
            return

        if not request.user.may.write(page):
            msg =  "You are not allowed to edit this page"
            json.dump(dict(status="error", msg=msg), request)
            return

        p = Page(request, page)
        if p.exists():
            msg = "Page already exists"
            json.dump(dict(status="error", msg=msg), request)
            return

        editor = PageEditor(request, page)
        msg = editor.saveText(content,  p.get_real_rev())
        json.dump(dict(status="ok", msg=msg), request)


    elif util == "getProperties":
        key = request.form.get('key', [''])[0]
        json.dump(get_properties(request, key), request)
        return

    elif util == "uploadFile":
        from MoinMoin.action.AttachFile import add_attachment, AttachmentAlreadyExists

        form = request.form
        overwrite = form.get('overwrite', 0)

        response = dict(success=list(), failed=list())
        for key in form:
            if key.endswith("__filename__"):
                filename = form.get(key, None)
                fileobj = form.get(key[:-12], [None])[-1]
                try:
                    t,s = add_attachment(request, pagename, filename, fileobj, overwrite=overwrite)
                    response['success'].append(filename)
                except AttachmentAlreadyExists:
                    response['failed'].append(filename)


        json.dump(response ,request)
        return
