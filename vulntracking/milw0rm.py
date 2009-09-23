#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for milw0rm exploit feed
    TBD: check for CVE IDs in exploit files

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

import urllib, re, urlparse
from collections import defaultdict
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS
remoteurl='''http://www.milw0rm.com/remote.php'''
localurl='''http://www.milw0rm.com/local.php'''


def scrape_mw(scrapeurl):
    if 1:
        f = urllib.urlopen(scrapeurl)
    else:
        f = open("/tmp/mw.html")
    for tr in BS(f, convertEntities="html").findAll("tr", "submit"):
        cols = tr.findAll('td')
        if len(cols) < 2:
            continue
        date = unicode(cols[0].contents[0])
        descr = unicode(cols[1].contents[0].string)
        link = unicode(cols[1].contents[0]['href'])
        if '/exploits/' not in link:
            continue
        data = urllib.urlopen(urlparse.urljoin(remoteurl, link)).read()
        cves = set([('CVE-' + x) for x in re.findall(r'(?i)cve\D{0,4}(\d+-\d+)', data)])
        yield date, cves, descr, link


if __name__ == '__main__':
#     scrape_mw(localurl)
#     scrape_mw(localurl + '?start=30')
    #scrape_mw(remoteurl)
    for z in scrape_mw(remoteurl + '?start=60'):
        print z
