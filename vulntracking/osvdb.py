#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for OSVDB

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

import urllib, urlparse, re
from collections import defaultdict
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS

indexurl='http://osvdb.org/browse/by_reference_type/CVEID'
#indexurl='file:///tmp/osv_l.html'


def scrape():
    for link in BS(urllib.urlopen(indexurl)).find(
        "table", "browse_t").findAll("a"):
        if re.match(r'^\s*\d+\s*$', link.string):
            for r in scrape_one(urlparse.urljoin(indexurl, link['href'])):
                yield r

def textify(s):
    out = []
    for elt in s.contents:
        if isinstance(elt, basestring):
            s = unicode(elt).strip()
            if s:
                out.append(s)
        elif elt.tag == 'br':
            out.append(u'\n')
        else:
            out += textify(elt)
    return out


def scrape_one(url):
#    if 1: url = 'file:///tmp/osv_d.html'
    soup = BS(urllib.urlopen(url), convertEntities="html")
    vt = soup.find("table", "show_vuln_table")
    for h in vt.findAll("h1"):
        x = h.next
        while 1:
            if not isinstance(x, basestring) and x.get('class') == 'white_content':
                break
            x = x.next
        r = scrape_row(h.string, textify(x), url)
        if r:
            yield r

def scrape_row(h, s, url):
    # just use the references row for now
    if h != u'References':
        return None
    kvl = []
    d = []
    k = None
    for w in s:
        if w.endswith(':'):
            kvl.append((url, k, u' '.join(d)))
            k = w.rstrip(':')
            d = []
        else:
            d.append(w)
    del kvl[0]
    return kvl

if __name__ == '__main__':
    for z in scrape():
        print z
