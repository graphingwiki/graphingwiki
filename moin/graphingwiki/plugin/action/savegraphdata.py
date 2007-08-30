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
from time import time

# MoinMoin imports
from MoinMoin import config
from MoinMoin.parser.wiki import Parser
from MoinMoin.wikiutil import importPlugin
from MoinMoin.util.lock import WriteLock

# graphlib imports
from graphingwiki import graph
from graphingwiki.patterns import special_attrs

url_re = re.compile(u'^(' + Parser.url_pattern + ')')

# We only want to save linkage data releted to pages in this wiki
# Interwiki links will have ':' in their names (this will not affect
# pages as their names are url quotes at this stage)
def local_page(pagename):
    if url_re.search(pagename) or ':' in pagename:
        return False

    return True

# Add in-links from current node to local nodes
def shelve_add_in(shelve, (frm, to), linktype):
    if not linktype:
        linktype = '_notype'
    if local_page(to):
         temp = shelve.get(to, {})

         if not temp.has_key('in'):
             temp['in'] = {linktype: [frm]}
         elif not temp['in'].has_key(linktype):
             temp['in'][linktype] = [frm]
         else:
             temp['in'][linktype].append(frm)

         # Notification that the destination has changed
         temp['mtime'] = time()
         
         shelve[to] = temp

# Add out-links from local nodes to current node
def shelve_add_out(shelve, (frm, to), linktype):
    if not linktype:
        linktype = '_notype'
    if local_page(frm):
         temp = shelve.get(frm, {})

         if not temp.has_key('out'):
             temp['out'] = {linktype: [to]}
         elif not temp['out'].has_key(linktype):
             temp['out'][linktype] = [to]
         else:
             temp['out'][linktype].append(to)

         shelve[frm] = temp

# Respectively, remove in-links
def shelve_remove_in(shelve, (frm, to), linktype):
    import sys
#    sys.stderr.write('Starting to remove in\n')
    temp = shelve.get(to, {})
    if local_page(to) and temp.has_key('in'):
        for type in linktype:
#            sys.stderr.write("Removing %s %s %s\n" % (frm, to, linktype))
            # eg. when the shelve is just started, it's empty
            if not temp['in'].has_key(type):
#                sys.stderr.write("No such type: %s\n" % type)
                continue
            if frm in temp['in'][type]:
                temp['in'][type].remove(frm)
                if not temp['in'][type]:
                    del temp['in'][type]
                    
                # Notification that the destination has changed
                temp['mtime'] = time()
                
#                sys.stderr.write("Hey man, I think I did it!\n")
        shelve[to] = temp

# Respectively, remove out-links
def shelve_remove_out(shelve, (frm, to), linktype):
    import sys
#    sys.stderr.write('Starting to remove out\n')
    temp = shelve.get(frm, {})
    if local_page(frm) and temp.has_key('out'):
        for type in linktype:
#            sys.stderr.write("Removing %s %s %s\n" % (frm, to, linktype))
            # eg. when the shelve is just started, it's empty
            if not temp['out'].has_key(type):
#                sys.stderr.write("No such type: %s\n" % type)
                continue
            if to in temp['out'][type]:
                temp['out'][type].remove(to)
                if not temp['out'][type]:
                    del temp['out'][type]
#                sys.stderr.write("Hey man, I think I did it!\n")
        shelve[frm] = temp

def quotemeta(key, val):
    # Keys may be pages -> url-quoted
    key = url_quote(key.strip())
    if key != 'label':
        val = val.strip()

    # Values are just quoted strings
    val = quotedstring(val)
    return key, val

def node_set_attribute(pagenode, key, val):
    key, val = quotemeta(key, val)
    vars = getattr(pagenode, key, None)
    if not vars:
        setattr(pagenode, key, set([val]))
    else:
        vars.add(val)
        setattr(pagenode, key, vars)

def shelve_unset_attributes(shelve, node):
    if shelve.get(node, {}).has_key('meta'):

        temp = shelve[node]
        temp['meta'] = {}
        shelve[node] = temp

def shelve_set_attribute(shelve, node, key, val):
    key, val = quotemeta(key, val)

    temp = shelve.get(node, {})

    if not temp.has_key('meta'):
        temp['meta'] = {key: set([val])}
    elif not temp['meta'].has_key(key):
        temp['meta'][key] = set([val])
    # a page can not have more than one label, shapefile etc
    elif key in special_attrs:
        temp['meta'][key] = set([val])
    else:
        temp['meta'][key].add(val)

    shelve[node] = temp

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

def getlinktype(augdata):
    linktype = ''
    if len(augdata) > 1:
        if ':' in augdata[0]:
            # links with namespace!
            linktype = quotens(augdata[0])
        else:
            # quote all link types
            linktype = url_quote(augdata[0])
    return linktype

