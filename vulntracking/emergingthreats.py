#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for emergingthreats.net snort sigs

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

import urllib, re, socket

from collections import defaultdict

emerging_url = 'http://www.emergingthreats.net/rules/emerging-all.rules'
def fix_refs(refs): 
    for refk, refv in refs: 
        if refk == 'url': 
            yield 'URL', 'http://%s' % refv
        elif refk == 'cve': 
            yield 'CVE', 'CVE-%s' % refv
        elif refk == 'bugtraq': 
            yield 'Bugtraq ID', refv

def scrape():
    for line in open("emerging-all.rules"): #urllib.urlopen(emerging_url):
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
                zdict[refk].append(refv)
            for x in classtypes:
                zdict['EmergingThreats-classtype'].append(x)
            if proto:
                zdict['EmergingThreats-target'].append("%s:%s" % (proto.upper(), port))
            if (msg.startswith('ET EXPLOIT') or
                'CVE' in zdict):
                yield u'EmergingThreats ' + unicode(msg, 'latin-1'), zdict

def update_vulns(s):
    for vid, data in scrape():
        s[str(vid)] = data
        for cveid in map(str, data.get('CVE', [])):
            if cveid not in s:
                d = defaultdict(list)
            else:
                d = s[cveid]
            d['EmergingThreats'].append(u"[[" + vid + u"]]")
            s[cveid] = d


if __name__ == '__main__':
    for z in scrape():
        print z
