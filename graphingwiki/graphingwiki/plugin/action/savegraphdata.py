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
from MoinMoin import caching

# graphlib imports
from graphingwiki.patterns import node_type, SPECIAL_ATTRS, NO_TYPE
from graphingwiki.editing import parse_categories

# Add in-links from current node to local nodes
def shelve_add_in(new_data, (frm, to), linktype):
    if not linktype:
        linktype = NO_TYPE

    temp = new_data.get(to, {})

    if not temp.has_key(u'in'):
        temp[u'in'] = {linktype: [frm]}
    elif not temp[u'in'].has_key(linktype):
        temp[u'in'][linktype] = [frm]
    else:
        temp[u'in'][linktype].append(frm)
        
    # Notification that the destination has changed
    temp[u'mtime'] = time()

    new_data[to] = temp

# Add out-links from local nodes to current node
def shelve_add_out(new_data, (frm, to), linktype, hit):
    if not linktype:
        linktype = NO_TYPE

    temp = new_data.get(frm, {})

    # Also add literal text (hit) for each link
    # eg, if out it SomePage, lit can be ["SomePage"]
    if not temp.has_key(u'out'):
        temp[u'out'] = {linktype: [to]}
        temp[u'lit'] = {linktype: [hit]}
    elif not temp[u'out'].has_key(linktype):
        temp[u'out'][linktype] = [to]
        temp[u'lit'][linktype] = [hit]
    else:
        temp[u'out'][linktype].append(to)
        temp[u'lit'][linktype].append(hit)

    new_data[frm] = temp

# Respectively, remove in-links
def shelve_remove_in(new_data, (frm, to), linktype):
    # import sys
    # sys.stderr.write('Starting to remove in\n')
    temp = new_data.get(to, {})
    if not temp.has_key(u'in'):
        return

    for type in linktype:
        # sys.stderr.write("Removing %s %s %s\n" % (frm, to, linktype))
        # eg. when the shelve is just started, it's empty
        if not temp[u'in'].has_key(type):
            # sys.stderr.write("No such type: %s\n" % type)
            continue
        if frm in temp[u'in'][type]:
            temp[u'in'][type].remove(frm)

            # Notification that the destination has changed
            temp[u'mtime'] = time()
            
        if not temp[u'in'][type]:
            del temp[u'in'][type]


    # sys.stderr.write("Hey man, I think I did it!\n")
    new_data[to] = temp

# Respectively, remove out-links
def shelve_remove_out(new_data, (frm, to), linktype):
    # print 'Starting to remove out'
    temp = new_data.get(frm, {})

    if not temp.has_key(u'out'):
        return 

    for type in linktype:
        # print "Removing %s %s %s" % (frm, to, linktype)
        # eg. when the shelve is just started, it's empty
        if not temp[u'out'].has_key(type):
            # print "No such type: %s" % type
            continue
        if to in temp[u'out'][type]:
            # As the literal text values for the links
            # are added at the same time, they have the
            # same index value
            i = temp[u'out'][type].index(to)
            del temp[u'out'][type][i]
            del temp[u'lit'][type][i]

            # print "removed %s" % (repr(to))

        if not temp[u'out'][type]:
            del temp[u'out'][type]
            del temp[u'lit'][type]
            # print "%s empty" % (type)
            # print "Hey man, I think I did it!"

    new_data[frm] = temp

def strip_meta(key, val):
    key = key.strip()
    if key != 'gwikilabel':
        val = val.strip()
    return key, val

def shelve_set_attribute(new_data, node, key, val):
    key, val = strip_meta(key, val)

    temp = new_data.get(node, {})

    if not temp.has_key(u'meta'):
        temp[u'meta'] = {key: [val]}
    elif not temp[u'meta'].has_key(key):
        temp[u'meta'][key] = [val]
    # a page can not have more than one label, shapefile etc
    elif key in SPECIAL_ATTRS:
        temp[u'meta'][key] = [val]
    else:
        temp[u'meta'][key].append(val)

    new_data[node] = temp

def add_meta(new_data, pagename, (key, val)):

    # Do not handle empty metadata, except empty labels
    if key != 'gwikilabel':
        val = val.strip()
    if not val:
        return

    # Values to be handled in graphs
    if key in SPECIAL_ATTRS:
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
    temp.setdefault(u'include', list()).append(pagearg)
    new_data[pagename] = temp

