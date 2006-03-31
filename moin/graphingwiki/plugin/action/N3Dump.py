import shelve
import os
from codecs import getencoder
from urllib import quote

from MoinMoin import config
from MoinMoin.Page import Page
from MoinMoin.util import MoinMoinNoFooter

def rdfdump(n3file, wikiname, wikiurl, pages=None):
    # Open rdfdata
    n3db = shelve.open(n3file, flag='r')
    
    # If no pages given, dump all!
    if pages is None:
        pages = n3db.keys()

    # Default namespace definitons
    # TODO: Add rdf namespaces to interwikinames and get rid of this?
    outstr = """@prefix log: <http://www.w3.org/2000/10/swap/log#> .
@prefix math: <http://www.w3.org/2000/10/swap/math#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix %s: <%s> .
""" % (wikiname, wikiurl)

    # Add interwikinames to namespaces
    intermap = os.path.join(os.path.dirname(n3file),
                            '../', 'intermap.txt')
    iwns = file(intermap)
    for line in iwns:
        line = line.rstrip('\012\015')
        if line and not line.startswith('#'):
            outstr = outstr + "@prefix " + \
                     line.replace(' ', ': <', 1) + "> .\n"
    iwns.close()

    for page in pages:
        outstr = outstr + n3db[page]

    n3db.close()

    return outstr

def execute(pagename, request):
    if request.cfg.interwikiname:
        wikiname = quote(request.cfg.interwikiname)
    else:
        wikiname = quote(request.cfg.sitename)

    pageobj = Page(request, pagename)
    pagedir = pageobj.getPagePath()

    # Encoder from unicode to charset selected in config
    encoder = getencoder(config.charset)
    def _e(str):
        return encoder(str, 'replace')[0]

    n3file = os.path.join(pagedir, '../', 'rdfdata.shelve')
    pagename = quote(_e(pagename))

    request.http_headers(["Content-type: text/plain;charset=%s" %
                          config.charset])

    request.write('starting to write')

    n3 = rdfdump(n3file, wikiname, request.getBaseURL() + '/',
                 [pagename])

    request.write('stopped')

    request.write(n3)
    raise MoinMoinNoFooter
