# -*- coding: utf-8 -*-"
action_name = 'metaCSV'

import cgi
import urllib
import csv

from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin.util import MoinMoinNoFooter
from graphingwiki.editing import process_edit, getvalues
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import encode

def execute(pagename, request):
    # Strip non-ascii chars in header
    pagename_header = '%s.csv' % (pagename)
    pagename_header = pagename_header.encode('ascii', 'ignore')
    
    request.http_headers(['Content-Type: text/csv; charset=UTF-8',
                          'Content-Disposition: attachment; ' +
                          'filename="%s"' % pagename_header])
    GetMeta = wikiutil.importPlugin(request.cfg, 'xmlrpc', 'GetMeta')
    class x: pass
    x.request = request
    try:
        args = request.args['args'][0]
    except (KeyError, IndexError):
        args = u''
    z = GetMeta(x, args, keysonly=False)
    if 0:
        print '--', z, '--'
        print 'args', request.args
        print 'pagename', pagename

    out = []
    for keys in z.pop(0):
        out.extend(urllib.unquote(encode(x)) for x in keys)
    
    keys = ['page name'] + out
    writer = csv.writer(request, delimiter=';')
    writer.writerow(keys)

    for row in z:
        out = []
        for x in row[1:]:
            out.extend(x)
        writer.writerow([urllib.unquote(encode(row[0]))] +
                        [urllib.unquote(encode(x)) for x in out])
	
    raise MoinMoinNoFooter
