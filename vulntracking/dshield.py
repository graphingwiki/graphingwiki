#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for dshield top10 feed

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""
import urllib
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS
top10url='http://www.dshield.org/top10.html'

def scrape():
    ll=[]
    for table in BS(urllib.urlopen(top10url)).findAll("table", "datatable")[:3]:
        l=[]
        for tr in table.findAll('tr')[1:]:
            tds = tr.findAll('td')
            l.append((unicode(tds[0].find('a').string), unicode(tds[1].string)))
        if l:
            ll.append(l)
    return zip(['reports', 'targets', 'sources'], ll)

if __name__ == '__main__':
    for tblname, tbl in scrape():
        print tblname
        for row in tbl:
            print row[0], row[1]

