#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for VUPEN exploit feed

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

exploits_rss_url='http://www.vupen.com/exploits.xml'
import urllib, re, urlparse
from collections import defaultdict
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS

def scrape_rss():
    for link in BSS(urllib.urlopen(exploits_rss_url)).findAll("link"):
        if u'/exploits/' in link.contents[0]:
            x = scrape_one(urlparse.urljoin(exploits_rss_url, link.contents[0]))
            if x:
                yield x

def scrape_one(url):
    soup = BS(urllib.urlopen(url), convertEntities="html")
    for f in soup.findAll('font', text=re.compile(r'^CVE-\d')):
        zdict = defaultdict(list)
        zdict[u'url'].append(url)
        zdict[u'CVE ID'].append(unicode(f.string))
        zdict[u'Feed type'].append('Exploit')
        return u'VUPEN-' +\
            url.split(u'/')[-1].replace(u'.php', '').split('_')[-1], zdict

if __name__ == '__main__':
    #print scrape_one("file:///tmp/tt.html")
    for z in scrape_rss():
        print z
