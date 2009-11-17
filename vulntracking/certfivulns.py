#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for CERT-FI vuln feed

    @copyright: 2009 Erno Kuusela, Sauli Pahlman
    @license: GPLv2
"""
import urllib, re, urlparse
from collections import defaultdict
from osvdb import textify
from BeautifulSoup import BeautifulStoneSoup as BSS, BeautifulSoup as BS
import scrapeutil
import time

rssurl='''http://www.cert.fi/rss/haavoittuvuudet.xml'''

def scrape_rss():
    surfer = scrapeutil.Surfer()
    for link in surfer.gourl(rssurl).findAll("link"):
        if link.contents[0].startswith('http://www.cert.fi/haavoittuvuudet'):
            yield scrape_one_vuln(surfer.gourl(link.contents[0]), link.contents[0])

def scrape_urlwalk():
    surfer = scrapeutil.Surfer()
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
            r = scrape_one_vuln(surfer.gourl(url), url)
            if r is not None:
                yield r
            
def scrape_one_vuln(soup, url):
    zdict = defaultdict(list)

    x = soup.find('h1', text=re.compile(r'CERT-FI haavoittuvuustiedote \d+/\d+'))
    if not x:
        return None
    vulnid = re.findall(r'(\d+/\d+)', x.string)[0]

    x = soup.find("p", "pvm")
    if x:
        isodate = time.strftime("%Y-%m-%d", time.strptime(x.string, '%d.%m.%Y'))
        zdict["published"].append(isodate)
        
    zdict["url"].append(unicode(url))
    tbl = soup.find("table", "userdefinedTable")
    if not tbl:
        print "table not found in", url
        return None
    for tr in tbl.findAll("tr"):
        try:
            za, zb, zc=tr.findAll('td')
        except ValueError:
            continue
        k = textify(za)[0].rstrip(':')
        for s in textify(zb):
            zdict[k].append(unicode(s.lstrip(u'- ')))
    zdict['CVE ID'] += list(set(
            map(lambda x: unicode(x),
                soup.findAll('a', text=re.compile(r'^CVE-')))))
    zdict['Feed type'].append('Vulnerability')
    return u'CERT-FI ' + vulnid.replace('/', '-'), zdict

def update_vulns(s):
    return scrapeutil.update_vulns(s, scrape_urlwalk(), 'CERT-FI',
                                   template=wiki_template)
            
wiki_template=("CertFiVulnTemplate", u"""
= @PAGE@ =

 CVE ID::
 Feed type::
 published::
 url:: 

 Kohde:
 Hyväksikäyttö
 Ratkaisu::
 Hyökkäystapa::


<<LinkedIn>>

----
CategoryVuln
CategoryCertFiVuln
""")

if __name__ == '__main__':
    for z in scrape_rss():
        print z
