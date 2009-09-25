#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for emergingthreats.net snort sigs

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

import urllib, re, socket

emerging_exploits_url = 'file:///tmp/emerging-exploit.rules'
#emerging_exploits_url = 'http://www.emergingthreats.net/rules/emerging-exploit.rules'

def scrape():
    for line in urllib.urlopen(emerging_exploits_url):
        refs  = re.findall(r'reference:(\w+),([^; ]*)[; ]', line)
        classtypes  = re.findall(r'classtype:(\w+),([^; ]*)[; ]', line)
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
            yield refs, classtypes, (proto, port)

