#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from xml.parsers import expat
from pprint import pprint

from MoinMoin.wikiutil import quoteWikinameFS, unquoteWikiname

from graphingwiki.graph import Graph
from graphingwiki.util import encode

class Parser:

    def __init__(self):
        self._parser = expat.ParserCreate()
        self._parser.StartElementHandler = self.start
        self._parser.EndElementHandler = self.end
        self.hier = {}
        self.stack = []
        self.graph = Graph()

        self.idnamemap = {}
        self.nameidmap = {}
        self.glinks = {}

    def feed(self, data):
        self._parser.Parse(data, 0)

    def close(self):
        self._parser.Parse("", 1) # end of data
        del self._parser # get rid of circular references

    def start(self, tag, attrs):
        if tag == 'arrowlink':
            self.glinks.setdefault(self.idnamemap[self.stack[-1]],
                                   []).append(attrs['DESTINATION'])
        elif tag != 'node':
            return

        # strip enters, they screw up Moin
        ndname = attrs.get('TEXT', '').replace('\n', ' ')
        if ndname:
            self.idnamemap[ndname] = attrs['ID']
            self.nameidmap[attrs['ID']] = ndname

            if not self.graph.nodes.get(ndname):
                self.graph.nodes.add(ndname)
            self.hier.setdefault(ndname, [])
            if len(self.stack):
                self.hier[self.stack[-1]].append(ndname)
                self.graph.edges.add(self.stack[-1], ndname)
            self.stack.append(ndname)
#        print "START", repr(tag), attrs

    def end(self, tag):
        if tag != 'node':
            return

        if len(self.stack):
            del self.stack[-1]
#        print "END", repr(tag)

p = Parser()
p.feed(sys.stdin.read())
p.close()
#pprint(p.hier)

basedir = os.path.join(sys.argv[1], 'data/pages')

cat = ""
if len(sys.argv) > 2:
    cat = sys.argv[2]

for start in p.glinks:
    for end in p.glinks[start]:
        p.graph.edges.add(p.nameidmap[start],
                          p.nameidmap[end])


for node, in p.graph.nodes:
    nodedir = os.path.join(basedir, quoteWikinameFS(node))
    curf = os.path.join(nodedir, 'current')
    nro = 1
    revdir = os.path.join(nodedir, 'revisions')
    if not os.path.exists(nodedir):
        os.mkdir(nodedir)
    if not os.path.exists(revdir):
        os.mkdir(revdir)
    if os.path.exists(curf):
        nro = int(file(curf).read()[:-1]) + 1
        os.unlink(curf)
    curver = "%08d" % nro
    file(curf, 'w').write(curver + '\n')
    out = file(os.path.join(revdir, curver), 'w')    

    for par, chi in p.graph.edges:
        if not par == node:
            continue
        out.write('["%s"]\n\n' % encode(chi))

    if cat:
        out.write('%s\n' % cat)

    out.close()

#print p.glinks
