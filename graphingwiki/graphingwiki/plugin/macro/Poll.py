# -*- coding: utf-8 -*-"
"""
    Poll macro plugin to MoinMoin/Graphingwiki
     - Polling/voting widget

    @copyright: 2014 by Lauri Pokka <larpo@clarifiednetworks.com>
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

from graphingwiki.editing import metatable_parseargs, get_metas


from urllib import quote

from MoinMoin import config

try:
    import simplejson as json
except ImportError:
    import json


def execute(macro, args):
    request = macro.request
    pagename = request.page.page_name

    if args is None:
        args = ''

    opts = {"pagename": pagename}

    if request.user.valid and request.user.name:
        opts["username"] = request.user.name

    for arg in args.split(','):
        arg = arg.strip()
        if '=' in arg:
            key, val = arg.split('=')
            opts.setdefault(key.encode(config.charset), list()).append(val)
        else:
            opts.setdefault('keys', list()).append(arg)


    return u'''
    <div class="poll" data-options="%s"></div>
    ''' % quote(json.dumps(dict(opts.items())))
