# -*- coding: utf-8 -*-"
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
import shelve

from time import time
from copy import copy

# MoinMoin imports
from MoinMoin.parser.wiki import Parser
from MoinMoin.wikiutil import importPlugin
from MoinMoin.util.lock import WriteLock

# graphlib imports
from graphingwiki import graph
from graphingwiki.patterns import special_attrs
from graphingwiki.editing import parse_categories

# Page names cannot contain '//'
url_re = re.compile(u'^(%s)://' % (Parser.url_pattern))

# We only want to save linkage data releted to pages in this wiki
def local_page(pagename):
    if url_re.search(pagename):
        return False
    return True

# Add in-links from current node to local nodes
def shelve_add_in(new_data, (frm, to), linktype):
    if not linktype:
        linktype = '_notype'
    if local_page(to):
         temp = new_data.get(to, {})

         if not temp.has_key('in'):
             temp['in'] = {linktype: [frm]}
         elif not temp['in'].has_key(linktype):
             temp['in'][linktype] = [frm]
         else:
             temp['in'][linktype].append(frm)

         # Notification that the destination has changed
         temp['mtime'] = time()
         
         new_data[to] = temp

# Add out-links from local nodes to current node
def shelve_add_out(new_data, (frm, to), linktype, hit):
    if not linktype:
        linktype = '_notype'
    if local_page(frm):
         temp = new_data.get(frm, {})

         # Also add literal text (hit) for each link
         # eg, if out it SomePage, lit can be ["SomePage"]
         if not temp.has_key('out'):
             temp['out'] = {linktype: [to]}
             temp['lit'] = {linktype: [hit]}
         elif not temp['out'].has_key(linktype):
             temp['out'][linktype] = [to]
             temp['lit'][linktype] = [hit]
         else:
             temp['out'][linktype].append(to)
             temp['lit'][linktype].append(hit)

         new_data[frm] = temp

# Respectively, remove in-links
def shelve_remove_in(new_data, (frm, to), linktype):
    import sys
#    sys.stderr.write('Starting to remove in\n')
    temp = new_data.get(to, {})
    if local_page(to) and temp.has_key('in'):
        for type in linktype:
#            sys.stderr.write("Removing %s %s %s\n" % (frm, to, linktype))
            # eg. when the shelve is just started, it's empty
            if not temp['in'].has_key(type):
#                sys.stderr.write("No such type: %s\n" % type)
                continue
            while frm in temp['in'][type]:
                temp['in'][type].remove(frm)

                # Notification that the destination has changed
                temp['mtime'] = time()

            if not temp['in'][type]:
                del temp['in'][type]
                
#                sys.stderr.write("Hey man, I think I did it!\n")
        new_data[to] = temp

# Respectively, remove out-links
def shelve_remove_out(new_data, (frm, to), linktype):
#    print 'Starting to remove out'
    temp = new_data.get(frm, {})
    if local_page(frm) and temp.has_key('out'):
        for type in linktype:
#            print "Removing %s %s %s" % (frm, to, linktype)
            # eg. when the shelve is just started, it's empty
            if not temp['out'].has_key(type):
#                print "No such type: %s" % type
                continue
            while to in temp['out'][type]:
                # As the literal text values for the links
                # are added at the same time, they have the
                # same index value
                i = temp['out'][type].index(to)
                temp['out'][type].remove(to)
                del temp['lit'][type][i]

#                print "removed %s" % (repr(to))

            if not temp['out'][type]:
                del temp['out'][type]
                del temp['lit'][type]
#                print "%s empty" % (type)
#            print "Hey man, I think I did it!"

        new_data[frm] = temp

def strip_meta(key, val):
    key = key.strip()
    if key != 'gwikilabel':
        val = val.strip()
    return key, val

def shelve_set_attribute(new_data, node, key, val):
    key, val = strip_meta(key, val)

    temp = new_data.get(node, {})

    if not temp.has_key('meta'):
        temp['meta'] = {key: [val]}
    elif not temp['meta'].has_key(key):
        temp['meta'][key] = [val]
    # a page can not have more than one label, shapefile etc
    elif key in special_attrs:
        temp['meta'][key] = [val]
    else:
        temp['meta'][key].append(val)

    new_data[node] = temp

def getlinktype(augdata):
    linktype = ''
    if len(augdata) > 1:
        linktype = augdata[0]
    return linktype

def add_meta(new_data, pagename, hit):
    # decode to target charset, grab comma-separated key,val
    hit = hit[11:-3]
    args = hit.split(',')

    # If no data, continue
    if len(args) < 2:
        return

    key = args[0]
    val = ','.join(args[1:])

    # Do not handle empty metadata, except empty labels
    if key != 'gwikilabel':
        val = val.strip()
    if not val:
        return

    # Values to be handled in graphs
    if key in special_attrs:
        shelve_set_attribute(new_data, pagename, key, val)
        # If color defined, set page as filled
        if key == 'fillcolor':
            shelve_set_attribute(new_data, pagename, 'style', 'filled')
        return

    # Save to shelve's metadata list
    shelve_set_attribute(new_data, pagename, key, val)

