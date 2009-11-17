#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for emergingthreats.net snort sigs

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

import urllib, re, socket

from collections import defaultdict
import scrapeutil

emerging_url = 'http://www.emergingthreats.net/rules/emerging-all.rules'
def fix_refs(refs): 
    for refk, refv in refs: 
        if refk == 'url': 
            yield 'ref-url', 'http://%s' % refv
        elif refk == 'cve': 
            yield 'CVE ID', str(refv)
        elif refk == 'bugtraq': 
            yield 'Bugtraq ID', refv
            

def scrape():
#    for line in open("emerging-all.rules"): #urllib.urlopen(emerging_url):
    for line in urllib.urlopen(emerging_url):
        refs  = re.findall(r'reference:(\w+),([^; ]*)[; ]', line)
        x = re.search(r'msg:"([^"]*)"', line)
        if not x:
            continue
        msg = x.group(1)
        if not msg:
            continue

        refs = fix_refs(refs)

        classtypes  = re.findall(r'classtype:([^; ]*)[; ]', line)
        m = re.match(r'alert (\w+) \$\S* any -> \$\S* (\S+)', line)
        if m:
            proto, port = m.groups()
            if port.startswith('$'):
                try:
                    port = str(socket.getservbyname(port[1:].split('_')[0].lower()))
                except socket.error:
                    proto, port = None, None
        else:
            proto, port = None, None
        if refs or classtypes:
            zdict = defaultdict(list)
            zdict['feedtype'].append('defense')
            for refk, refv in refs:
                zdict[refk].append(unicode(refv))
            for x in classtypes:
                zdict['EmergingThreats-classtype'].append(unicode(x))
            if proto:
                zdict['EmergingThreats-target'].append(u"%s:%s" % (proto.upper(), port))
            zdict['msg'].append(msg)
            if (msg.startswith('ET EXPLOIT') or
                'CVE' in zdict):
                yield 'EmergingThreats-' + scrapeutil.hash_name(msg), zdict


wiki_template = ("EmergingThreatsVulnTemplate","""
= @PAGE@ =

 CVE ID::
 feedtype::
 msg:: 

 URL:: 
 EmergingThreats-classtype::
 EmergingThreats-target:: 
 

<<LinkedIn>>

----
CategoryVuln
CategoryEmergingThreatsVuln
""")

def update_vulns(s):
    scrapeutil.update_vulns(s, scrape(), scraperkey="EmergingThreats",
                            template=wiki_template)

if __name__ == '__main__':
    for z in scrape():
        print z
