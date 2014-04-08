# -*- coding: utf-8 -*-"
"""
    setMetaJSON2 action plugin for MoinMoin/Graphingwiki
     - Refactored meta editing backend with more sensible api

    @copyright: 2014 by Lauri Pokka larpo@clarifiednetworks.com
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

try:
    import simplejson as json
except ImportError:
    import json


from graphingwiki.editing import set_metas
from graphingwiki import values_to_form

def execute(pagename, request):
    _ = request.getText
    if request.environ['REQUEST_METHOD'] != 'POST':
        #405 Method Not Allowed
        request.status_code = 405
        return

    pagename = pagename.strip()

    form = values_to_form(request.values)

    indata = form.get('metas', [None])[0]
    batch = form.get('batch', [None])[0]
    if not indata:
        #400 Bad Request
        request.status_code = 400
        request.write('No data')
        return

    cleared, added, discarded = {}, {}, {}

    def parse(metas, page=pagename):
        add = metas.get('add', {})
        remove = metas.get('del', {})
        put = metas.get('set', {})

        discarded[page] = remove
        added[page] = dict(add.items() + put.items())
        cleared[page] = put.keys()

    indata = json.loads(indata)

    # edit multiple pages
    if batch:
        for _page, _metas in indata.iteritems():
            parse(_metas, _page)
    # edit single page
    else:
        parse(indata)

    success, msg = set_metas(request, cleared, discarded, added)
    if not success:
        #403 Forbidden, the set_metas fails when user doesn't have write perms
        request.status_code = 403

    json.dump(dict(msg=msg), request)

