#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for CERT-FI vuln feed

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

import urllib, re
from collections import defaultdict
from osvdb import textify
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS
rssurl='''http://www.cert.fi/rss/haavoittuvuudet.xml'''


def scrape_rss():
    for link in BSS(urllib.urlopen(rssurl)).findAll("link"):
        if link.contents[0].startswith('http://www.cert.fi/haavoittuvuudet'):
            yield scrape_one_vuln(link.contents[0])


def scrape_one_vuln(url):
    soup = BS(urllib.urlopen(url), convertEntities="html")
    
    x = soup.find('h1', text=re.compile(r'CERT-FI haavoittuvuustiedote \d+/\d+'))
    if not x:
        return None
    
    vulnid = re.findall(r'(\d+/\d+)', x.string)[0]
    zdict = defaultdict(list)
    zdict["url"].append(url)
    for tr in soup.find("table", "userdefinedTable").findAll("tr"):
        try:
            za, zb, zc=tr.findAll('td')
        except ValueError:
            continue
        k = textify(za)[0].rstrip(':')
        for s in textify(zb):
            zdict[k].append(s.lstrip(u'- '))
    zdict['CVE ID'] += list(set(
            map(unicode, soup.findAll('a', text=re.compile(r'^CVE-')))))
    return u'CERT-FI ' + vulnid, zdict

if __name__ == '__main__':
    for z in scrape_rss():
        print z
