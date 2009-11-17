#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for CERT-FI CVEs

    @copyright: 2009 Sauli Pahlman
    @license: GPLv2
"""

import urllib, re, urlparse
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS

def scrape():
#if __name__ == '__main__':
    for year in range(2001, 2010):
        temp_count = 0
        url = 'http://www.cert.fi/haavoittuvuudet/%d.html' % (year)
        data = urllib.urlopen(url).read()
        year_links = re.findall(r'/haavoittuvuudet.*\.html', data)
        url = 'http://www.cert.fi/varoitukset/%d.html' % (year)
        data = urllib.urlopen(url).read()
        year_links.extend(re.findall(r'/varoitukset.*\.html', data))
        for i in range(len(year_links)):
            if str(year) not in year_links[i]:
                continue
            url = urlparse.urljoin('http://www.cert.fi', year_links[i])
            urldata = urllib.urlopen(url)
            print url
            cves = set([('CVE-' + x) for x in re.findall(r'(?i)cve\D{0,4}(\d+-\d+)', urldata.read())])
            temp_count += len(cves)
            yield cves, year

if __name__ == '__main__':
    for z in scrape():
        print z
