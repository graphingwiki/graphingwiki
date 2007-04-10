# -*- coding: iso-8859-1 -*-
"""
    savegraphdata class for saving the semantic data of pages

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

import re
import os
import cPickle
import shelve
from codecs import getencoder
from urllib import quote as url_quote
from urllib import unquote as url_unquote

# MoinMoin imports
from MoinMoin import config
from MoinMoin.parser.wiki import Parser
from MoinMoin.wikiutil import importPlugin

# graphlib imports
from graphingwiki import graph

url_re = re.compile(u'^(' + Parser.url_pattern + ')')

special_attrs = ["label", "sides", "tooltip", "skew", "orientation",
                 "shape", 'belongs_to_patterns', 'URL', 'shapefile']

# non-local pagenames have either an URL or a namespace
def local_page(pagename):
    if url_re.search(pagename) or ':' in pagename:
        return False

    return True

# Add in-links from current node to local nodes
def shelve_add_in(shelve, (frm, to)):
    if local_page(to):                    
        shelve['in'].setdefault(to, set()).add(frm)

# Add out-links from local nodes to current node
def shelve_add_out(shelve, (frm, to)):
    if local_page(frm):
        shelve['out'].setdefault(frm, set()).add(to)

# Respectively, remove in-links
def shelve_remove_in(shelve, (frm, to)):
    if local_page(to) and shelve['in'].has_key(to):
        if frm in shelve['in'][to]:
            if len(shelve['in'][to]) == 1:
                del shelve['in'][to]
            else:
                shelve['in'][to].discard(frm)

# Respectively, remove out-links
def shelve_remove_out(shelve, (frm, to)):
    if local_page(frm) and shelve['out'].has_key(frm):
        if to in shelve['out'][frm]:
            if len(shelve['out'][frm]) == 1:
                del shelve['out'][frm]
            else:
                shelve['out'][frm].discard(to)

def node_set_attribute(pagenode, key, val):
    # Keys may be pages -> url-quoted
    key = url_quote(key.strip())
    # Values are just quoted strings
    val = quotedstring(val.strip())
    vars = getattr(pagenode, key, None)
    if not vars:
        setattr(pagenode, key, set([val]))
    else:
        vars.add(val)
        setattr(pagenode, key, vars)

def shelve_set_attribute(shelve_data, node, key, val):
     shelve_data['meta'].setdefault(node, {}).setdefault(key, []).append(val)

## Different encoding/quoting functions
# Encoder from unicode to charset selected in config
encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]
def wiki_unquote(str):
    return url_unquote(str).replace('_', ' ')

# Escape quotes in str, remove existing quotes, add outer quotes.
def quotedstring(str):
    escq = re.compile(r'(?<!\\)"')
    str = str.strip("\"'")
    str = escq.subn('\\"', str)[0]
    return '"' + str + '"'

# Quote names with namespace/interwiki (for rdf/n3 use)
def quotens(str):
    return ':'.join([url_quote(encode(x)) for x in str.split(':')])

def execute(pagename, request, text, pagedir, page):
    # Skip MoinEditorBackups
    if pagename.endswith('/MoinEditorBackup'):
        return

    graphshelve = os.path.join(pagedir, '../', 'graphdata.shelve')

    # lock on graphdata
    graphlock = graphshelve + '.lock'
    os.spawnlp(os.P_WAIT, 'lockfile', 'lockfile', graphlock)

    # Open file db for global graph data, creating it if needed
    globaldata = shelve.open(graphshelve, writeback=True, flag='c')

    # The global graph data contains all the links, even those that
    # are not immediately available in the page's graphdata pickle

    # The in-dict contains all the links to a node
    if not globaldata.has_key('in'):
        globaldata['in'] = {}
    # The out-dict contains a node's out-links
    # that are not shown in the node's pickle
    if not globaldata.has_key('out'):
        globaldata['out'] = {}

    # List of all the metadata keys of pages
    if not globaldata.has_key('meta'):
        globaldata['meta'] = {}

    quotedname = url_quote(encode(pagename))

    # Page graph file to save detailed data in
    gfn = os.path.join(pagedir,'graphdata.pickle')
    # load graphdata if present and not trashed, remove it from index
    if os.path.isfile(gfn) and os.path.getsize(gfn):
        pagegraphfile = file(gfn)
        old_data = cPickle.load(pagegraphfile)
        for edge in old_data.edges.getall(parent=quotedname):
            shelve_remove_in(globaldata, edge)
        for edge in old_data.edges.getall(child=quotedname):
            shelve_remove_out(globaldata, edge)
        if globaldata['meta'].has_key(quotedname):
            globaldata['meta'][quotedname] = {}
        pagegraphfile.close()
            
    # Overwrite pagegraphfile with the new data
    pagegraphfile = file(gfn, 'wb')

    # import text_url -formatter
    try:
        Formatter = importPlugin(request.cfg, 'formatter',
                                 'text_url', "Formatter")
    except:
        # default to plain text
        from MoinMoin.formatter.text_plain import Formatter

    urlformatter = Formatter(request)

    # Get formatting rules from Parser/wiki
    # Regexps used below are also from there
    wikiparse = Parser(text, request)
    wikiparse.formatter = urlformatter
    urlformatter.setPage(page)

    rules = wikiparse.formatting_rules.replace('\n', '|')

    if request.cfg.bang_meta:
        rules = ur'(?P<notword>!%(word_rule)s)|%(rules)s' % {
            'word_rule': wikiparse.word_rule,
            'rules': rules,
            }

    # For versions with the deprecated config variable allow_extended_names
    if not '?P<wikiname_bracket>' in rules:
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

    # add a node for current page
    pagenode = pagegraph.nodes.add(quotedname)

    # Add nicer looking label if necessary
    unqname = wiki_unquote(quotedname)
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
                    hit = encode(hit[11:-3])
                    args = hit.split(',')
                    # Skip hidden argument
                    if args[-1] == 'hidden':
                        args = args[:-1]
                    # Skip mismatched pairs
                    if len(args) % 2:
                        args = args[:-1]
                    # set attributes for this page
                    for key, val in zip(args[::2], args[1::2]):
                        # Do not handle empty metadata, except empty labels
                        if key != 'label':
                            val = val.strip()
                        if not val:
                            continue
                        # Values to be handed to dot
                        if key in special_attrs:
                            setattr(pagenode, key, val)
                            continue
                        # Save to pagegraph and shelve's metadata list
                        node_set_attribute(pagenode, key, val)
                        shelve_set_attribute(globaldata, quotedname, key, val)

                # Handling of links
                if hit is not None and type in types and not inpre:
                    #print hit
                    # urlformatter
                    replace = getattr(wikiparse, '_' + type + '_repl')
                    attrs = replace(hit)

                    if len(attrs) == 3:
                        # Name of node for local nodes = pagename
                        nodename = url_quote(encode(attrs[1]))
                        nodeurl = encode(attrs[0])
                        # To prevent subpagenames from sucking
                        if nodeurl.startswith('/'):
                            nodeurl = './' + nodename
                    elif len(attrs) == 2:
                        # Name of other nodes = url
                        nodename = encode(attrs[0])
                        nodeurl = nodename

                        # Change name for different type of interwikilinks
                        if type == 'interwiki':
                            nodename = quotens(hit)
                        elif type == 'url_bracket':
                            # Interwikilink in brackets?
                            iw = re.search(r'\[(?P<iw>.+?)[\] ]',
                                           hit).group('iw')

                            if iw.split(":")[0] == 'wiki':
                                iw = iw.split(None, 1)[0]
                                iw = iw[5:].replace('/', ':', 1)
                                nodename = quotens(iw)
                        # Interwikilink turned url?
                        elif type == 'url':
                            if hit.split(":")[0] == 'wiki':
                                iw = hit[5:].replace('/', ':', 1)
                                nodename = quotens(iw)
                    else:
                        # Image link, or what have you
                        continue

                    if nodename.startswith('Category'):
                        node_set_attribute(pagenode, 'WikiCategory', nodename)

                    # Add node w/ URL, label if not already added
                    if not pagegraph.nodes.get(nodename):
                        n = pagegraph.nodes.add(nodename)
                        n.URL = nodeurl
                        # Nicer looking labels for nodes
                        unqname = wiki_unquote(nodename)
                        if unqname != nodename:
                            n.label = unqname

                    edge = [quotedname, nodename]

                    # augmented links, eg. [:PaGe:Ooh: PaGe]
                    augdata = [x.strip() for x in
                               encode(attrs[-1]).split(': ')]
                    
                    # in-links
                    if len(augdata) > 1 and augdata[0].endswith('From'):
                        augdata[0] = augdata[0][:-4]
                        edge.reverse()
                        shelve_add_out(globaldata, edge)

                    # Add edge if not already added
                    e = pagegraph.edges.get(*edge)
                    if not e:
                        e = pagegraph.edges.add(*edge)
                    if len(augdata) > 1:
                        if ':' in augdata[0]:
                            # links with namespace!
                            e.linktype = quotens(augdata[0])
                        else:
                            # quote all link types
                            e.linktype = url_quote(augdata[0])

                    shelve_add_in(globaldata, edge)

    # Save graph as pickle, close
    cPickle.dump(pagegraph, pagegraphfile)
    pagegraphfile.close()
    # Remove locks, close shelves
    globaldata.close()
    os.unlink(graphlock)
