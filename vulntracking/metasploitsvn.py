#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for metasploit svn

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""
import os, errno, re, subprocess

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
        raise MetasploitScrapingError("svn command returnde failure")
    for root, dirs, files in os.walk(tmpdir):
        for fn in files:
            if not fn.endswith('.rb'):
                continue
            for cveref in findcve(os.path.join(root, fn)):
                #print 'hit', root, fn, cveref
                yield cveref


def findcve(rbfile):
    PRE_REFS, IN_REFS = 1, 2
    state = PRE_REFS
    for line in open(rbfile):
        if state == PRE_REFS and "'References'" in line and '=>' in line:
            state = IN_REFS
        elif state == IN_REFS:
            if '=>' in line or (']' in line and '[' not in line):
                return
            m = re.search(r"'([^']*)'\s*,\s*'([^']*)'", line)
            if m:
                yield m.groups()

if __name__ == '__main__':
    for z in scrape():
        print z

                