def parse_link(wikiparse, hit, type):
    replace = getattr(wikiparse, '_' + type + '_repl')
    attrs = replace(hit)

    nodename = attrs[0]
    linktype = ''

    # Bracketed links and attachments may return extra data 
    # (funnily enough, both with linktype url_bracket),
    # which may include linktype [:Page:LinkType: text].
    # This method of specifying linktype is considered quite 
    # deprecated, and support for it may later be removed.
    if type == 'url_bracket' and len(attrs) > 1:
        linktype = attrs[1]

    # Change name for different type of interwikilinks
    if type == 'interwiki':
        if not hit.startswith('Self'):
            nodename = hit
    elif type == 'url_bracket':
        # Interwikilink in brackets?
        iw = re.search(r'\[(?P<iw>.+?)[\] ]',
                       hit).group('iw')

        if iw.split(":")[0] == 'wiki':
            iw = iw.split(None, 1)[0]
            iw = iw[5:].replace('/', ':', 1)
            nodename = iw

        # Bracket URL:s with linktype [:PaGe:Ooh: PaGe]
        linktype = [x.strip() for x in linktype.split(': ')]
        if len(linktype) > 1:
            linktype = linktype[0]
        else:
            linktype = ''

    # Interwikilink turned url?
    elif type == 'url':
        if hit.split(":")[0] == 'wiki':
            iw = hit[5:].replace('/', ':', 1)
            nodename = iw

    return nodename, linktype

def add_link(new_data, pagename, nodename, linktype, hit):
    edge = [pagename, nodename]

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
                        temp[u'acl'] = line[5:]
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
                    if hit.startswith('[[Include'):
                        add_include(new_data, pagename, hit)

                # Handling of links
                elif type in linktypes and not inpre:
                    # If we just came from a dict, which saved a typed
                    # link, do not save it again
                    if dicturl:
                        dicturl = False
                        continue

                    name, linktype = parse_link(wikiparse, hit, type)

                    if name:
                        add_link(new_data, pagename, name, linktype, hit)

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

                                name, _ = parse_link(wikiparse,
                                                     hit, type)

                                if name:
                                    add_link(new_data, pagename, 
                                             name, key, hit)

                                    # The val will also be parsed by
                                    # Moin's link parser -> need to
                                    # have state in the loop that this
                                    # link has already been saved
                                    dicturl = True

                    if dicturl:
                        continue

                    # If it was not link, save as metadata. 
                    add_meta(new_data, pagename, (key, val))

    # Add the page categories as links too
    _, categories = parse_categories(request, text)
    for category in categories:
        name, linktype = parse_link(wikiparse, category, "word")
        if name:
            add_link(new_data, pagename, name, u"gwikicategory", category)

    return new_data

def changed_meta(request, pagename, old_data, new_data):
    add_out = dict()
    lit_out = dict()
    del_out = dict()

    add_in = dict()
    del_in = dict()

    for page in new_data:
        add_in.setdefault(page, list())
        del_in.setdefault(page, list())

    # Code for making our which edges have changed.
    # We only want to save changes, not all the data,
    # as edges have a larger time footprint while saving.

    add_out.setdefault(pagename, list())
    lit_out.setdefault(pagename, list())
    del_out.setdefault(pagename, list())

    old_keys = set(old_data.get(u'out', {}).keys())
    new_keys = set(new_data.get(pagename, {}).get(u'out', {}).keys())
    changed_keys = old_keys.intersection(new_keys)

    # Changed edges == keys whose values have experienced changes
    for key in changed_keys:
        new_edges = len(new_data[pagename][u'out'][key])
        old_edges = len(old_data[u'out'][key])

        for i in range(max(new_edges, old_edges)):

            # old data had more links, delete old
            if new_edges <= i:
                val = old_data[u'out'][key][i]
                lit = old_data[u'lit'][key][i]

                del_out[pagename].append((key, val))

                # Only local pages will have edges and metadata
                if node_type(request, val) == 'page':
                    del_in.setdefault(val, list()).append((key, pagename))

            # new data has more links, add new
            elif old_edges <= i:
                val = new_data[pagename][u'out'][key][i]
                lit = new_data[pagename][u'lit'][key][i]

                add_out[pagename].append((key, val))
                lit_out[pagename].append(lit)

                # Only save in-links to local pages, not eg. url or interwiki
                if node_type(request, val) == 'page':
                    add_in.setdefault(val, list()).append((key, pagename))

            # check if the link i has changed
            else:
                val = old_data[u'out'][key][i]
                new_val = new_data[pagename][u'out'][key][i]

                if val == new_val:
                    continue

                # link changed, replace old link with new
                lit = new_data[pagename][u'lit'][key][i]                

                # add and del out-links
                add_out[pagename].append((key, new_val))
                lit_out[pagename].append(lit)

                del_out[pagename].append((key, val))

                # Only save in-links to local pages, not eg. url or interwiki
                if node_type(request, new_val) == 'page':
                    add_in.setdefault(new_val, list()).append((key, pagename))
                # Only save in-links to local pages, not eg. url or interwiki
                if node_type(request, val) == 'page':
                    del_in.setdefault(val, list()).append((key, pagename))

    # Added edges of a new linktype
    for key in new_keys.difference(old_keys):
        for i, val in enumerate(new_data[pagename][u'out'][key]):
            lit = new_data[pagename][u'lit'][key][i]

            add_out[pagename].append((key, val))
            lit_out[pagename].append(lit)

            # Only save in-links to local pages, not eg. url or interwiki
            if node_type(request, val) == 'page':
                add_in.setdefault(val, list()).append((key, pagename))

    # Deleted edges
    for key in old_keys.difference(new_keys):
        for val in old_data[u'out'][key]:

            del_out[pagename].append((key, val))

            # Only local pages will have edges and metadata
            if node_type(request, val) == 'page':
                del_in.setdefault(val, list()).append((key, pagename))

    # Adding and removing in-links are the most expensive operation in a
    # shelve, so we'll try to minimise them. Eg. if page TestPage is
    #  a:: ["b"]\n a:: ["a"] 
    # and it is resaved as
    #  a:: ["a"]\n a:: ["b"]
    # the ordering of out-links in TestPage changes, but we do not have
    # to touch the in-links in pages a and b. This is possible because
    # in-links do not have any sensible order.
    for page in new_data:
        #print repr(page), add_in[page], del_in[page]

        changes = set(add_in[page] + del_in[page])

        #print changes

        for key, val in changes:
            #print 'change', repr(key), repr(val)

            add_count = add_in[page].count((key, val))
            del_count = del_in[page].count((key, val))

            if not add_count or not del_count:
                #print "No changes"
                #print
                continue

            change_count = add_count - del_count

            # If in-links added and deleted as many times, 
            # there are effectively no changes to be saved
            if change_count == 0:
                for x in range(add_count):
                    add_in[page].remove((key, val))
                    del_in[page].remove((key, val))
                    #print "No changes"

            elif change_count < 0:
                for x in range(abs(change_count)):
                    del_in[page].remove((key, val))
                    #print "No need to delete %s from %s" % (val, page)

            else:
                for x in range(abs(change_count)):
                    #print "No need to add %s to %s" % (val, page)
                    add_in[page].remove((key, val))

            #print

    #print

    return add_out, lit_out, del_out, add_in, del_in

