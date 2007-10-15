action_name = 'MetaCSV'

import cgi
import urllib
import csv

from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin.util import MoinMoinNoFooter
from graphingwiki.editing import process_edit, getvalues
from graphingwiki.editing import metatable_parseargs

def execute(pagename, request):
    request.http_headers(['Content-Type: text/plain',
                          'Not-Content-Disposition: attachment; filename="%s.csv"' % pagename])
    GetMeta = wikiutil.importPlugin(request.cfg, 'xmlrpc', 'GetMeta')
    class x: pass
    x.request = request

    if 0:
        keys, stuff = GetMeta(x, pagename, keysonly=False)
        writer = csv.writer(request)
	vals = map(lambda x: x[0], stuff[1:])
        writer.writerows(zip(keys, vals))
    else:
        z = GetMeta(x, pagename, keysonly=False)
	keys = ['page name'] + z.pop(0)
        writer = csv.writer(request)
	writer.writerow(keys)
	for row in z:
            # why are the values lists of length 1?
            row[1:] = map(lambda x: x[0].encode('utf-8'), row[1:])
            writer.writerow(row)
	
    raise MoinMoinNoFooter
    