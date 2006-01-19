import re, os, codecs, cPickle

# MoinMoin imports
from MoinMoin import config
from MoinMoin.parser.wiki import Parser

# cpe imports
import graph

def execute(pagename, request, text, pagedir):

    # Filename to save data to
    gfn = os.path.join(pagedir,'graphdata.pickle')
    f = open(gfn, 'wb')
    # f = codecs.open(gfn, 'wb', config.charset)

    # Get formatting rules from Parser/wiki
    # Regexps used below are also from there
    wikiparse = Parser(text, request)
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

    outgraph = graph.Graph()
    outgraph.nodes.add(pagename)

    for line in lines:
        # Comments not processed
        if line[0:2] == "##":
            continue
        # Headings not processed
        if heading_re.match(line):
            continue
        for match in all_re.finditer(line):
            for type, hit in match.groupdict().items():
                # Don't get links from inside preformatted/processor
                if type in pretypes and hit is not None:
                    inpre = not inpre
                # If there was a match we liked, not in preformat area
                if hit is not None and type in types and not inpre:
                    outgraph.nodes.add(hit)
                    e = outgraph.edges.add(pagename, hit)
                    e.type = type

    cPickle.dump(outgraph, f)
    f.close()
