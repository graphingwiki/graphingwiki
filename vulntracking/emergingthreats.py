#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for emergingthreats.net snort sigs

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

import urllib, re, socket

from collections import defaultdict

emerging_exploits_url = 'http://www.emergingthreats.net/rules/emerging-exploit.rules'

def fix_refs(refs):
    new_refs = list()
    for ref in refs:
        if ref[0] == 'url':
            new_refs.append(('URL', 'http://%s' % ref[1]))
        elif ref[0] == 'cve':
            new_refs.append(('CVE', 'CVE-%s' % ref[1]))
        elif ref[0] == 'bugtraq':
            new_refs.append(('Bugtraq ID', ref[1]))
            
    return new_refs

def scrape():
    for line in urllib.urlopen(emerging_exploits_url):
        refs  = re.findall(r'reference:(\w+),([^; ]*)[; ]', line)
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
            zdict = defaultdict()
            for typ, val in refs:
                zdict.setdefault(typ, list()).append(val)
            for x in classtypes:
                zdict.setdefault('Emergingthreats-classtype', list()).append(x)
            if proto:
                zdict['Emergingthreats-target'] = "%s:%s" % (proto.upper(), port)
            yield zdict

if __name__ == '__main__':
    for z in scrape():
        print z
