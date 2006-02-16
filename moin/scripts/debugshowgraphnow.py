#! /usr/bin/env python

import os
import sys

try:
    wikipath = sys.argv[2]
    os.chdir(wikipath)
except:
    print "Usage: " + sys.argv[0] + " <pagename> <path-to-wiki>" 
    raise

# Moin dirs
sys.path.insert(0, os.path.join(wikipath, 'config'))
from MoinMoin import wikiutil
from MoinMoin import request
from MoinMoin.Page import Page

pagename = sys.argv[1]

# Make a new request for the page, get raw text
req = request.RequestCLI(pagename=pagename)
req.form['action'] = ['ShowGraphNow']
req.form['colorby'] = ['Status']
req.form['orderby'] = ['Year']
p = Page(req, pagename)
pagedir = p.getPagePath()
text = p.get_raw_body()

# Apply the showgraph-action to the page
showgraph = wikiutil.importPlugin(req.cfg, 'action', 'ShowGraph')
showgraph(pagename, req)