def execute(pagename, request, text, pagedir, page):
    # Skip MoinEditorBackups
    if pagename.endswith('/MoinEditorBackup'):
        return

    pageitem = page

    # Get new data from parsing the page
    new_data = parse_text(request, page, text)

    # Get a copy of current data
    old_data = request.graphdata.get(pagename, {})

    add_out, lit_out, del_out, add_in, del_in = \
        changed_meta(request, pagename, old_data, new_data)

    # Insert metas and other stuff from parsed content
    cur_time = time()

    temp = request.graphdata.get(pagename, {})
    temp[u'meta'] = new_data.get(pagename, dict()).get(u'meta', dict())
    temp[u'acl'] = new_data.get(pagename, dict()).get(u'acl', '')
    temp[u'include'] = new_data.get(pagename, dict()).get(u'include', list())
    temp[u'mtime'] = cur_time
    temp[u'saved'] = True

    # Release ReadLock (from the previous reads), make WriteLock
    request.graphdata.writelock()

    request.graphdata[pagename] = temp
    # Save the links that have truly changed
    for page in del_out:
        for edge in del_out[page]:
            #print 'delout', repr(page), edge
            linktype, dst = edge
            shelve_remove_out(request.graphdata, [page, dst], [linktype])
    for page in del_in:
        for edge in del_in[page]:
            #print 'delin', repr(page), edge
            linktype, src = edge
            shelve_remove_in(request.graphdata, [src, page], [linktype])

    for page in add_out:
        for i, edge in enumerate(add_out[page]):
            linktype, dst = edge
            #print 'addout', repr(page), edge
            hit = lit_out[page][i]
            shelve_add_out(request.graphdata, [page, dst], linktype, hit)
    for page in add_in:
        for edge in add_in[page]:
            #print 'addin', repr(page), edge
            linktype, src = edge
            shelve_add_in(request.graphdata, [src, page], linktype)

    # Clear cache

    # delete pagelinks
    arena = pageitem
    key = 'pagelinks'
    cache = caching.CacheEntry(request, arena, key)
    cache.remove()

    # forget in-memory page text
    pageitem.set_raw_body(None)

    # clean the in memory acl cache
    pageitem.clean_acl_cache()

    request.graphdata.cache = dict()

    # clean the cache
    for formatter_name in ['text_html']:
        key = formatter_name
        cache = caching.CacheEntry(request, arena, key)
        cache.remove()

    request.graphdata.readlock()
