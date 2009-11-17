#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
    @copyright: 2008-2009 Lari Huttunen, Juhani Eronen, Erno Kuusela
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
import sys
import os
import re
import optparse
import collections
import shelve


from scrapeutil import  normalize_cveid

from opencollab.util.config import parseConfig
from opencollab.wiki import CLIWiki, WikiFailure, WikiFault
from opencollab.meta import Meta, Metas
 
def import_metas(wiki, metas, verbose, include_pages, metafiltspec,
                 link_depth=None, delete_first=False):
    uploaded_templates = []
    
    if link_depth:
        link_depth = int(link_depth)
        vuln_to_cve = collections.defaultdict(list)
        cve_to_vuln = collections.defaultdict(list)
        for pagename, pmdict in metas.iteritems():
            # skip templates
            if isinstance(pmdict, basestring):
                continue

            for cveid in map(normalize_cveid, pmdict.get("CVE ID", []) + pmdict.get("CVE ID", [])):
                vuln_to_cve[pagename].append(cveid)
                cve_to_vuln[cveid].append(pagename)
                    

    def page_included(pagename):
        if include_pages and pagename not in include_pages:
            return False

        if link_depth:
            if pagename.startswith('CVE-') or pagename.startswith('CAN-'):
                if len(cve_to_vuln[pagename]) >= link_depth:
                    print 'take', pagename, '- linkcount', len(cve_to_vuln[pagename]), 'greater or equal to limit', link_depth
                else:
                    return False
            else:
                cves = vuln_to_cve[pagename]
                ok = 0
                for cveid in cves:
                    if len(cve_to_vuln[cveid]) >= link_depth:
                        ok=1
                if not ok:
                    print pagename, 'had no links to sufficiently linked cves'
                    return False
                else:
                    print pagename, 'did have links to sufficiently linked cves'

        if metafiltspec:
            pm = metas[pagename]
            ok=0
            for filtkey, filtrx in metafiltspec.items():
                if filtkey in pm:
                    for pagemetaval in pm[filtkey]:
                        if filtrx.match(pagemetaval):
                            ok=1
                            break
            if not ok:
                return False

        return True

    allcount=len(metas)
    passed=0
    for page, pmeta in metas.iteritems():
        if page.endswith('Template'):
            continue
        
        if not page_included(page):
            #print "skip", page, "(filter)"
            continue


        passed += 1
        print 'import_metas: doing page', page
        
        kw = {'replace': True}

        z = 'gwikitemplate'
        x = pmeta.get(z)
        if x:
            kw['template'] = templatename = x[0]
            del pmeta[z]
        else:
            kw['template'] = templatename =  u'GenericVulnTemplate'
            
        if templatename not in uploaded_templates:
            print 'upload template', templatename
            try:
                wiki.getPage(templatename)
            except WikiFault, what:
                if 'No such page' in str(what):
                    wiki.putPage(templatename, metas[str(templatename)])
                else:
                    raise
            uploaded_templates.append(templatename)

        def linkify(text):
            if not text.startswith(u'[['):
                text = u'[[' + text + u']]'
            return text
            
        for mk in pmeta:
            if mk == 'CVE ID':
                pmeta[mk] = map(linkify, pmeta[mk])

        if delete_first:
            status = wiki.deletePage(page)
            if verbose:
                print 'delete:', status
        if 1:
            status = wiki.setMeta(page, pmeta, **kw)
        else:
            status = "(dry run)"
        if verbose:
            print status

    print 'imported', passed, 'of', allcount, 'pages'


def main():
    parser = optparse.OptionParser()
    parser.add_option( "-c", "--config",
        action="store",
        type="string", dest="config",
        default = None,
        metavar="CONFIG",
        help="CONFIG file path.")

    parser.add_option("-u", "--url",
                      dest="url",
                      default=None,
                      metavar="COLLAB-URL",
                      help="COLLAB-URL to connect to.")
    parser.add_option("-k", "--match-metakey",
                      dest="metafiltspec",
                      default='',
                      metavar="METASPEC",
                      help="Only include entries that have matching metas to METASPEC (format: <key>=<val-regexp>)")
    parser.add_option("-p", "--pages",
                      dest="pagelist",
                      default='',
                      metavar="PAGES",
                      help="Only include pages named PAGES (format: page1,page2,...")
    parser.add_option("-f", "--file",
                      dest="pages_file",
                      default='',
                      metavar="FILE",
                      help="Only include pages mentioned in FILE (format: whitespace-separated)")
    parser.add_option("-s", "--shelve",
                      dest="shelvefn",
                      default=None,
                      metavar="SHELVE-FILENAME",
                      help="SHELVE-FILENAME to load data from")

    parser.add_option("-l", "--link-depth",
                      dest="link_depth",
                      default=None,
                      metavar="NR",
                      help="skip cve entries and related vulns with less than NR related links")

    parser.add_option("-d", "--delete-first",
        action="store_true", dest="delete_first", default=False,
        help="Replace pages by deleting them first (for changing templates)" )

    parser.add_option("-v",
        action="store_true", dest="verbose", default=False,
        help="Enable verbose output." )
    parser.set_usage("%prog [options]")
    options, args = parser.parse_args()
    iopts={}
    if options.shelvefn and os.path.exists(options.shelvefn):
        page_metas = dict(shelve.open(options.shelvefn))
        print '%d metas in %s' % (len(page_metas), options.shelvefn)
    else:
        parser.error("shelve file name needs to be specified. Use -h for help.")

    if options.config:
        iopts = parseConfig(options.config, "creds", "import-vulndata-from-pickle")

    url = None
    if options.url:
        url = options.url
        collab = CLIWiki(url)
    elif options.config and "url" in iopts["creds"]:
        url = iopts["creds"]["url"]
        collab = CLIWiki(url, config=options.config)
    if not url:
        parser.error("Collab URL needs to be specified. Use -h for help.")


    if options.config and "url" in iopts["creds"]:
        cves = file(iopts["creds"]["url"]).readlines()

    if options.pages_file:
        try:
            pagenames = file(options.pages_file).read().split()
        except EnvironmentError, what:
            sys.exit("failed to read %s: %s" % (options.pages_file, what))
    elif options.pagelist:
        pagenames = options.pagelist.split(",")
    else:
        pagenames = None

    metafiltspec = {}
    if metafiltspec:
        for x in options.metafiltspec.split(","):
            if "=" not in x:
                sys.exit("bad metafiltspec: %s" % x)
            k, v = x.split("=", 1)
            metafiltspec[k] = re.compile(v)
    if options.url:
        if options.verbose:
            print "Importing metas to", url

        import_metas(collab, page_metas, options.verbose, pagenames,
                     metafiltspec, options.link_depth, options.delete_first)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "Script interrupted via CTRL-C."

