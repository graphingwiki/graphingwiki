#! /usr/bin/env python

import os
import sys

try:
    wikipath = sys.argv[1]
    os.chdir(os.path.join(wikipath, 'data/pages'))
except:
    print "Usage: " + sys.argv[0] + " <path-to-wiki>"
    raise

# Moin dirs
sys.path.insert(0, os.path.join(wikipath, 'config'))
sys.path.insert(0, CPEDIR)
from MoinMoin import wikiutil
from MoinMoin import request
from MoinMoin.Page import Page
from MoinMoin.wikiutil import unquoteWikiname

pages = []

# List pages with graphdata
for dir in [x for x in os.listdir('.') if os.path.isdir(x)]:
    if 'graphdata.pickle' in os.listdir(dir):
        pages.append(str(unquoteWikiname(dir)))

for pagename in pages:
    print "Rehashing " + pagename
    # Make a new request for the page, get raw text
    req = request.RequestCLI(pagename=pagename)
    p = Page(req, pagename)
    pagedir = p.getPagePath()
    text = p.get_raw_body()
    
    # Apply the graphsaver-action to the page
    graphsaver = wikiutil.importPlugin(req.cfg, 'action', 'savegraphdata')
    graphsaver(pagename, req, text, pagedir, p)
