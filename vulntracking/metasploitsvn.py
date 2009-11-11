#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for metasploit svn

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""
import os, errno, re, subprocess
from collections import defaultdict
import scrapeutil

exploits_svn_url = 'http://metasploit.com/svn/framework3/trunk/modules/exploits'

tmpdir = '/tmp/scraping_metasploit.' + str(os.getuid())

class MetasploitScrapingError(Exception):
    pass

def scrape():
    new = True
    try:
        os.mkdir(tmpdir)
    except OSError, what:
        if what.errno != errno.EEXIST:
            raise
        new = False
    if os.stat(tmpdir).st_uid != os.getuid():
        raise MetasploitScrapingError("suspicious permissions for " + tmpdir)
    if new:
        retcode = subprocess.call(["svn", "co", exploits_svn_url, tmpdir])
    else:
        retcode = subprocess.call(["svn", "update", tmpdir])
    if retcode:
        raise MetasploitScrapingError("svn command returned failure")
    for root, dirs, files in os.walk(tmpdir):
        for fn in files:
            if not fn.endswith('.rb'):
                continue
            zdict = findcve(os.path.join(root, fn))
            if zdict:
                #print 'hit', root, fn, zdict
                yield zdict

def findcve(rbfile):
    seen_refs=0
    zdict = defaultdict(list)
    zdict['feedtype'].append('attack')
    gotany=0
    for line in open(rbfile):
        if not seen_refs and "'References'" in line and '=>' in line:
            seen_refs=1
        elif seen_refs:
            if '=>' in line or (']' in line and '[' not in line):
                break
            m = re.search(r"'([^']*)'\s*,\s*'([^']*)'", line)
            if m and m.group(1) and m.group(2):
                zdict[m.group(1)].append(m.group(2))
                gotany=1
    if gotany:
        pagename = 'MetaSploit ' +rbfile.lstrip(tmpdir).rstrip('.rb').replace('/', '-')
        return pagename, zdict
    else:
        return None

def update_vulns(s):
    scrapeutil.update_vulns(s, scrape(), 'Metasploit', cvekey='CVE')

if __name__ == '__main__':
    for z in scrape():
        print z

