import re, os, cPickle
from codecs import getencoder
from urllib import quote, unquote

# MoinMoin imports
from MoinMoin import config
from MoinMoin.parser.wiki import Parser
from MoinMoin.Page import Page
from MoinMoin import wikiutil

# cpe imports
import graph

def execute(pagename, request, text, pagedir, page):
    # Filename to save data to
    gfn = os.path.join(pagedir,'graphdata.pickle')
    f = open(gfn, 'wb')

    # Encoder from unicode to charset selected in config
    encoder = getencoder(config.charset)
    def _e(str):
        return encoder(str, 'replace')[0]

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

    # Init graph to be saved
    outgraph = graph.Graph()
    outgraph.charset = config.charset
    # add a node for current page to graph
    selfname = quote(pagename)
    pagenode = outgraph.nodes.add(selfname)
    pagenode.label = _e(pagename)

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
                    # decode to target charset, remove )]]
                    hit = _e(hit[:-3])
                    args = hit.split('(')[1].split(',')
                    # Skip hidden argument
                    if args[-1] == 'hidden':
                        args = args[:-1]
                    # Skip mismatched pairs
                    if len(args) % 2:
                        args = args[:-1]
                    # set attributes for this page
                    for key, val in zip(args[::2], args[1::2]):
                        setattr(pagenode, key, val)

                # Handling of links
                if hit is not None and type in types and not inpre:
                    # urlformatter
                    replace = getattr(wikiparse, '_' + type + '_repl')
                    attrs = replace(hit)
                    if len(attrs) == 3:
                        # Name of node for local nodes = pagename
                        nodename = _e(attrs[1])
                    elif len(attrs) == 2:
                        # Name of other nodes = url
                        nodename = _e(attrs[0])
                    else:
                        # Image link, or what have you
                        continue

                    # Add node w/ URL, label if not already added
                    if not outgraph.nodes.get(nodename):
                        n = outgraph.nodes.add(nodename)
                        n.URL = _e(attrs[0])
                        n.label = unquote(nodename).replace('_', ' ')

                    edge = [selfname, nodename]
                    # Augmented links, eg. [PaGe:Ooh: PaGe]
                    augdata = _e(attrs[-1]).split(': ')
                    # in-links
                    if len(augdata) > 1 and augdata[0].endswith('From'):
                        augdata[0] = augdata[0][:-4]
                        edge.reverse()
                    # Add edge if not already added
                    if not outgraph.edges.get(*edge):
                        e = outgraph.edges.add(*edge)
                    if len(augdata) > 1:
                        e.linktype = augdata[0]
                    # Debug for urlformatter
                    # e.type = _e(type)

    # Save graph as pickle
    cPickle.dump(outgraph, f)
    f.close()
