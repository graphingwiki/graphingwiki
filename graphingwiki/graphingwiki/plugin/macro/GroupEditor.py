# -*- coding: utf-8 -*-"
"""
    GroupEditor macro plugin for MoinMoin/Graphingwiki
    The functionality is implemented on gwikicommon/js/GroupEditor.js

    @copyright: 2014 by Lauri Pokka larpo@codenomicon.com
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import json
from urllib import quote


def do_macro(request, **kw):
    opts = {"baseurl": request.getScriptname()}

    return '''
    <h2>Group Editor</h2>
    <div class="no-bootstrap warning">
    <p>
        <strong>
        Bootstrap-based theme (opencollab, codedenomicon, ficora etc) is required for this editor to function properly.
        </strong>
    </p>
    </div>
    <div class="groupeditor" data-options="%s">
    </div>
    <hr>
    ''' % quote(json.dumps(dict(opts.items() + kw.items())))


def execute(macro, args):
    return do_macro(macro.request)