def add_include(new_data, pagename, hit):
    hit = hit[11:-3]
    pagearg = hit.split(',')[0]

    # If no data, continue
    if not pagearg:
        return

    temp = new_data.get(pagename, {})
    temp.setdefault('include', list()).append(pagearg)
    new_data[pagename] = temp

def parse_link(wikiparse, hit, type):
    replace = getattr(wikiparse, '_' + type + '_repl')
    attrs = replace(hit)

    if len(attrs) == 4:
        # Attachments, eg:
        # URL   = Page?action=AttachFile&do=get&target=k.txt
        # name  = Page/k.txt        
        nodename = attrs[1]
        nodeurl = attrs[0]
    elif len(attrs) == 3:
        # Local pages
        # Name of node for local nodes = pagename
        nodename = attrs[1]
        nodeurl = attrs[0]
        # To prevent subpagenames from sucking
        if nodeurl.startswith('/'):
            nodeurl = './' + nodename
    elif len(attrs) == 2:
        # Name of other nodes = url
        nodeurl = attrs[0]
        nodename = nodeurl

        # Change name for different type of interwikilinks
        if type == 'interwiki':
            nodename = hit
        elif type == 'url_bracket':
            # Interwikilink in brackets?
            iw = re.search(r'\[(?P<iw>.+?)[\] ]',
                           hit).group('iw')

            if iw.split(":")[0] == 'wiki':
                iw = iw.split(None, 1)[0]
                iw = iw[5:].replace('/', ':', 1)
                nodename = iw
        # Interwikilink turned url?
        elif type == 'url':
            if hit.split(":")[0] == 'wiki':
                iw = hit[5:].replace('/', ':', 1)
                nodename = iw
    else:
        # Catch-all
        return "", "", ""

    # augmented links, eg. [:PaGe:Ooh: PaGe]
    augdata = [x.strip() for x in attrs[-1].split(': ')]

    linktype = getlinktype(augdata)

    return nodename, nodeurl, linktype

def add_link(new_data, pagename, nodename, nodeurl, linktype, hit):
    edge = [pagename, nodename]

# in-links were here, but as they were never used, YAGNI
#    if linktype.endswith('From'):
#        linktype = linktype[:-4]
#        edge.reverse()

    shelve_add_in(new_data, edge, linktype)
    shelve_add_out(new_data, edge, linktype, hit)

def parse_text(request, page, text):
    new_data = {}
    pagename = page.page_name

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

    in_processing_instructions = True

    for line in lines:

        # Have to handle the whole processing instruction shebang
        # in order to handle ACL:s correctly
        if in_processing_instructions:
            found = False
            for pi in ("##", "#format", "#refresh", "#redirect", "#deprecated",
                       "#pragma", "#form", "#acl", "#language"):
                if line.lower().startswith(pi):
                    found = True
                    if pi == '#acl':
                        temp = new_data.get(pagename, {})
                        temp['acl'] = line[5:]
                        new_data[pagename] = temp

            if not found:
                in_processing_instructions = False
            else:
                continue

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

                # Handling of MetaData- and Include-macros
                elif type == 'macro' and not inpre:
                    if hit.startswith('[[MetaData'):
                        add_meta(new_data, pagename, hit)

                    if hit.startswith('[[Include'):
                        add_include(new_data, pagename, hit)

                # Handling of links
                elif type in linktypes and not inpre:
                    # If we just came from a dict, which saved a typed
                    # link, do not save it again
                    if dicturl:
                        dicturl = False
                        continue

                    name, url, linktype = parse_link(wikiparse, hit, type)

                    if name:
                        add_link(new_data, pagename, name, url, linktype, hit)

                # Links and metadata defined in a definition list
                elif type == 'dl' and not inpre:
                    data = line.split('::')
                    key, val = data[0], '::'.join(data[1:])
                    key = key.lstrip()

                    if not key:
                        continue

                    # Try to find if the value points to a link
                    matches = all_re.match(val.lstrip())
                    if matches:
                        # Take all matches if hit non-empty
                        # and hit type in linktypes
                        match = [(type, hit) for type, hit in
                                 matches.groupdict().iteritems()
                                 if hit is not None \
                                 and type in linktypes]

                        # If link, 
                        if match:
                            type, hit = match[0]

                            # and nothing but link, save as link
                            if hit == val.strip():

                                val = val.strip()
                                name, url, linktype = parse_link(wikiparse,\
                                                                 hit, type)

                                # Take linktype from the dict key
                                linktype = getlinktype([x for x in key, val])

                                if name:
                                    add_link(new_data, pagename, 
                                             name, url, linktype, hit)

                                    # The val will also be parsed by
                                    # Moin's link parser -> need to
                                    # have state in the loop that this
                                    # link has already been saved
                                    dicturl = True

                    if dicturl:
                        continue

                    # If it was not link, save as metadata. 
                    add_meta(new_data, pagename,
                             "[[MetaData(%s,%s)]]" % (key, val))

    # Add the page categories as links too
    _, categories = parse_categories(request, text)
    for category in categories:
        name, url, linktype = parse_link(wikiparse, category, "word")
        if name:
            add_link(new_data, pagename, 
                     name, url, "gwikicategory", category)

    return new_data

