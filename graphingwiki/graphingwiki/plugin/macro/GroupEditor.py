# -*- coding: utf-8 -*-"
"""
    GroupEditor macro plugin for MoinMoin/Graphingwiki
    The functionality is implemented on gwikicommon/js/GroupEditor.js

    @copyright: 2014 by Lauri Pokka larpo@codenomicon.com
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from urllib import quote

try:
    import simplejson as json
except ImportError:
    import json


def do_macro(request, **kw):
    return '''
    <h2>Group Editor</h2>
    <div class="groupeditor" data-options="%s">
    </div>
    <hr>
    ''' % quote(json.dumps(kw.items()))


def execute(macro, args):
    return do_macro(macro.request)
