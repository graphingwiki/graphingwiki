import urllib, urlparse, urllib2, cookielib
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup
import shelve

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
