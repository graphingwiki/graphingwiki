#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
    hacked up from opencollab-import-mresolved
    
    @copyright: 2008-2009 Lari Huttunen, Juhani Eronen, Erno Kuusela
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
import sys
import os
import csv
import time
import optparse
import collections
import shelve

from opencollab.util.config import parse_config
from opencollab.wiki import CLIWiki, WikiFailure
from opencollab.meta import Meta, Metas
 
def import_metas(wiki, metas, template, verbose, cves):
    for page, pmeta in metas.iteritems():
        if cves:
            if not page in cves:
                continue
        status = wiki.setMeta( page, pmeta, template=template, replace=True )
        if verbose:
            print status

def main():
    parser = optparse.OptionParser()
    parser.add_option( "-c", "--config",
        action="store",
        type="string", dest="config",
        default = None,
        metavar="CONFIG",
        help="CONFIG file path.")

    parser.add_option("-t", "--template",
                      dest="template",
                      default=None,
                      metavar="TEMPLATE",
                      help="Wiki TEMPLATE.")
    parser.add_option("-u", "--url",
                      dest="url",
                      default=None,
                      metavar="COLLAB-URL",
                      help="COLLAB-URL to connect to.")
    parser.add_option("-k", "--sw-keywords",
                      dest="sw_keywords",
                      default='',
                      metavar="KEYWORDS",
                      help="Only include entries with one of KEYWORDS in the 'vulnerable-software' field")
    parser.add_option("-f", "--file",
                      dest="cves",
                      default='',
                      metavar="FILE",
                      help="Only include cve entries mentioned in FILE")
    parser.add_option("-s", "--shelve",
                      dest="shelvefn",
                      default=None,
                      metavar="SHELVE-FILENAME",
                      help="SHELVE-FILENAME to load data from")
    parser.add_option("-v",
        action="store_true", dest="verbose", default=False,
        help="Enable verbose output." )
    parser.set_usage("%prog [options]")
    options, args = parser.parse_args()
    iopts={}
    if options.shelvefn and os.path.exists(options.shelvefn):
        start = time.time()
        page_metas = shelve.open(options.shelvefn)
        print 'loaded %d metas from %s in %.2f s' % (len(page_metas), options.shelvefn, time.time() - start)
    else:
        parser.error("shelve file name needs to be specified. Use -h for help.")

    if options.config:
        iopts = parse_config(options.config, "creds", "import-nvd-xml")

    if options.template:
        template = options.template
    elif options.config and "template" in iopts["import-nvd-xml"]:
        template = iopts["import-nvd-xml"]["template"]
    else:
        template = "CveTemplate"
    url = None
    if options.url:
        url = options.url
        collab = CLIWiki(url)
    elif options.config and "url" in iopts["creds"]:
        url = iopts["creds"]["url"]
        collab = CLIWiki(url, config=options.config)
    if not url:
        parser.error("Collab URL needs to be specified. Use -h for help.")

    cves = []
    if options.cves:
        cves = file(options.cves).readlines()
    elif options.config and "url" in iopts["creds"]:
        cves = file(iopts["creds"]["url"]).readlines()
    cves = [x.strip() for x in cves]

    if options.url:
        if options.verbose:
            print "Importing metas to", url
        import_metas(collab, page_metas, template, options.verbose, cves)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "Script interrupted via CTRL-C."

