# -*- coding: utf-8 -*-"
"""
    InterMetaTable macro plugin to MoinMoin/Graphingwiki
     - Shows in tabular form the Metadata of desired pages across different
       collab instances

    @copyright: 2011 by Lauri Pokka <larpo@clarifiednetworks.com>
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

from urllib import quote
from graphingwiki.util import form_writer as wr

from MoinMoin import config

try:
    import simplejson as json
except ImportError:
    import json

def do_macro(request, **kw):
    pagename = request.page.page_name
    baseurl = request.getScriptname()
    args = {"pagename": pagename, "baseurl": baseurl}

    try:
        baseurl = request.cfg.collab_baseurl
        args['baseurl'] = baseurl

        user = request.user.name
        active = request.cfg.interwikiname
        path = request.cfg.collab_basedir

        from collabbackend import listCollabs
        collabs = []
        for (shortName, title, motd, link, active) in listCollabs(baseurl, user, path, active):
            collabs.append(shortName)

        if not 'collabs' in kw:
            args['collabs'] = collabs

        else:
            if type(kw['collabs']) is not type([]):
                kw['collabs'] = [kw['collabs']]
            
            for collab in kw['collabs']:
                if not collab in collabs:
                    kw['collabs'].remove(collab)
                    if 'inaccessibleCollabs' not in args:
                        args['inaccessibleCollabs'] = list()

                    args['inaccessibleCollabs'].append(collab)


    except:
       pass 

    return u'''
    <div class="InterMetaTable" data-options="%s"></div>
    '''% quote(json.dumps(dict(args.items() + kw.items())))


def execute(macro, args):
    request = macro.request

    if args is None:
        args = ''

    optargs = {}

    for arg in args.split(','):
        arg = arg.strip()
        if ':=' in arg:
            key, val = arg.split(':=')
            optargs.setdefault(key.encode(config.charset), list()).append(val)
        else:
            optargs.setdefault('selector', list()).append(arg)
 
    return do_macro(request, **optargs)
