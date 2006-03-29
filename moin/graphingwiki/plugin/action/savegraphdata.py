import re, os, cPickle, shelve
from codecs import getencoder
from urllib import quote, unquote
from tempfile import mktemp

# MoinMoin imports
from MoinMoin import config
from MoinMoin.parser.wiki import Parser
from MoinMoin.Page import Page
from MoinMoin import wikiutil

# cpe imports
from graphingwiki import graph

# shelve modifications go here
def shelve_add_category(shelve, cat, page):
    shelve['categories'].setdefault(cat, set()).add(page)

def shelve_add_link(shelve, (frm, to)):
    shelve['inlinks'].setdefault(to, set()).add(frm)

def execute(pagename, request, text, pagedir, page):
    if request.cfg.interwikiname:
        wikiname = quote(request.cfg.interwikiname)
    else:
        wikiname = quote(request.cfg.sitename)

    # Page graph file to save detailed data in
    gfn = os.path.join(pagedir,'graphdata.pickle')
    pagegraphfile = file(gfn, 'wb')

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

    # add categories, inlinks if nonexisting
    globaldata.setdefault('categories', {})
    globaldata.setdefault('inlinks', {})

    ## Different encoding/quoting functions
    # Encoder from unicode to charset selected in config
    encoder = getencoder(config.charset)
    def _e(str):
        return encoder(str, 'replace')[0]
    def _u(str):
        return unquote(str).replace('_', ' ')
    # Escape quotes in str, remove existing quotes, add outer quotes.
    def _quotestring(str):
        escq = re.compile(r'(?<!\\)"')
        str = str.strip("\"'")
        str = escq.subn('\\"', str)[0]
        return '"' + str + '"'

    # Quote names with namespace/interwiki (for rdf/n3 use)
    def _quotens(str):
        return ':'.join([_e(quote(x)) for x in str.split(':')])

    # import text_url -formatter
    try:
        Formatter = wikiutil.importPlugin(request.cfg, 'formatter',
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
    quotedname = _e(quote(_u(pagename)))
    pagenode = pagegraph.nodes.add(quotedname)

    page_n3 = wikiname + ":" + quotedname + " " + \
              wikiname + ":" + "URL" + " " + \
              wikiname + ":" + pagename + " .\n"

    # all in-links, categories from this page, to eliminate removed ones
    inlinks = set()
    categories = set()
    
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
                        key = quote(key.strip())
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
                                  wikiname + ":Property" + quote(key) + " " + \
                                  val + " .\n"

                # Handling of links
                if hit is not None and type in types and not inpre:
                    # urlformatter
                    replace = getattr(wikiparse, '_' + type + '_repl')
                    attrs = replace(hit)
                    if len(attrs) == 3:
                        # Name of node for local nodes = pagename
                        nodename = _e(quote(_u(attrs[1])))
                    elif len(attrs) == 2:
                        # Name of other nodes = url
                        nodename = _e(attrs[0])
                    else:
                        # Image link, or what have you
                        continue

                    # Add to categories
                    if nodename.startswith('Category'):
                        shelve_add_category(globaldata, nodename, quotedname)
                        categories.add(nodename)

                    # Add node w/ URL, label if not already added
                    if not pagegraph.nodes.get(nodename):
                        n = pagegraph.nodes.add(nodename)
                        n.URL = _e(attrs[0])
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
                    augdata = [strip(x) for x in _e(attrs[-1]).split(': ')]
                    
                    # in-links
                    if len(augdata) > 1 and augdata[0].endswith('From'):
                        augdata[0] = augdata[0][:-4]
                        edge.reverse()
                        n3_link.reverse()

                    n3_linktype = wikiname + ":Property" + _e(type)

                    # Add edge if not already added
                    e = pagegraph.edges.get(*edge)
                    if not e:
                        e = pagegraph.edges.add(*edge)
                    if len(augdata) > 1:
                        # quote all link types
                        e.linktype = quote(augdata[0])
                        if ':' in augdata[0]:
                            # links with namespace!
                            n3_linktype = _quotens(augdata[0])
                        else:
                            # links with link type from this wiki
                            n3_linktype = wikiname + ":Property" + \
                                          quote(augdata[0])
                    # Debug for urlformatter
                    # e.type = _e(type)

                    # FIXME: sux, add namespaces everywhere
                    if not edge[0].startswith('http://'):
                        shelve_add_link(globaldata, edge)
                        inlinks.add(edge[1])

                    # n3 data for link
                    # (links do property refs only)
                    link = n3_link[0] + " " + \
                           n3_linktype + " " + \
                           n3_link[1] + " .\n"
                    
                    # Don't add duplicate links
                    if not link in page_n3:
                        page_n3 = page_n3 + link

    # Remove old links, ie. links not in inlinks
    for page in globaldata['inlinks'].keys():
        if (quotedname in globaldata['inlinks'][page] and
            page not in inlinks):
            globaldata['inlinks'][page].remove(quotedname)

    # Remove old categories
    for cat in globaldata['categories'].keys():
        if (quotedname in globaldata['categories'][cat] and
            cat not in categories):
            globaldata['categories'][cat].remove(quotedname)

    # Save graph as pickle, close
    cPickle.dump(pagegraph, pagegraphfile)
    pagegraphfile.close()
    # Remove locks, close shelves
    os.unlink(graphlock)
    globaldata.close()

    os.unlink(rdflock)
    rdfdata[quotedname] = page_n3
    rdfdata.close()
