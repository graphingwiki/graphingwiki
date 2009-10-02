"""
#! /usr/bin/env python
# -*- coding: latin-1 -*-
    Scraper for CVE vuln feed

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

from lxml import objectify
from collections import defaultdict
import shelve
 
def parse_nvd_data(fob, shelf):
    objectify.enable_recursive_str()
    tree = objectify.parse(fob)
    e = tree.getroot().entry
    do_nvd_entry(e, shelf)
    while 1:
        e = e.getnext()
        if e is None:
            break
        cveid, zdict = do_nvd_entry(e, shelf)
        print cveid
        shelf[cveid] = zdict
            

def do_nvd_entry(e, shelf):
    m = defaultdict(list)
    m['feedsource'].append('nvd')
    #m['feedtype'].append('?')
    cveid = e.get('id')

    for s in 'published-datetime', 'last-modified-datetime', 'security-protection', 'summary', 'severity':
        try:
            x = e['{http://scap.nist.gov/schema/vulnerability/0.4}' + s]
            m[s].append(unicode(x))
            #print s, x.encode('ascii', 'replace')
        except AttributeError:
            pass

    try:
        vs = e['{http://scap.nist.gov/schema/vulnerability/0.4}vulnerable-software-list']
    except AttributeError:
        vs = []
    for s in vs:
        #print 'vulnerable-software', s['{http://scap.nist.gov/schema/vulnerability/0.4}product']
        m['vulnerable-software'].append(unicode(s['{http://scap.nist.gov/schema/vulnerability/0.4}product']))
                   

    try:
        refs = e['{http://scap.nist.gov/schema/vulnerability/0.4}references']
    except AttributeError:
        refs = []

    for r in refs:
        #print 'ref',
        #print r['{http://scap.nist.gov/schema/vulnerability/0.4}source'],
        #print r['{http://scap.nist.gov/schema/vulnerability/0.4}reference'].get('href')
        m['reference'].append(unicode(r['{http://scap.nist.gov/schema/vulnerability/0.4}source']) + u' ' + unicode(r['{http://scap.nist.gov/schema/vulnerability/0.4}reference'].get('href')))
    
    metric = lambda x: e['{http://scap.nist.gov/schema/vulnerability/0.4}cvss']['{http://scap.nist.gov/schema/cvss-v2/0.2}base_metrics']['{http://scap.nist.gov/schema/cvss-v2/0.2}' + x]
    
    for mn in 'score', 'access-vector', 'access-complexity', 'availability-impact', 'confidentiality-impact', 'integrity-impact':
        try:
            z =  metric(mn)
            #print 'cvss-'+mn, z
        except AttributeError:
            pass
        else:
            m['cvss-' + mn].append(unicode(z))

    try:
        cweid = e['{http://scap.nist.gov/schema/vulnerability/0.4}cwe'].get("id")
    except AttributeError:
        pass
    else:
        if cweid:
            m["cwe-id"].append(cweid)
    return cveid, m

def main():
    s = shelve.open("parsednvd.shelve")
    parse_nvd_data(open('nvdcve-2.0-2009.xml'), s)
    s.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "Script interrupted via CTRL-C."

