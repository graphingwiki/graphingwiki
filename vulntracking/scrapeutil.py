import urllib, urlparse, urllib2, cookielib
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup
from collections import defaultdict
import shelve
import re
import sys

class Surfer:
    timeout = 30
    def __init__(self, cachepath=None):
        if cachepath:
            self.cache = shelve.open(cachepath, 'c')
        else:
            self.cache = {}
        self.cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self.cookies))
        self.url = None

    def gourl(self, *urlparts, **postparams):
        if len(urlparts)> 1:
            url = urlparse.urljoin(*urlparts)
        else:
            url = urlparts[0]
        url = str(url) # catch unicode and BS NavigableStrings
        if url not in self.cache:
            r = self.opener.open(url,
                      urllib.urlencode(postparams) if postparams else None,
                      self.timeout)
            if 'html' in r.info()['content-type']:
                self.cache[url] = BeautifulSoup(r, convertEntities="html")
            else:
                self.cache[url] = BeautifulStoneSoup(r, convertEntities="html")
        self.url = url
        return self.cache[url]

class Bleat(Exception):
    pass

def update_vulns(s, scrapeiter, keyname, cvekey=None):
    """
    Update mapping s with (vuln-id, vulndata) pairs from scrapeiter,
    and make a link keyname: vuln-id on the CVE entry s[vulndata[CVE ID]]
    """
    for vid, data in scrapeiter:
        s[str(vid)] = data
        if cvekey and cvekey in data:
            data['CVE ID'] = data[cvekey]
            del data[cvekey]
            
        for cveid in map(str, data.get('CVE ID', [])):
            if cveid and cveid[0].isdigit():
                cveid = 'CVE-' + cveid

            if not re.match(r'(CVE|CAN)-\d{4}-\d+', cveid):
                raise Bleat("malformed cveid %s" % cveid)

            if cveid not in s:
                d = defaultdict(list)
            else:
                d = s[cveid]
            d[keyname].append(u"[[" + vid + u"]]")
            s[cveid] = d
            
