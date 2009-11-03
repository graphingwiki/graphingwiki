"""
Vulntracking utils
"""

import urllib, urlparse, urllib2, cookielib
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup
import logging
import shelve
import tempfile

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

def main():
    s = shelve.open("vulns.shelve", "c", protocol=2)

    if 1:
        import nvd
        nvd.parse_nvd_data(open('nvdcve-2.0-2009.xml'), s)

        import certfivulns
        certfivulns.update_vulns(s)

        import emergingthreats
        emergingthreats.update_vulns(s)

        import metasploitsvn
        metasploitsvn.update_vulns(s)

    s.close()

if __name__ == "__main__":
    main()

