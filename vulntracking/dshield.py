#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for dshield top10 feed

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""
import urllib2
from collections import defaultdict
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS
top10url='http://www.dshield.org/top10.html'

def scrape():
    for table, tblname in zip(BS(urllib2.urlopen(top10url)).findAll("table", "datatable")[:3], ['reports', 'targets', 'sources']):
        for tr in table.findAll('tr')[1:]:
            tds = tr.findAll('td')
            port, count = (unicode(tds[0].find('a').string),
                           unicode(tds[1].string))

            zdict = defaultdict(list)
            zdict['dshield-top10-' + tblname + '-count'] = count
            zdict['port'] = port
            yield u'port-' + port, zdict

if __name__ == '__main__':
    for z in scrape():
        print z
