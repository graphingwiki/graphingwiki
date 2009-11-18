#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Scraper for Immunity exploits

    @copyright: 2009 Erno Kuusela, Jussi Eronen
    @license: GPLv2
"""

from critismunge import format_time
import scrapeutil
import urllib, re, urlparse, time
from collections import defaultdict
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS
remoteurl='''http://www.immunitysec.com/news-latest.shtml'''

def scrape(scrapeurl):
    if 1:
        f = urllib.urlopen(scrapeurl)
    else:
        f = open("/tmp/immunity.html")

    data = BS(f, convertEntities="html")

    current = []
    date_next = False
    zdict = defaultdict(list)

    for text in scrapeutil.textify(data):
        if text == None:
            if zdict['Date']:
                if zdict['CVE ID']:
                    yield "Immunity-%s" % (zdict['Date'][0].split()[0]), zdict

            zdict = defaultdict(list)
            zdict['Feed type'].append('Exploit')
            date_next = True
        elif date_next:
            zdict['Date'].append(format_time(text))
            date_next = False
        else:
            zdict['CVE ID'].extend(x for x in 
                                re.findall(r'(?i)(CVE-\D{0,4}\d+-\d+)', text))
            zdict['MS'].extend(x.replace('_', '-') for x in 
                               re.findall(r'(?i)(MS\D{0,4}\d+[-_]\d+)', text))


def update_vulns(s):
    scrapeutil.update_vulns(s, scrape(remoteurl), 'ImmunitySec')

if __name__ == '__main__':
    for z in scrape(remoteurl):
        print z
