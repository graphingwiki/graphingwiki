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
            yield u'OSVDB ' +link['href'].split(u'/')[-1], scrape_one(urlparse.urljoin(indexurl, link['href']))


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
    #url = 'file:///tmp/osv_d.html'
    soup = BS(urllib.urlopen(url), convertEntities="html")
    vt = soup.find("table", "show_vuln_table")
    zdict = defaultdict(list)
    for h in vt.findAll("h1"):
        x = h.next
        while 1:
            if not isinstance(x, basestring) and x.get('class') == 'white_content':
                break
            x = x.next
        for k, v in scrape_row(unicode(h.string), map(unicode, textify(x)), unicode(url)):
            if not k.startswith('u(see also'):
                # Skip NVD links
                if not v.startswith('NVD'):
                    zdict[k].append(v)
    zdict['Feed type'].append('Vulnerability')
    return zdict

def scrape_row(h, s, url):
    # just use the references row for now
    if h != u'References':
        return
    d = []
    k = None

    bad = u'(see also'
    while bad in s:
        i = s.index(bad)
        del s[i:i+3]

    for w in s:
        if w.endswith(':'):
            if k:
                #print 'yield', k, repr(u' '.join(d))
                if k == 'CVE':
                    d = ["CVE-%s" % x for x in d]
                yield k, u' '.join(d)
            k = w.rstrip(':')
            d = []
        else:
            d.append(w)

if __name__ == '__main__':
    for z in scrape():
        print repr(z)
