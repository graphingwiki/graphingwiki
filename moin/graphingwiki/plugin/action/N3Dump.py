# -*- coding: iso-8859-1 -*-
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

from MoinMoin import config
from MoinMoin.util import MoinMoinNoFooter

from graphingwiki.patterns import get_shelve

from savegraphdata import encode
from ShowGraph import nonguaranteeds_p, get_interwikilist, get_selfname
from ShowPaths import load_graph, add_global_links

def graph_to_format(pagegraph, pagename, selfname, formatfunc):
    out = ''
    nodegraph = pagegraph.nodes.get(pagename)

    for prop in nonguaranteeds_p(nodegraph):
        for value in getattr(nodegraph, prop):
            out = out + formatfunc(selfname,
                                   (pagename, prop, value))

    for edge in pagegraph.edges.getall():
        edgegraph = pagegraph.edges.get(*edge)
        linktype = getattr(edgegraph, 'linktype', 'Link')
        out = out + formatfunc(selfname,
                               (edge[0], linktype, edge[1]))

    return out

def graph_to_yield(pagegraph, pagename, formatfunc):
    if not pagegraph:
        return

    nodegraph = pagegraph.nodes.get(pagename)

    for prop in nonguaranteeds_p(nodegraph):
        for value in getattr(nodegraph, prop):
            for data in formatfunc((pagename, prop, value)):
                yield data
            

    for edge in pagegraph.edges.getall():
        edgegraph = pagegraph.edges.get(*edge)
        linktype = getattr(edgegraph, 'linktype', 'Link')
        for data in formatfunc((edge[0], linktype, edge[1])):
            yield data
        

def get_page_n3(request, pagename):
    pagegraph = load_graph(request, pagename)
    pagename = url_quote(encode(pagename))
    globaldata = get_shelve(request)
    pagegraph = add_global_links(request, pagename, pagegraph, globaldata)
    selfname = get_selfname(request)

    return graph_to_format(pagegraph, pagename, selfname, wikins_n3triplet)

def get_page_fact(request, pagename, globaldata):
    pagename = unicode(url_unquote(pagename), config.charset)
    pagegraph = load_graph(request, pagename)
    pagename = url_quote(encode(pagename))
    pagegraph = add_global_links(request, pagename, pagegraph, globaldata)

    for data in graph_to_yield(pagegraph, pagename, wikins_fact):
        yield data

def get_all_facts(request, globaldata):
    for pagename in request.rootpage.getPageList():
        pagegraph = load_graph(request, pagename)
        pagename = url_quote(encode(pagename))
        if not pagegraph:
            continue
        pagegraph = add_global_links(request, pagename, pagegraph, globaldata)

        for data in graph_to_yield(pagegraph, pagename, wikins_fact):
            yield data

def wikins_fact(triplet):
    out = []
    for prop, cond in zip(triplet, [True, False, True]):
        out.append(wikins_property("", prop, cond).strip('"'))
    yield out

def wikins_n3triplet(selfname, triplet):
    out = ''
    for prop, cond in zip(triplet, [True, False, True]):
        out = out + wikins_property(selfname + ":", prop, cond) + ' '
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

    for iw, iw_url in get_interwikilist(request).items():
        outstr = (outstr + '@prefix '+ iw + ': <' + 
                  iw_url + '> .' + "\n")

    for pagename in pages:
        outstr = outstr + unicode(get_page_n3(request, pagename),
                                  config.charset)

    return outstr
    
def execute(pagename, request):
    request.http_headers(["Content-type: text/plain;charset=%s" %
                          config.charset])

    n3 = n3dump(request, [pagename])

    request.write(n3)
    raise MoinMoinNoFooter
