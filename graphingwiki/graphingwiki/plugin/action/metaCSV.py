# -*- coding: utf-8 -*-"
action_name = 'metaCSV'

import cgi
import urllib
import csv

from MoinMoin import wikiutil

from graphingwiki.editing import getmeta_to_table
from graphingwiki.util import encode_page
from graphingwiki import values_to_form

def execute(pagename, request):
    # Strip non-ascii chars in header
    pagename_header = '%s.csv' % (pagename)
    pagename_header = pagename_header.encode('ascii', 'ignore')
    
    request.content_type = 'text/csv; charset=UTF-8'
    request.headers['Content-Disposition'] = \
        'attachment; filename="%s"' % pagename_header
    GetMeta = wikiutil.importPlugin(request.cfg, 'xmlrpc', 'GetMeta')
    class x: pass
    x.request = request

    form = values_to_form(request.values)

    try:
        args = form['args'][0]
    except (KeyError, IndexError):
        args = u''

    table = GetMeta(x, args, keysonly=False)
    table = getmeta_to_table(table)
    if 0:
        print '--', table, '--'
        print 'args', args
        print 'pagename', pagename

    writer = csv.writer(request, delimiter=';')

    for row in table:
        writer.writerow(map(encode_page, row))