def add_meta(globaldata, pagenode, quotedname, hit):
    # decode to target charset, grab comma-separated key,val
    hit = encode(hit[11:-3])
    args = hit.split(',')

    # If no data, continue
    if len(args) < 2:
        return

    key = args[0]
    val = ','.join(args[1:])

    # Do not handle empty metadata, except empty labels
    if key != 'label':
        val = val.strip()
    if not val:
        return

    # Values to be handed to dot
    if key in special_attrs:
        setattr(pagenode, key, val)
        shelve_set_attribute(globaldata, quotedname, key, val)
        # If color defined¸ set page as filled
        if key == 'fillcolor':
            setattr(pagenode, 'style', 'filled')
            shelve_set_attribute(globaldata, quotedname,
                                 'style', 'filled')
        return

    # Save to pagegraph and shelve's metadata list
    node_set_attribute(pagenode, key, val)
    shelve_set_attribute(globaldata, quotedname, key, val)

def parse_link(wikiparse, hit, type):
    replace = getattr(wikiparse, '_' + type + '_repl')
    attrs = replace(hit)
    nodelabel = ''

    if len(attrs) == 4:
        # Attachments, eg:
        # URL   = Page?action=AttachFile&do=get&target=k.txt
        # name  = Page/k.txt
        # label = k.txt
        nodename = url_quote(encode(attrs[1]))
        nodeurl = encode(attrs[0])
        nodelabel = encode(attrs[2])
    elif len(attrs) == 3:
        # Local pages
        # Name of node for local nodes = pagename
        nodename = url_quote(encode(attrs[1]))
        nodeurl = encode(attrs[0])
        # To prevent subpagenames from sucking
        if nodeurl.startswith('/'):
            nodeurl = './' + nodename
        # Nicer looking labels for nodes
        unqname = wiki_unquote(nodename)
        if unqname != nodename:
            nodelabel = unqname
    elif len(attrs) == 2:
        # Name of other nodes = url
        nodeurl = encode(attrs[0])
        nodename = url_quote(nodeurl)

        # Change name for different type of interwikilinks
        if type == 'interwiki':
            nodename = quotens(hit)
            nodelabel = nodename
        elif type == 'url_bracket':
            # Interwikilink in brackets?
            iw = re.search(r'\[(?P<iw>.+?)[\] ]',
                           hit).group('iw')

            if iw.split(":")[0] == 'wiki':
                iw = iw.split(None, 1)[0]
                iw = iw[5:].replace('/', ':', 1)
                nodename = quotens(iw)
                nodelabel = nodename
        # Interwikilink turned url?
        elif type == 'url':
            if hit.split(":")[0] == 'wiki':
                iw = hit[5:].replace('/', ':', 1)
                nodename = quotens(iw)
                nodelabel = nodename
    else:
        # Catch-all
        return "", "", "", ""

    # augmented links, eg. [:PaGe:Ooh: PaGe]
    augdata = [x.strip() for x in
               encode(attrs[-1]).split(': ')]

    linktype = getlinktype(augdata)

    return nodename, nodelabel, nodeurl, linktype

def add_link(globaldata, quotedname, pagegraph, cat_re,
             nodename, nodelabel, nodeurl, linktype):
    if cat_re.search(nodename):
        pagenode = pagegraph.nodes.get(quotedname)
        node_set_attribute(pagenode, 'WikiCategory', nodename)
        shelve_set_attribute(globaldata, quotedname,
                             'WikiCategory', nodename)

    # Add node w/ URL, label if not already added
    shelve_set_attribute(globaldata, nodename, 'URL', nodeurl)
    if not pagegraph.nodes.get(nodename):
        n = pagegraph.nodes.add(nodename)
        n.URL = nodeurl
        # Add label, if not already added
        if nodelabel and not getattr(n, 'label', ''):
            n.label = nodelabel
            meta = globaldata.get(nodename, {}).get('meta', {})
            if not meta.get('label', ''):
                shelve_set_attribute(globaldata, nodename,
                                     'label', nodelabel)

    edge = [quotedname, nodename]

    # in-links
    if linktype.endswith('From'):
        linktype = linktype[:-4]
        edge.reverse()

    shelve_add_in(globaldata, edge, linktype)
    shelve_add_out(globaldata, edge, linktype)

    # Add edge if not already added
    e = pagegraph.edges.get(*edge)
    if not e:
        e = pagegraph.edges.add(*edge)

    if not linktype:
        linktype = '_notype'

    if hasattr(e, 'linktype'):
        e.linktype.add(linktype)
    else:
        e.linktype = set([linktype])


