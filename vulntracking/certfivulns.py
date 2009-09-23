#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Screen scraper for CERT-FI vuln feed

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

import urllib, re
from collections import defaultdict
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS
rssurl='''http://www.cert.fi/rss/haavoittuvuudet.xml'''


def scrape_rss():
    for link in BSS(urllib.urlopen(rssurl)).findAll("link"):
        if link.contents[0].startswith('http://www.cert.fi/haavoittuvuudet'):
            yield scrape_one_vuln(link.contents[0])

def textify(s):
    out = []
    for elt in s.contents:
        if isinstance(elt, basestring):
            s = unicode(elt).strip()
            if s:
                out.append(s)
        else:
            out += textify(elt)
    return out

def scrape_one_vuln(url):
    soup = BS(urllib.urlopen(url), convertEntities="html")
    cves = set(map(unicode, soup.findAll('a', text=re.compile(r'^CVE-'))))
    
    zdict = defaultdict(list)
    for tr in soup.find("table", "userdefinedTable").findAll("tr"):
        try:
            za, zb, zc=tr.findAll('td')
        except ValueError:
            continue
        k = textify(za)[0].rstrip(':')
        for s in textify(zb):
            zdict[k].append(s.lstrip(u'- '))
    return url, cves, zdict


if __name__ == '__main__':
    for z in scrape_rss():
        print z
