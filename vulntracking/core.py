#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Scraper for Core security exploit feed

    @copyright: 2009 Erno Kuusela, Jussi Eronen
    @license: GPLv2
"""

from critismunge import format_time

import urllib, re, urlparse, time
from collections import defaultdict
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS
remoteurl='''http://www.coresecurity.com/content/core-impact-pro-security-updates'''

def scrape_mw(scrapeurl):
    if 1:
        f = urllib.urlopen(scrapeurl)
    else:
        f = open("/tmp/core.html")
    for div in BS(f, convertEntities="html").findAll(\
        attrs={'class': ['block']}):
        date = div.findAll('b')[0].contents[0]
        link = div.findAll('a')[0]
        descr = link.contents[0]
        URL = urlparse.urljoin("http://www.coresecurity.com", link['href'])
        data = urllib.urlopen(URL).read()
        cves = set([('CVE-' + x) for x in re.findall(r'(?i)cve\D{0,4}(\d+-\d+)', data)])

        zdict = defaultdict(list)
        zdict['CVE'].extend(cves)
        zdict['URL'] = URL
        zdict['Description'] = descr
        zdict['Date'] = format_time(date)
        zdict['Feed type'].append('Exploit')
        yield "Core-%s" % (link['href'].split('/')[-1]), zdict

if __name__ == '__main__':
    for z in scrape_mw(remoteurl):
        print z
