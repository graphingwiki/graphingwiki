# -*- coding: utf-8 -*-"
action_name = 'metaCSV'

import cgi
import urllib
import csv

from MoinMoin import wikiutil
from MoinMoin import config
from graphingwiki.editing import process_edit, getvalues
from graphingwiki.editing import getmeta_to_table
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

    table = GetMeta(x, args, keysonly=False)
    table = getmeta_to_table(table)
    if 0:
        print '--', table, '--'
        print 'args', request.args
        print 'pagename', pagename

    writer = csv.writer(request, delimiter=';')

    for row in table:
        writer.writerow(row)
