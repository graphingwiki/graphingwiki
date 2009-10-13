#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Scraper for CVE vuln feed

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""

import xml.etree.cElementTree as ET
from collections import defaultdict
import shelve

def gen_text(obj):
    return obj.text.replace('\n', '').replace('\t', '').replace('\r', '')

def parse_nvd_data(fob, shelf):
    tree = ET.parse(fob)
    for entry in tree.getroot().getchildren():
        cveid, zdict = do_nvd_entry(entry, shelf)
        print cveid
        shelf[cveid] = zdict
            
def do_nvd_entry(e, shelf):
    m = defaultdict(list)
    m['feedsource'].append('nvd')
    m['feedtype'].append('Vulnerability')
    cveid = e.get('id')

    for s in 'published-datetime', 'last-modified-datetime', 'security-protection', 'summary', 'severity':
        try:
            x = e.find('{http://scap.nist.gov/schema/vulnerability/0.4}' + s)
            m[s].append(gen_text(x))
            #print s, x.encode('ascii', 'replace')
        except AttributeError:
            pass

    try:
        vs = e.find'{http://scap.nist.gov/schema/vulnerability/0.4}vulnerable-software-list')
        if not vs:
            vs = []
    except AttributeError:
        vs = []
    for s in vs:
        #print 'vulnerable-software', s['{http://scap.nist.gov/schema/vulnerability/0.4}product']
        m['vulnerable-software'].append(gen_text(s))
                   

    try:
        refs = e.findall('{http://scap.nist.gov/schema/vulnerability/0.4}references')
    except AttributeError:
        refs = []

    for r in refs:
        #print 'ref',
        #print r['{http://scap.nist.gov/schema/vulnerability/0.4}source'],
        #print r['{http://scap.nist.gov/schema/vulnerability/0.4}reference'].get('href')
        m['reference'].append(gen_text(r[0]), r[1].get('href'))
    
    metric = lambda x: e.find('{http://scap.nist.gov/schema/vulnerability/0.4}cvss').find('{http://scap.nist.gov/schema/cvss-v2/0.2}base_metrics').find('{http://scap.nist.gov/schema/cvss-v2/0.2}' + x)
    
    for mn in 'score', 'access-vector', 'access-complexity', 'availability-impact', 'confidentiality-impact', 'integrity-impact':
        try:
            z =  metric(mn)
            #print 'cvss-'+mn, z
        except AttributeError:
            pass
        else:
            m['cvss-' + mn].append(gen_text(z))

    try:
        cweid = e.find('{http://scap.nist.gov/schema/vulnerability/0.4}cwe').get("id")
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

