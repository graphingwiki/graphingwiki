#! /usr/bin/env python

import os
import sys

# Moin dirs
sys.path.insert(0, '/home/secpelle/public_access/wiki/config')
sys.path.insert(0, '/home/secpelle/cpe/supervisor')
from MoinMoin import wikiutil
from MoinMoin import request
from MoinMoin.Page import Page

wikipath = '/home/secpelle/public_access/wiki/data/pages/'

os.chdir(wikipath)

pages = []

# List pages with graphdata
for dir in [x for x in os.listdir('.') if os.path.isdir(x)]:
    if 'graphdata.pickle' in os.listdir(dir):
        pages.append(dir)

for pagename in pages:
    # print "Rehashing " + pagename
    # Make a new request for the page, get raw text
    req = request.RequestCLI(pagename=pagename)
    p = Page(req, pagename)
    pagedir = p.getPagePath()
    text = p.get_raw_body()
    
    # Apply the graphsaver-action to the page
    graphsaver = wikiutil.importPlugin(req.cfg, 'action', 'savegraphdata')
    graphsaver(pagename, req, text, pagedir, p)