def execute(pagename, request, text, pagedir, page):
    # Skip MoinEditorBackups
    if pagename.endswith('/MoinEditorBackup'):
        return

    # Get new data from parsing the page
    new_data = parse_text(request, page, text)

    add_out = dict()
    lit_out = dict()
    del_out = dict()

    add_in = dict()
    del_in = dict()

    # Code for making our which edges have changed.
    # We only want to save changes, not all the data,
    # as edges have a larger time footprint while saving.
    for page in new_data:
        # Get a copy of current data
        old_data = request.graphdata.get(page, {})

        add_out.setdefault(page, list())
        lit_out.setdefault(page, list())
        del_out.setdefault(page, list())

        add_in.setdefault(page, list())
        del_in.setdefault(page, list())

        old_keys = set(old_data.get('out', {}).keys())
        new_keys = set(new_data.get(page, {}).get('out', {}).keys())
        changed_keys = old_keys.intersection(new_keys)

        # Changed edges (destinations changed, or order changed)
        for key in changed_keys:
            for i, val in enumerate(old_data['out'][key]):

                if len(new_data[page]['out'][key]) <= i:
                    del_out[page].append((key, val))

                elif val != new_data[pagename]['out'][key][i]:
                    add_out[page].append((key, 
                                          new_data[pagename]['out'][key][i]))
                    lit_out[page].append(new_data[pagename]['lit'][key][i])
                    del_out[page].append((key, val))

        # Added edges
        for key in new_keys.difference(old_keys):
            for i, val in enumerate(new_data[pagename]['out'][key]):
                add_out[page].append((key, val))
                lit_out[page].append(new_data[pagename]['lit'][key][i])

        # Deleted edges
        for key in old_keys.difference(new_keys):
            for val in old_data['out'][key]:
                del_out[page].append((key, val))

        add_in[page] = copy(add_out[page])
        del_in[page] = copy(del_out[page])
        changes = set(add_in[page] + del_in[page])

        # Adding and removing in-links are the most expensive operation in a
        # shelve, so we'll try to minimise them. This is possible as we do not
        # have to care about preserving order of in-links (not defined).
        for key in changed_keys:
            for val in changes:
                add_count = add_in[page].count(val)
                del_count = del_in[page].count(val)

                if not add_count or not del_count:
                    continue

                change_count = add_count - del_count

                # If in-links added and deleted as many times, 
                # there are effectively no changes to be saved
                if change_count == 0:
                    for x in range(add_count):
                        del_in[page].remove(val)
                        add_in[page].remove(val)

                elif change_count < 0:
                    for x in range(abs(change_count)):
                        del_in[page].remove(val)

                else:
                    for x in range(abs(change_count)):
                        add_in[page].remove(val)

    # Insert metas and other stuff from parsed content
    cur_time = time()

    temp = request.graphdata.get(pagename, {'time': cur_time, 'saved': True})
    temp['meta'] = new_data.get(pagename, dict()).get('meta', dict())
    temp['acl'] = new_data.get(pagename, dict()).get('acl', '')
    temp['include'] = new_data.get(pagename, dict()).get('include', list())
    temp['mtime'] = cur_time
    temp['saved'] = True
    request.graphdata[pagename] = temp

    # Release ReadLock (from the previous reads), make WriteLock
    request.lock.release()
    request.lock = WriteLock(request.cfg.data_dir, timeout=10.0)
    request.lock.acquire()

    # Save the links that need to be saved
    for page in add_out:
        for i, edge in enumerate(add_out[page]):
            linktype, dst = edge
            hit = lit_out[page][i]
            shelve_add_out(request.graphdata, [pagename, dst], linktype, hit)
    for page in add_in:
        for edge in add_in[page]:
            linktype, dst = edge
            shelve_add_in(request.graphdata, [dst, pagename], linktype)

    for page in del_out:
        for edge in del_out[page]:
            linktype, dst = edge
            shelve_remove_out(request.graphdata, [dst, pagename], [linktype])
    for page in del_in:
        for edge in del_in[page]:
            linktype, dst = edge
            shelve_remove_in(request.graphdata, [pagename, dst], [linktype])

    request.lock.release()