def execute(pagename, request, text, pagedir, page):
    # Skip MoinEditorBackups
    if pagename.endswith('/MoinEditorBackup'):
        return

    # Category matching regexp
    cat_re = re.compile(request.cfg.page_category_regex)

    graphshelve = os.path.join(request.cfg.data_dir,
                               'graphdata.shelve')

    # Expires old locks left by crashes etc.
    # Page locking mechanisms should prevent this code being
    # executed prematurely - thus expiring both read and
    # write locks
    lock = WriteLock(request.cfg.data_dir, timeout=10.0)
    lock.acquire()

    # Open file db for global graph data, creating it if needed
    globaldata = shelve.open(graphshelve, flag='c')
    
    # The global graph data contains all the links, even those that
    # are not immediately available in the page's graphdata pickle

    quotedname = url_quote(encode(pagename))

    # Page graph file to save detailed data in
    gfn = os.path.join(pagedir,'graphdata.pickle')
    # load graphdata if present and not trashed, remove it from index
    if os.path.isfile(gfn) and os.path.getsize(gfn):
        pagegraphfile = file(gfn)
        old_data = cPickle.load(pagegraphfile)
        
        for edge in old_data.edges.getall(parent=quotedname):
            e = old_data.edges.get(*edge)
            linktype = getattr(e, 'linktype', ['_notype'])
            shelve_remove_in(globaldata, edge, linktype)
            shelve_remove_out(globaldata, edge, linktype)

        for edge in old_data.edges.getall(child=quotedname):
            e = old_data.edges.get(*edge)
            linktype = getattr(e, 'linktype', ['_notype'])
            shelve_remove_in(globaldata, edge, linktype)
            shelve_remove_out(globaldata, edge, linktype)

        shelve_unset_attributes(globaldata, quotedname)

        pagegraphfile.close()

    # Include timestamp to current page
    if not globaldata.has_key(quotedname):
        globaldata[quotedname] = {'mtime': time(), 'saved': True}
    else:
        temp = globaldata[quotedname]
        temp['mtime'] = time()
        temp['saved'] = True
        globaldata[quotedname] = temp

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
    linktypes = ["wikiname_bracket", "word",
                  "interwiki", "url", "url_bracket"]

    # Get lines of raw wiki markup
    lines = eol_re.split(text)

    # status: are we in preprocessed areas?
    inpre = False
    pretypes = ["pre", "processor"]

    # status: have we just entered a link with dict,
    # we should not enter it again
    dicturl = False

    # Init pagegraph
    pagegraph = graph.Graph()
    pagegraph.charset = config.charset

    # add a node for current page
    pagenode = pagegraph.nodes.add(quotedname)
    # add a nicer-looking label, also
    pagelabel = encode(pagename)
    shelve_set_attribute(globaldata, quotedname, 'label', pagelabel)

    for line in lines:
        # Comments not processed
        if line[0:2] == "##":
            continue
        # Headings not processed
        if heading_re.match(line):
            continue
        for match in all_re.finditer(line):
            for type, hit in match.groupdict().items():
                #if hit:
                #    print hit, type

                # Skip empty hits
                if hit is None:
                    continue

                # We don't want to handle anything inside preformatted
                if type in pretypes:
                    inpre = not inpre
                    #print inpre

                # Handling of MetaData-macro
                elif type == 'macro' and not inpre:
                    if hit.startswith('[[MetaData'):
                        add_meta(globaldata, pagenode, quotedname, hit)

                # Handling of links
                elif type in linktypes and not inpre:
                    # If we just came from a dict, which saved a typed
                    # link, do not save it again
                    if dicturl:
                        dicturl = False
                        continue

                    name, label, url, linktype = parse_link(wikiparse,
                                                            hit,
                                                            type)

                    if name:
                        add_link(globaldata, quotedname, pagegraph, cat_re,
                                 name, label, url, linktype)

                # Links and metadata defined in a definition list
                elif type == 'dl' and not inpre:
                    data = line.split('::')
                    key, val = data[0], '::'.join(data[1:])
                    key = key.lstrip()

                    # Try to find if the value points to a link
                    matches = all_re.search(val.lstrip())
                    if matches:
                        # Take all matches if his non-empty
                        # and hit type in linktypes
                        match = [(type, hit) for type, hit in
                                 matches.groupdict().iteritems()
                                 if hit is not None \
                                 and type in linktypes]
                        # If link, save as link
                        if match:
                            type, hit = match[0]

                            val = val.strip()
                            name, label, url, linktype = parse_link(wikiparse,\
                                                         hit, type)
                            # Take linktype from the dict key
                            linktype = getlinktype([encode(x)
                                                    for x in key, val])

                            if name:
                                add_link(globaldata, quotedname,
                                         pagegraph, cat_re,
                                         name, label, url, linktype)
                                # The val is also parsed by Moin's link parser
                                # -> need to tell our link parser that the
                                #    link was already saved
                                dicturl = True

                    # If it was not link, save as metadata
                    if not dicturl:
                        add_meta(globaldata, pagenode, quotedname,
                                 "[[MetaData(%s,%s)]]" % (key, val))
                    
    # Save graph as pickle, close
    cPickle.dump(pagegraph, pagegraphfile)
    pagegraphfile.close()
    # Remove locks, close shelves
    globaldata.close()
    lock.release()
