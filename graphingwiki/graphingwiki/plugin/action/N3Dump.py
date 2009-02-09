# -*- coding: utf-8 -*-"
"""
    N3Dump action plugin to MoinMoin
     - Dumps dumps the semantic data on pages in Notation 3

    @copyright: 2006 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""

import shelve
from urllib import quote as url_quote
from urllib import unquote as url_unquote
from MoinMoin.wikiutil import load_wikimap

from MoinMoin import config

from graphingwiki.util import nonguaranteeds_p, get_selfname

def graph_to_format(pagegraph, pagename, selfname, formatfunc):
    out = ''
    nodegraph = pagegraph.nodes.get(pagename)

    for prop in nonguaranteeds_p(nodegraph):
        for value in getattr(nodegraph, prop):
            if not isinstance(prop, unicode):
                prop = unicode(prop, config.charset)
            if not isinstance(value, unicode):
                value = unicode(value, config.charset)
            out = out + formatfunc(selfname,
                                   (pagename, prop, value))

    for edge in pagegraph.edges:
        edgegraph = pagegraph.edges.get(*edge)
        for linktype in getattr(edgegraph, 'linktype', 'Link'):
            if not isinstance(linktype, unicode):
                linktype = unicode(linktype, config.charset)
            if not isinstance(edge[1], unicode):
                dst = unicode(edge[1], config.charset)
            else:
                dst = edge[1]
            out = out + formatfunc(selfname,
                                   (edge[0], linktype, dst))

    return out

def graph_to_yield(pagegraph, pagename, formatfunc):
    if not pagegraph:
        return

    nodegraph = pagegraph.nodes.get(pagename)
    if not nodegraph:
        return

    for prop in nonguaranteeds_p(nodegraph):
        for value in getattr(nodegraph, prop):
            for data in formatfunc((pagename, prop, value)):
                yield data

    for edge in pagegraph.edges:
        edgegraph = pagegraph.edges.get(*edge)
        linktype = getattr(edgegraph, 'linktype', 'Link')
        for data in formatfunc((edge[0], linktype, edge[1])):
            yield data

def get_page_n3(request, pagename):
    pagegraph = request.graphdata.load_graph(pagename, '')
    selfname = get_selfname(request)

    return graph_to_format(pagegraph, pagename, selfname, wikins_n3triplet)

def get_page_fact(request, pagename, graphdata):
    pagegraph = graphdata.load_graph(pagename, '')
    if isinstance(pagename, unicode):
        pagename = unicode(url_quote(pagename), config.charset)

    for data in graph_to_yield(pagegraph, pagename, wikins_fact):
        yield data, pagename

def get_all_facts(request, graphdata):
    # We do not want underlay pages
    if hasattr(request.cfg, 'data_underlay_dir'):
        tmp = request.cfg.data_underlay_dir
        request.cfg.data_underlay_dir = None

    for pagename in request.rootpage.getPageList():
        pagegraph = graphdata.load_graph(pagename, '')
        if isinstance(pagename, unicode):
            pagename = unicode(url_quote(pagename), config.charset)

        for data in graph_to_yield(pagegraph, pagename, wikins_fact):
            yield data, pagename

    request.cfg.data_underlay_dir = tmp

def wikins_fact(triplet):
    out = []
    for prop, cond in zip(triplet, [True, False, True]):
        out.append(wikins_property("", prop, cond).strip('"'))
    yield out

def wikins_n3triplet(selfname, triplet):
    out = ''
    for prop, cond in zip(triplet, [True, False, True]):
        if isinstance(prop, basestring):
            # meta
            out = out + wikins_property(selfname + ":", prop, cond) + ' '
        else:
            # You can have multiple link types
            for val in prop:
                out = out + wikins_property(selfname + ":", val, cond) + ' '
    return out + '.\n'

def wikins_property(selfname, property, page):
    # Literal
    if property.startswith('"'):
        return property
    # A ready interwikiname
    if ':' in property:
        return property
    # Self
    if page:
        return selfname + property
    else:
        return selfname + 'Property' + property

def n3dump(request, pages):
    # Default namespace definitons, needed?
    outstr = u"""@prefix log: <http://www.w3.org/2000/10/swap/log#> .
@prefix math: <http://www.w3.org/2000/10/swap/math#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
"""

    for iw, iw_url in load_wikimap(request).items():
        outstr = (outstr + '@prefix '+ iw + ': <' + 
                  iw_url + '> .' + "\n")

    for pagename in pages:
        outstr = outstr + get_page_n3(request, pagename)

    return outstr
    
def execute(pagename, request):
    request.emit_http_headers(["Content-type: text/plain;charset=%s" %
                               config.charset])

    n3 = n3dump(request, [pagename])

    request.write(n3)
