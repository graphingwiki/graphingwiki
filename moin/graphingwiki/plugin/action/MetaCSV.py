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

    z = GetMeta(x, pagename, keysonly=False)
    if 0: print '--', z, '--'
    keys = ['page name'] + z.pop(0)
    writer = csv.writer(request)
    writer.writerow(keys)
    for row in z:
        # why are the values lists?
        def val2text(val):
            if not val:
                return ''
            else:
                out = u' '.join(val)
                return out.encode('utf-8')
        row[1:] = map(val2text, row[1:])
        writer.writerow(row)
	
    raise MoinMoinNoFooter
    
