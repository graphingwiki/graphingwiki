#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for milw0rm exploit feed

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

from critismunge import format_time

import urllib, re, urlparse, time
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
        zdict = defaultdict(list)
        zdict['CVE'].extend(cves)
        zdict['URL'] = urlparse.urljoin("http://www.milw0rm.com", link)
        zdict['Description'] = descr
        zdict['Date'] = format_time(date)
        zdict['Feed type'].append('Exploit')
        yield "Milw0rm-%s" % (link.split('/')[-1]), zdict


def update_vulns(s):
    from itertools import chain
    for vid, data in chain(scrape_mw(remoteurl),
                           scrape_mw(remoteurl + '?start=30')):
        s[str(vid)] = data
        for cveid in map(str, data.get('CVE', [])):
            if cveid not in s:
                d = defaultdict(list)
            else:
                d = s[cveid]
            d['Milw0rm'].append(u"[[" + vid + u"]]")
            s[cveid] = d
            

if __name__ == '__main__':
#     scrape_mw(localurl)
#     scrape_mw(localurl + '?start=30')
    for z in scrape_mw(remoteurl):
    #for z in scrape_mw(remoteurl + '?start=60'):
        print z
