#! /usr/bin/env python
# -*- coding: latin-1 -*-
"""
    Ad-hoc snippets for munging some vuln data (for a paper we did)

    @copyright: 2009 Erno Kuusela
    @license: GPLv2
"""
import csv, re
from collections import defaultdict

wikiurl = 'https://www.example.com/collab/yourcollab/'    



def metatable_csv_to_dict(f):
    z = csv.reader(f, delimiter=";")
    fieldnames = z.next()
    out = {}
    for row in z:
        rec = defaultdict(list)
        for k, v in zip(fieldnames, row):
            if v:
                rec[k].append(v)
        out[row[0]] = rec
    return out


def get_hosts_opencollab():
    from opencollab.wiki import CLIWiki

    w = CLIWiki(wikiurl)
    print 'call authenticate'
    w.authenticate()
    pages = w.getMeta('CategoryContainer, ||ipv4||gwikishapefile||tia-name||<gwikistyle="list"> ipv4->serves||ipv4->listens to||ipv4->OS||')
    print pages

from graphingwiki.editing import xmlrpc_error, xmlrpc_conninit, \
     xmlrpc_connect, getmeta_to_table, getuserpass
import os
import cPickle as pickle

def cached(fun, name):
    cachefn = 'cache/%s.pickle' % name
    if not os.path.exists(cachefn):
        r = fun()
        f = open(cachefn, 'w')
        pickle.dump(r, f, 2)
        f.close()
    return pickle.load(open(cachefn))

def get_hosts():
    username, password = getuserpass()
    w, _ = xmlrpc_conninit(wikiurl, username, password)
    result = xmlrpc_connect(w.GetMetaStruct, wikiurl, 'CategoryContainer, operating-system=/centos/')
    return result

def getmeta(arg):
    username, password = getuserpass()
    w, _ = xmlrpc_conninit(wikiurl, username, password)
    result = xmlrpc_connect(w.GetMetaStruct, wikiurl, arg)
    return result

def conninit():
    username, password = getuserpass()
    w, _ = xmlrpc_conninit(wikiurl, username, password)
    return w

def setmeta(w, page, arg):
    result = xmlrpc_connect(w.SetMeta, wikiurl, page, arg, "repl")
    return result

def mark_patch_status():
    d = parse_yum_logs()
    username, password = getuserpass()
    w, _ = xmlrpc_conninit(wikiurl, username, password)
    hosts = cached(get_hosts, 'critis-hosts')
    for h in hosts:
        try:
            name = hosts[h]['tia-name'][0]
        except (KeyError, IndexError):
            pass
        else:
            status = d.get(name, 'unknown')
        result = xmlrpc_connect(w.SetMeta, wikiurl, h, {"last-yum-update": [status]})
        print result


def upload_rhsa():
    username, password = getuserpass()
    w, _ = xmlrpc_conninit(wikiurl, username, password)
    rhsa_dict = pickle.load(open("rhsa.pickle"))
    for rhsa_id, rhsa_meta in rhsa_dict.items():
        del rhsa_meta['cves']
        rhsa_meta['cve-id'] = map(lambda x: '[['+x+']]', rhsa_meta['cve-id'])
        result = xmlrpc_connect(w.SetMeta, wikiurl, rhsa_id, dict(rhsa_meta))
        print result


def upload_rhsa_cves():
    rhsa_dict = pickle.load(open("rhsa.pickle"))
    wanted_cves = set()
    for rhsa_id, rhsa_meta in rhsa_dict.items():
        for cveid in rhsa_meta['cve-id']:
            wanted_cves.add(cveid)
    upload_cves(wanted_cves)

def mark_access_vector_rhsa():
    username, password = getuserpass()
    w, _ = xmlrpc_conninit(wikiurl, username, password)
    rhsa_dict = pickle.load(open("rhsa.pickle"))
    wanted_cves = set()
    cve_dict = pickle.load(open("nvd.pickle"))
    for rhsa_id, rhsa_meta in rhsa_dict.items():
        av=set()
        for cveid in rhsa_meta['cve-id']:
            map(av.add, cve_dict[cveid]['cvss-access-vector'])
            result = xmlrpc_connect(w.SetMeta, wikiurl, rhsa_id, {'cvss-access-vector': list(av)})

def mark_client_rhsa():
    username, password = getuserpass()
    w, _ = xmlrpc_conninit(wikiurl, username, password)
    print 'load'
    rhsa_dict = pickle.load(open("rhsa.pickle"))
    wanted_cves = set()
    cve_dict = pickle.load(open("nvd.pickle"))
    print 'loop'
    for rhsa_id, rhsa_meta in rhsa_dict.items():
        isclient='no'
        for cveid in rhsa_meta['cve-id']:
            for vs in cve_dict[cveid]['vulnerable-software']:
                if re.search(r'mozilla|xiph|xine|desktop|lynx|gstreamer', vs):
                    isclient='yes'
                else:
                    isclient='no'
        print rhsa_id, isclient
        result = xmlrpc_connect(w.SetMeta, wikiurl, rhsa_id,{'isclient': [isclient]})
                    

def upload_cves(wanted_cves):
    username, password = getuserpass()
    w, _ = xmlrpc_conninit(wikiurl, username, password)
    cve_dict = pickle.load(open("nvd.pickle"))
    for cve_id in wanted_cves:
        if cve_id not in cve_dict:
            print 'no cve', cve_id
            continue
        cve_meta = cve_dict[cve_id]
        cd = dict()
        for k, v in cve_meta.items():
            cd[k] = list(v)
        result = xmlrpc_connect(w.SetMeta, wikiurl, cve_id, cd)
        print 'did', cve_id
        print result


from time import strptime, mktime, strftime

def parse_yum_logs():
    # result of grepping 'yum: Updated' from logserver
    f = open("yum-updated-2009")
    d = {}
    for line in f:
        # skip entries from december of prev year
        if not line.startswith("Dec"):
            break

    for line in f:
        ts = strftime("%Y-%m-%d %H:%M:%S", strptime('2009 ' + line[:15], '%Y %b %d %H:%M:%S'))
        try:
            hostname, rest = line[16:].split(None, 1)
        except ValueError:
            print "bad line", repr(line)
            continue
        hostname = hostname.split('.')[0]
        if hostname not in d:
            d[hostname] = ts
        d[hostname] = max(ts, d[hostname])
    return d
                        
def installed_vs_advisories():
    rhsa_dict = pickle.load(open("rhsa.pickle"))
    adv_rpms = set()
    for rhsa_id in rhsa_dict:
        print rhsa_id
        for rpmfilename in rhsa_dict[rhsa_id]['update-rpm']:
            x = rpmfilename.split('.')
            assert x.pop() == 'rpm'
            if x.pop() not in ('x86_64', 'i386', 'noarch'):
                continue
            x = '.'.join(x).split('-')
            z = []
            while x and x[0] and not x[0][0].isdigit():
                z.append(x.pop(0))
            print z, x
            #version = re.search(r'(.*)-(\d[^-]*)', base)
            #print version
            

# installed rpm format:
# ssh $h 'grep -q CentOS /etc/redhat-release && rpm -qa --qf "%{name}-%{version}-%{release}.%{arch}\n"' > rpm-qa.$h

    
def runmunge():
    data = cached(get_hosts, 'critis-hosts')
    hosts_by_hostname = {}
    for metadict in data.values():
        print ''.join(metadict['tia-name']),
    print
    
