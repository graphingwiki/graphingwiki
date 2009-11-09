#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Screen scraper for Red Hat security advisories

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""
from critismunge import format_time

import BeautifulSoup
from BeautifulSoup import BeautifulSoup as BS
import urllib, urlparse, os, re
import cPickle as pickle
from pprint import pprint
import collections
import scrapeutil

def adv_id_to_url(adv_id):
    return "http://rhn.redhat.com/errata/%s.html" % adv_id.replace(':', '-')

def towiki(soup):
    # attempt to wikify soup
    out = u' '
    for elt in list(soup):
        if isinstance(elt, BeautifulSoup.NavigableString):
            out += unicode(elt).replace(u"\n", u" ") + u' '
        elif elt.name == 'a' and elt.has_key('href'):
            out += '[[%s|%s]]' % (elt["href"], towiki(elt.contents).strip()) + u' '
        else:
#             if elt.name in ('p', 'br'):
#                 out += u"\n"
            out += towiki(elt.contents)
    return out.strip()

def absolutify_urls(soup, baseurl):
    for a_tag in soup.findAll("a"):
        if a_tag.has_key("href"):
            a_tag["href"] = urlparse.urljoin(baseurl, a_tag["href"])
            
errata_baseurl = "http://rhn.redhat.com/errata/"
def scrapeit(save=False, cachedir="./rhsa_cache"):
    startfn ='rhel-server-errata-security.html'
    s = BS(urllib.urlopen(errata_baseurl + startfn))
    absolutify_urls(s, errata_baseurl + startfn)
    tehdict = collections.defaultdict(list)
    if not os.path.isdir(cachedir):
        os.mkdir(cachedir)
    adv_ids = set(
        map(unicode, s.findAll(text=re.compile(r'^RHSA-\d.*'))))
    for adv_id in sorted(adv_ids):
        adv_url = adv_id_to_url(adv_id)
        cachefn=os.path.join(cachedir, adv_url.split('/')[-1])
        if not os.path.exists(cachefn):
            print 'cache miss', cachefn
            f = open(cachefn, 'w')
            f.write(urllib.urlopen(adv_url).read())
            f.close()

        s2 = BS(open(cachefn))
        absolutify_urls(s2, errata_baseurl + cachefn)
        d = collections.defaultdict(list)
        d['CVE ID'] = sorted(set(
                map(unicode, s2.findAll(text=re.compile(r'^CVE-\d')))))

        d['Feed type'].append('Vulnerability')

        # try to find updates for rhel 5
#         [x.parent for x in s.findAll(text=re.compile("Red.*v. 5.*server\)"))
#          if not x.parent.has_key("href")]
                                     
        d['update-rpm'] = sorted(set(
                map(unicode, s2.findAll(text=re.compile(r'.*\.rpm')))))

        if not d['update-rpm']:
            continue

        t = s2.find('table', 'details')
        for th in t.findAll('th'):
            metakey = towiki(th).split()[0].rstrip(':').lower().replace(' ', '-')
            if metakey == 'cves':
                continue
            d[metakey].append(format_time(towiki(th.parent.find("td"))))

        d['rhsa-url'].append(adv_url)
        d['gwikicategory'].append('CategoryRhsa')
        yield d['advisory'][0], d

    if save:
        f = open('rhsa.pickle', 'w')
        pickle.dump(tehdict, f, 2)
        f.close()

def update_vulns(s):
    return scrapeutil.update_vulns(s, scrapeit(True), 'RHSA')
            

if __name__ == '__main__':
    from pprint import pprint
    for z in scrapeit():
        pprint(z)
