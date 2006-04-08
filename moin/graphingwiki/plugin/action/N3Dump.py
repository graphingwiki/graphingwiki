import os
import cPickle
import shelve
from urllib import quote as url_quote
from urllib import unquote as url_unquote

from MoinMoin import config
from MoinMoin.Page import Page
from MoinMoin.util import MoinMoinNoFooter

from savegraphdata import encode
from ShowGraph import nonguaranteeds_p, get_interwikilist, get_selfname

def load_graph(request, pagename):
    if not request.user.may.read(pagename):
        return None

    pageobj = Page(request, pagename)
    pagedir = pageobj.getPagePath()
    afn = os.path.join(pagedir, 'graphdata.pickle')
    if os.path.exists(afn):
        af = file(afn)
        adata = cPickle.load(af)
        return adata
    return None

def add_global_links(request, pagename, graph):
    inlist, outlist = set([]), set([])

    datapath = Page(request, u'', is_rootpage=1).getPagePath()
    graphshelve = os.path.join(datapath, 'pages/graphdata.shelve')
    # Make sure nobody is writing to graphshelve, as concurrent
    # reading and writing can result in erroneous data
    graphlock = graphshelve + '.lock'
    os.spawnlp(os.P_WAIT, 'lockfile', 'lockfile', graphlock)
    os.unlink(graphlock)

    globaldata = shelve.open(graphshelve, 'r')
    if globaldata['in'].has_key(pagename):
        inlist = globaldata['in'][pagename]
    if globaldata['out'].has_key(pagename):
        outlist = globaldata['out'][pagename]
    globaldata.close()

    for page in inlist:
        newdata = load_graph(request,
                             unicode(url_unquote(page), config.charset))
        if not newdata:
            continue
        for parent, child in newdata.edges.getall(child=pagename):
            newnode = graph.nodes.get(parent)
            if not newnode:
                newnode = graph.nodes.add(parent)
            newnode.update(newdata.nodes.get(parent))
            newedge = graph.edges.add(parent, child)
            newedge.update(newdata.edges.get(parent, child))
    for page in outlist:
        newdata = load_graph(request,
                             unicode(url_unquote(page), config.charset))
        if not newdata:
            continue
        for parent, child in newdata.edges.getall(parent=pagename):
            newnode = graph.nodes.get(child)
            if not newnode:
                newnode = graph.nodes.add(child)
            newnode.update(newdata.nodes.get(child))
            newedge = graph.edges.add(parent, child)
            newedge.update(newdata.edges.get(parent, child))

    return graph

def graph_to_n3(pagegraph, pagename, selfname):
    out = ''
    nodegraph = pagegraph.nodes.get(pagename)

    for prop in nonguaranteeds_p(nodegraph):
        for value in getattr(nodegraph, prop):
            out = out + wikins_triplet(selfname,
                                       (pagename, prop, value)) + '.\n'

    for edge in pagegraph.edges.getall():
        edgegraph = pagegraph.edges.get(*edge)
        linktype = getattr(edgegraph, 'linktype', 'Link')
        out = out + wikins_triplet(selfname,
                                   (edge[0], linktype, edge[1])) + '.\n'

    return out

def get_page_n3(request, pagename):
    pagegraph = load_graph(request, pagename)
    pagename = url_quote(encode(pagename))
    pagegraph = add_global_links(request, pagename, pagegraph)
    selfname = get_selfname(request)

    return graph_to_n3(pagegraph, pagename, selfname)

def wikins_triplet(selfname, triplet):
    out = ''
    for prop, cond in zip(triplet, [True, False, True]):
        out = out + wikins_property(selfname, prop, cond) + ' '
    return out

def wikins_property(selfname, property, page):
    # Literal
    if property.startswith('"'):
        return property
    # A ready interwikiname
    if ':' in property:
        return property
    # Self
    if page:
        return selfname + ':' + property
    else:
        return selfname + ':Property' + property

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
