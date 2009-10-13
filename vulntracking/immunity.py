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
remoteurl='''http://www.immunitysec.com/news-latest.shtml'''

def textify(s):
    out = []
    for elt in s.contents:
        if isinstance(elt, basestring):
            s = unicode(elt).strip()
            if s:
                out.append(s)
        elif elt.name == 'br':
            out.append(u'\n')
        elif elt.name == 'b':
            out.append(None)
            out.append(elt.string)
        else:
            out += textify(elt)
    return out

def scrape_mw(scrapeurl):
    if 1:
        f = urllib.urlopen(scrapeurl)
    else:
        f = open("/tmp/immunity.html")

    data = BS(f, convertEntities="html")

    current = []
    date_next = False
    zdict = defaultdict(list)

    for text in textify(data):
        if text == None:
            if zdict['Date']:
                if zdict['CVE']:
                    yield "Immunity-%s" % (zdict['Date'].split()[0]), zdict

            zdict = defaultdict(list)
            zdict['Feed type'].append('Exploit')
            date_next = True
        elif date_next:
            zdict['Date'] = format_time(text)
            date_next = False
        else:
            zdict['CVE'].extend(x for x in 
                                re.findall(r'(?i)(CVE-\D{0,4}\d+-\d+)', text))
            zdict['MS'].extend(x.replace('_', '-') for x in 
                               re.findall(r'(?i)(MS\D{0,4}\d+[-_]\d+)', text))

if __name__ == '__main__':
    for z in scrape_mw(remoteurl):
        print z
