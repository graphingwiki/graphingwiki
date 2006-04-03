import re, os, cPickle, shelve
from codecs import getencoder
from urllib import quote as url_quote
from urllib import unquote as url_unquote
from tempfile import mktemp

# MoinMoin imports
from MoinMoin import config
from MoinMoin.parser.wiki import Parser
from MoinMoin.Page import Page
from MoinMoin.wikiutil import importPlugin

# cpe imports
from graphingwiki import graph

def shelve_add_link(shelve, (frm, to)):
    shelve.setdefault(to, set()).add(frm)

def shelve_remove_link(shelve, (frm, to)):
    if not shelve.has_key(to):
        return
    if frm in shelve[to]:
        if len(shelve[to]) == 1:
            del shelve[to]
        else:
            shelve[to].discard(frm)

def execute(pagename, request, text, pagedir, page):

    ## Different encoding/quoting functions
    # Encoder from unicode to charset selected in config
    encoder = getencoder(config.charset)
    def _e(str):
        return encoder(str, 'replace')[0]
    def _u(str):
        return url_unquote(str).replace('_', ' ')
    # Escape quotes in str, remove existing quotes, add outer quotes.
    def _quotestring(str):
        escq = re.compile(r'(?<!\\)"')
        str = str.strip("\"'")
        str = escq.subn('\\"', str)[0]
        return '"' + str + '"'

    # Quote names with namespace/interwiki (for rdf/n3 use)
    def _quotens(str):
        return ':'.join([_e(url_quote(x)) for x in str.split(':')])

    if request.cfg.interwikiname:
        wikiname = url_quote(_e(request.cfg.interwikiname))
    else:
        wikiname = url_quote(_e(request.cfg.sitename))

    graphshelve = os.path.join(pagedir, '../', 'graphdata.shelve')
    rdfshelve = os.path.join(pagedir, '../', 'rdfdata.shelve')

    # lock on graphdata
    graphlock = graphshelve + '.lock'
    os.spawnlp(os.P_WAIT, 'lockfile', 'lockfile', graphlock)

    # FIXME: to be removed, in due time
    # lock on rdfdata
    rdflock = rdfshelve + '.lock'
    os.spawnlp(os.P_WAIT, 'lockfile', 'lockfile', rdflock)

    # Open file db for global graph data, creating it if needed
    globaldata = shelve.open(graphshelve, writeback=True, flag='c')

    # FIXME: to be removed, in due time
    rdfdata = shelve.open(rdfshelve, flag='c')

    # Page graph file to save detailed data in
    gfn = os.path.join(pagedir,'graphdata.pickle')
    # load graphdata if present and not trashed, remove it from index
    if os.path.isfile(gfn) and os.path.getsize(gfn):
        pagegraphfile = file(gfn)
        old_data = cPickle.load(pagegraphfile)
        for edge in old_data.edges.getall():
            if not edge[1].startswith('http://'):
                shelve_remove_link(globaldata, edge)
        pagegraphfile.close()
            
    # Overwrite pagegraphfile with the new data
    pagegraphfile = file(gfn, 'wb')

    # import text_url -formatter
    try:
        Formatter = importPlugin(request.cfg, 'formatter',
                                 'text_url', "Formatter")
    except:
        # default to plain text
        import sys
        from MoinMoin.formatter.text_plain import Formatter

    urlformatter = Formatter(request)

    # Get formatting rules from Parser/wiki
    # Regexps used below are also from there
    wikiparse = Parser(text, request)
    wikiparse.formatter = urlformatter
    urlformatter.setPage(page)

    rules = wikiparse.formatting_rules.replace('\n', '|')

    if request.cfg.allow_extended_names:
        rules = rules + ur'|(?P<wikiname_bracket>\[".*?"\])'

    all_re = re.compile(rules, re.UNICODE)
    eol_re = re.compile(r'\r?\n', re.UNICODE)
    # end space removed from heading_re, it means '\n' in parser/wiki
    heading_re = re.compile(r'\s*(?P<hmarker>=+)\s.*\s(?P=hmarker)',
                            re.UNICODE)

    # These are the match types that really should be noted
    types = ["wikiname_bracket", "word",
             "interwiki", "url", "url_bracket"]

    # Get lines of raw wiki markup
    lines = eol_re.split(text)

    # status: are we in preprocessed areas?
    inpre = False
    pretypes = ["pre", "processor"]

    # Init pagegraph
    pagegraph = graph.Graph()
    pagegraph.charset = config.charset

    # add a node for current page to different data stores
    quotedname = url_quote(_e(pagename))
    pagenode = pagegraph.nodes.add(quotedname)

    page_n3 = ''

    # Add nicer looking label if necessary
    unqname = _u(quotedname)
    if unqname != quotedname:
        pagenode.label = unqname

    for line in lines:
        # Comments not processed
        if line[0:2] == "##":
            continue
        # Headings not processed
        if heading_re.match(line):
            continue
        for match in all_re.finditer(line):
            for type, hit in match.groupdict().items():
                # We don't want to handle anything inside preformatted
                if type in pretypes and hit is not None:
                    inpre = not inpre

                # Handling of MetaData-macro
                if hit is not None and type == 'macro' and not inpre:

                    if not hit.startswith('[[MetaData'):
                        continue
                    # decode to target charset, grab comma-separated args
                    hit = _e(hit[11:-3])
                    args = hit.split(',')
                    # Skip hidden argument
                    if args[-1] == 'hidden':
                        args = args[:-1]
                    # Skip mismatched pairs
                    if len(args) % 2:
                        args = args[:-1]
                    # set attributes for this page
                    for key, val in zip(args[::2], args[1::2]):
                        # Keys may be pages -> url-quoted
                        key = url_quote(key.strip())
                        # Values are just quoted strings
                        val = _quotestring(val.strip())
                        vars = getattr(pagenode, key, None)
                        if not vars:
                            setattr(pagenode, key, set([val]))
                        else:
                            vars.add(val)
                            setattr(pagenode, key, vars)

                        # Make n3 entry for the metadata,
                        # quoted text as literals
                        # (metadata-macro does literal refs only)

                        page_n3 = page_n3 + \
                                  wikiname + ":" + quotedname + " " + \
                                  wikiname + ":Property" + \
                                  key + " " + val + " .\n"

                # Handling of links
                if hit is not None and type in types and not inpre:
                    # print hit
                    # urlformatter
                    replace = getattr(wikiparse, '_' + type + '_repl')
                    attrs = replace(hit)
                    if len(attrs) == 3:
                        # Name of node for local nodes = pagename
                        # Is this a hack, or what?
                        if '_' in attrs[1]:
                            nodename = _e(url_quote(
                                attrs[1].replace('_', ' ')))
                            nodeurl = _e(url_quote(
                                attrs[0].replace('_', ' ')))
                        else:
                            nodename = _e(attrs[1])
                            nodeurl = _e(attrs[0])
                        # To prevent subpagenames from sucking
                        if nodeurl.startswith('/'):
                            nodeurl = './' + nodename
                    elif len(attrs) == 2:
                        # Name of other nodes = url
                        nodename = _e(attrs[0])
                        nodeurl = nodename
                    else:
                        # Image link, or what have you
                        continue

                    # Add node w/ URL, label if not already added
                    if not pagegraph.nodes.get(nodename):
                        n = pagegraph.nodes.add(nodename)
                        n.URL = nodeurl
                        # Nicer looking labels for nodes
                        unqname = _u(nodename)
                        if unqname != nodename:
                            n.label = unqname

                    edge = [quotedname, nodename]

                    # Non-local/local links for n3 output
                    # so that namespaces / interwikilinks would rock
                    if len(attrs) == 2:
                        linkname = ''
                        
                        if type == 'interwiki':
                            linkname = _quotens(hit)
                        elif type == 'url_bracket':
                            # Interwikilink in brackets?
                            iw = re.search(r'\[(?P<iw>.+?)[\] ]',
                                           hit).group('iw')

                            if iw.split(":")[0] == 'wiki':
                                iw = iw.split(None, 1)[0]
                                iw = iw[5:].replace('/', ':', 1)
                                linkname = _quotens(iw)
                        # Interwikilink turned url?
                        elif type == 'url':
                            if hit.split(":")[0] == 'wiki':
                                iw = hit[5:].replace('/', ':', 1)
                                linkname = _quotens(iw)

                        # Normal url
                        if not linkname:
                            linkname = '<' + nodename + '>'

                        n3_link = [wikiname + ":" + quotedname,
                                   linkname]
                    else:
                        n3_link = [wikiname + ":" + quotedname,
                                   wikiname + ":" + nodename]

                    # Augmented links, eg. [:PaGe:Ooh: PaGe]
                    augdata = [x.strip() for x in _e(attrs[-1]).split(': ')]
                    
                    # in-links
                    if len(augdata) > 1 and augdata[0].endswith('From'):
                        augdata[0] = augdata[0][:-4]
                        edge.reverse()
                        n3_link.reverse()

                    # No need to quote if of basic type
                    n3_linktype = wikiname + ":Property" + _e(type)

                    # Add edge if not already added
                    e = pagegraph.edges.get(*edge)
                    if not e:
                        e = pagegraph.edges.add(*edge)
                    if len(augdata) > 1:
                        # quote all link types
                        e.linktype = url_quote(augdata[0])
                        if ':' in augdata[0]:
                            # links with namespace!
                            n3_linktype = _quotens(augdata[0])
                        else:
                            # links with link type from this wiki
                            # quoted because may be a page
                            n3_linktype = wikiname + ":Property" + \
                                          url_quote(augdata[0])
                    # Debug for urlformatter
                    # e.type = _e(type)

                    # FIXME: sux, add namespaces everywhere
                    if not edge[1].startswith('http://'):
                        shelve_add_link(globaldata, edge)
                    # print "inlinks to", edge[1], "from", edge[0]

                    # n3 data for link
                    # (links do property refs only)
                    link = n3_link[0] + " " + \
                           n3_linktype + " " + \
                           n3_link[1] + " .\n"
                    
                    # Don't add duplicate links
                    if not link in page_n3:
                        page_n3 = page_n3 + link

    # Save graph as pickle, close
    cPickle.dump(pagegraph, pagegraphfile)
    pagegraphfile.close()
    # Remove locks, close shelves
    globaldata.close()
    os.unlink(graphlock)

    rdfdata[quotedname] = page_n3
    rdfdata.close()
    os.unlink(rdflock)
