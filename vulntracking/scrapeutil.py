import urllib, urlparse, urllib2, cookielib
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup
from collections import defaultdict
import shelve
import re
import sys

class Surfer:
    timeout = 30
    def __init__(self, cachepath="./scrapesurfer.cache"):
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
            self.cache[url] = r.read(), r.info()['content-type']
        data, ctype = self.cache[url]
        if 'html' in ctype:
            soup = BeautifulSoup(data, convertEntities="html")
        else:
            soup = BeautifulStoneSoup(data, convertEntities="html")
        self.url = url
        return soup

class Bleat(Exception):
    pass


def normalize_cveid(cveid):
    cveid = cveid.strip()
    if cveid.startswith(u'[[') and cveid.endswith(u']]'):
        # strip these now, will be re-added later
        cveid = cveid[2:-2]
    if cveid[0].isdigit():
        cveid = 'CVE-' + cveid
    return cveid

def update_vulns(s, scrapeiter, scraperkey, cvekey="CVE ID",
                 template=None):
    """
    Update mapping s with (vuln-id, vulndata) pairs from scrapeiter,
    and make a link scraperkey: vuln-id on the CVE entry s[vulndata[CVE ID]]
    """

    def append_uniq(l, item):
        if item not in l:
            l.append(item)

    if not template:
        template = generic_vuln_template

    s[template[0]] = template[1]
    for vid, scrapedata in scrapeiter:
        scrapedata['gwikitemplate'].append(template[0])
        if cvekey in scrapedata:
            cvelist = map(normalize_cveid, scrapedata[cvekey])
            del scrapedata[cvekey]
            for cveid in cvelist:
                if not re.match(r'(CVE|CAN)-\d{4}-\d+', cveid):
                    # raise Bleat("malformed cveid %s" % repr(cveid))
                    print "malformed cveid %s in %s" % (repr(cveid), repr(vid))
                    continue

                cvedata = s.setdefault(str(cveid), defaultdict(list))

                vid_link = u"[[" + vid + u"]]"
                cve_link = u"[[" + cveid + u"]]"
                
                append_uniq(cvedata[scraperkey], vid_link)
                append_uniq(scrapedata["CVE ID"], cve_link)
                s[str(cveid)] = cvedata # shelve quirk

        s[str(vid)] = scrapedata

def score_all_cves(s):
    for vid in s.iterkeys():
        if not vid.startswith('CVE-'):
            continue
        score_cve(vid, s)

def score_cve(vid, s):
    scoretab = {
        'exploit-available': has_exploit,
        'remote-compromise': remote_compromise,
    }

def has_remote_compromise(cveid, s):
    pass

def has_exploit(cveid, s):
    # xxx check packetstorm, xforce, securityfocus
    return 'Milw0rm' in s[cveid] or 'MetaSploit' in s[cveid]

from hashlib import sha256
import struct

def hash_name(s):
    # truncate sha1 to 64 bits and convert to base-36 (a-z + 0-9)
    bytes = sha256(s).digest()[:8]
    n = struct.unpack('!Q', bytes)[0]
    return base36encode(n).zfill(13)

# from http://en.wikipedia.org/wiki/Base_36
def base36encode(number):
    if number < 0:
        raise ValueError('number must be positive')
 
    alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'
 
    base36 = ''
    while number:
        number, i = divmod(number, 36)
        base36 = alphabet[i] + base36
 
    return base36 or alphabet[0]

def textify(s):
    out = []
    for elt in s.contents:
        if isinstance(elt, basestring):
            s = unicode(elt).strip()
            if s:
                out.append(s)
        elif elt.name == 'br':
            out.append(u'\n')
        elif elt.name == 'b':
            out.append(None)
            out.append(elt.string)
        else:
            out += textify(elt)
    return out


generic_vuln_template = ("GenericVulnTemplate",u"""
= @PAGE@ =

 CVE ID::
 feedtype::

 Description::
 URL::

 
<<LinkedIn>>

----
CategoryVuln
""")

