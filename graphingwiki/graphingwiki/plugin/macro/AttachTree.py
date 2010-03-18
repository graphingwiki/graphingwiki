# -*- coding: utf-8 -*-"
"""
    AttachTree macro plugin to MoinMoin
     - Renders a tree of attachments for urlencoded paths in attachments

    @copyright: 2008-2010 by Marko Laakso <fenris@iki.fi>

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

from urllib import unquote, quote
import os

from MoinMoin.action.AttachFile import _get_files, getAttachUrl

def walk(*paths):
    result = dict()
    for path in paths:
        current = result
        for bite in path.split(os.sep):
            current = current.setdefault(bite, dict())
    return result

def render(req, f, content, parent='', depth=0):
    listfmt = {'class': 'attachtree_list'}
    direntryfmt = {'class': 'attachtree_direntry'}
    fileentryfmt = {'class': 'attachtree_fileentry'}

    result = f.bullet_list(1, **listfmt)

    for entry, values in sorted(content.items()):
        fullname = os.path.join(parent, unicode(entry))
        if not values.items():
            result += f.listitem(1, **fileentryfmt)
            link = getAttachUrl(f.page.page_name,
                                quote(fullname.encode("iso-8859-15"), safe=""),
                                req, escaped=1)
            result += f.url(1, link, 'attachtree_link')
            result += f.text(entry)
            result += f.url(0)
            result += f.listitem(0)
        else:
            result += f.listitem(1, **direntryfmt)
            result += f.text(entry)
            result += f.listitem(0)
            result += render(req, f, values, fullname, depth + 1)

    result += f.bullet_list(0)
    return result

def formatAttachTree(request, f):
    files = _get_files(request, f.page.page_name)
    realfiles = map(unquote, files)

    if not files:
        return f.text('No attachments, no tree.')

    divfmt = {'class': 'attachtree_area'}

    result = f.div(1, **divfmt)
    result += render(request, f, walk(*realfiles))
    result += f.div(0)

    return result
        
def execute(self, args):
    return formatAttachTree(self.request, self.formatter)
