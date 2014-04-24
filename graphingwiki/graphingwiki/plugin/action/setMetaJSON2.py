# -*- coding: utf-8 -*-"
"""
    setMetaJSON2 action plugin for MoinMoin/Graphingwiki
     - Refactored meta editing backend with more sensible api

    Reads edit transactions as JSON from POST body.
    An example JSON message:
        [
            {'op' : 'del', 'key': 'foo', 'value': 'bar'},
            {'op' : 'set', 'key': 'to_be_emptied'},
            {'op' : 'set', 'key': 'foo2', 'value': ['val1', 'val2']},
            {'op' : 'add', 'key': 'foo2', 'value': ['bar'], 'page': 'foopage'}
        ]

    @copyright: 2014 by Lauri Pokka larpo@clarifiednetworks.com
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

try:
    import simplejson as json
except ImportError:
    import json


from graphingwiki.editing import set_metas

def execute(pagename, request):
    _ = request.getText

    request.content_type = "application/json"

    if request.environ['REQUEST_METHOD'] != 'POST':
        #405 Method Not Allowed
        request.status_code = 405
        return

    pagename = pagename.strip()
    indata = request.read()

    if not indata:
        #400 Bad Request
        request.status_code = 400
        request.write('No data')
        return

    cleared, added, discarded = {}, {}, {}

    def parse(row):
        op = row.get('op', None)
        page = row.get('page', pagename)
        key = row.get('key', None)
        value = row.get('value', [])
        if type(value) != list:
            value = [value]

        if op == 'set':
            cleared.setdefault(page, set()).add(key)
        elif op == 'del':
            disc = discarded.setdefault(page, dict())
            disc.setdefault(key, list()).extend(value)

        if op in ['add', 'set']:
            add = added.setdefault(page, dict())
            add.setdefault(key, list()).extend(value)

    indata = json.loads(indata)

    if type(indata) is list:
        for data in indata:
            parse(data)
    else:
        parse(indata)

    success, msg = set_metas(request, cleared, discarded, added)
    if not success:
        #403 Forbidden, the set_metas fails when user doesn't have write perms
        request.status_code = 403

    json.dump(dict(msg=msg), request)

