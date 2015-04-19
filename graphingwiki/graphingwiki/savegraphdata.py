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

from time import time

# MoinMoin imports
from MoinMoin.parser.text_moin_wiki import Parser
from MoinMoin.wikiutil import importPlugin, get_processing_instructions
from MoinMoin.Page import Page 
from MoinMoin.wikiutil import AbsPageName
from MoinMoin import config

# gwiki imports
from graphingwiki.util import (node_type, SPECIAL_ATTRS, SAVED_PAGE, SAVED_NONE,
                               NO_TYPE, delete_moin_caches, filter_categories)

def parse_categories(request, text):
    r"""
    Parse category names from the page. Return a list of parsed categories,
    list of the preceding text lines and a list of the lines with categories.

    >>> from graphingwiki.tests import doctest_request
    >>> request = doctest_request()
    >>> parse_categories(request, "CategoryTest")
    (['CategoryTest'], [], ['CategoryTest'])

    Take into account only the categories that come after all other text
    (excluding whitespaces):

    >>> parse_categories(request, "Blah\nCategoryNot blah\nCategoryTest\n")
    (['CategoryTest'], ['Blah', 'CategoryNot blah'], ['CategoryTest', ''])

    The line lists are returned in a way that the original text can be
    easily reconstructed from them.

    >>> original_text = "Blah\nCategoryNot blah\n--------\nCategoryTest\n"
    >>> _, head, tail = parse_categories(request, original_text)
    >>> tail[0] == "--------"
    True
    >>> "\n".join(head + tail) == original_text
    True

    >>> original_text = "Blah\nCategoryNot blah\nCategoryTest\n"
    >>> _, head, tail = parse_categories(request, original_text)
    >>> "\n".join(head + tail) == original_text
    True

    Regression test, bug #540: Pages with only categories (or whitespaces) 
    on several lines don't get parsed correctly:

    >>> parse_categories(request, "\nCategoryTest")
    (['CategoryTest'], [''], ['CategoryTest'])
    """

    other_lines = text.splitlines()
    if text.endswith("\n"):
        other_lines.append("")

    categories = list()
    category_lines = list()
    unknown_lines = list()

    # Start looking at lines from the end to the beginning
    while other_lines:
        if not other_lines[-1].strip() or other_lines[-1].startswith("##"):
            unknown_lines.insert(0, other_lines.pop())
            continue

        # TODO: this code is broken, will not work for extended links
        # categories, e.g ["category hebrew"]
        candidates = other_lines[-1].split()
        confirmed = filter_categories(request, candidates)

        # A category line is defined as a line that contains only categories
        if len(confirmed) < len(candidates):
            # The line was not a category line
            break

        categories.extend(confirmed)
        category_lines[:0] = unknown_lines
        category_lines.insert(0, other_lines.pop())
        unknown_lines = list()

    if other_lines and re.match("^\s*-{4,}\s*$", other_lines[-1]):
        category_lines[:0] = unknown_lines
        category_lines.insert(0, other_lines.pop())
    else:
        other_lines.extend(unknown_lines)
    return categories, other_lines, category_lines


def parse_text(request, page, text):
    pagename = page.page_name
    
    newreq = request
    newreq.page = lcpage = LinkCollectingPage(newreq, pagename, text)
    parserclass = importPlugin(request.cfg, "parser",
                               'link_collect', "Parser")
    myformatter = importPlugin(request.cfg, "formatter",
                               'nullformatter', "Formatter")
    lcpage.formatter = myformatter(newreq)
    lcpage.formatter.page = lcpage
    p = parserclass(lcpage.get_raw_body(), newreq, formatter=lcpage.formatter)
    lcpage.parser = p
    lcpage.format(p)
    
    # These are the match types that really should be noted
    linktypes = ["wikiname_bracket", "word",                  
                 "interwiki", "url", "url_bracket"]
    
    new_data = dict_with_getpage()

    # Add the page categories as links too
    categories, _, _ = parse_categories(request, text)

    # Process ACL:s
    pi, _ = get_processing_instructions(text)
    for verb, args in pi:
        if verb == u'acl':
            # Add all ACL:s on multiple lines to an one-lines
            acls = new_data.get(pagename, dict()).get('acl', '')
            acls = acls.strip() + args
            new_data.setdefault(pagename, dict())['acl'] = acls

    for metakey, value in p.definitions.iteritems():
        for ltype, item in value:
            dnode = None

            if  ltype in ['url', 'wikilink', 'interwiki', 'email']:
                dnode = item[1]
                if '#' in dnode:
                    # Fix anchor links to point to the anchor page
                    url = False
                    for schema in config.url_schemas:
                        if dnode.startswith(schema):
                            url = True
                    if not url:
                        # Do not fix URLs
                        if dnode.startswith('#'):
                            dnode = pagename
                        else:
                            dnode = dnode.split('#')[0]
                if (dnode.startswith('/') or
                    dnode.startswith('./') or
                    dnode.startswith('../')):
                    # Fix relative links
                    dnode = AbsPageName(pagename, dnode)

                hit = item[0]
            elif ltype == 'category':
                # print "adding cat", item, repr(categories)
                dnode = item
                hit = item
                if item in categories:
                    add_link(new_data, pagename, dnode, 
                             u"gwikicategory")
            elif ltype == 'meta':
                add_meta(new_data, pagename, (metakey, item))
            elif ltype == 'include':
                # No support for regexp includes, for now!
                if not item[0].startswith("^"):
                    included = AbsPageName(pagename, item[0])
                    add_link(new_data, pagename, included, u"gwikiinclude")

            if dnode:
                add_link(new_data, pagename, dnode, metakey)

    return new_data

def strip_meta(key, val):
    key = key.strip()
    val = val.strip()

    # retain empty labels
    if key == 'gwikilabel' and not val:
        val = ' '        

    return key, val

def add_link(new_data, pagename, nodename, linktype):
    edge = [pagename, nodename]

    add_in(new_data, edge, linktype)
    add_out(new_data, edge, linktype)


def add_in(new_data, (frm, to), linktype):
    "Add in-links from current node to local nodes"

    if hasattr(new_data, 'add_in'):
        new_data.add_in((frm, to), linktype)
        return

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


def add_out(new_data, (frm, to), linktype):
    "Add out-links from local nodes to current node"

    if hasattr(new_data, 'add_out'):
        new_data.add_out((frm, to), linktype)
        return

    if not linktype:
        linktype = NO_TYPE

    temp = new_data.get(frm, {})
    
    if not temp.has_key(u'out'):
        temp[u'out'] = {linktype: [to]}
    elif not temp[u'out'].has_key(linktype):
        temp[u'out'][linktype] = [to]
    else:
        temp[u'out'][linktype].append(to)

    new_data[frm] = temp


def remove_in(new_data, (frm, to), linktype):
    "Remove in-links from local nodes to current node"

    if hasattr(new_data, 'remove_in'):
        new_data.remove_in((frm, to), linktype)
        return

    temp = new_data.getpage(to)
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

def remove_out(new_data, (frm, to), linktype):
    "remove outlinks"

    if hasattr(new_data, 'remove_out'):
        new_data.remove_out((frm, to), linktype)
        return

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
            i = temp[u'out'][type].index(to)
            del temp[u'out'][type][i]

            # print "removed %s" % (repr(to))

        if not temp[u'out'][type]:
            del temp[u'out'][type]
            # print "%s empty" % (type)
            # print "Hey man, I think I did it!"

    new_data[frm] = temp


def set_attribute(new_data, node, key, val):
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
    val = val.strip()
    if key == 'gwikilabel' and not val:
        val = ' '        

    if not val:
        return

    # Values to be handled in graphs
    if key in SPECIAL_ATTRS:
        set_attribute(new_data, pagename, key, val)
        # If color defined, set page as filled
        if key == 'fillcolor':
            set_attribute(new_data, pagename, 'style', 'filled')
        return

    # Save to shelve's metadata list
    set_attribute(new_data, pagename, key, val)

# class dict_with_getpage(dict):
#     def getpage(self, pagename):
#         return self.setdefault(pagename, {})

#     def add_out(self, frm, to, linktype):
#         if not self.has_key(u'out'):
#             self[u'out'] = {linktype: [to]}
#         elif not self[u'out'].has_key(linktype):
#             self[u'out'][linktype] = [to]
#         else:
#             self[u'out'][linktype].append(to)

dict_with_getpage = dict

def changed_meta(request, pagename, old_outs, new_data):
    add_out = dict_with_getpage()
    del_out = dict_with_getpage()

    add_in = dict_with_getpage()
    del_in = dict_with_getpage()

    for page in new_data:
        add_in.setdefault(page, list())
        del_in.setdefault(page, list())

    # Code for making out which edges have changed.
    # We only want to save changes, not all the data,
    # as edges have a larger time footprint while saving.

    add_out.setdefault(pagename, list())
    del_out.setdefault(pagename, list())

    old_keys = set(old_outs.keys())
    new_keys = set(new_data.get(pagename, {}).get(u'out', {}).keys())
    changed_keys = old_keys.intersection(new_keys)

    # Changed edges == keys whose values have experienced changes
    for key in changed_keys:
        new_edges = len(new_data[pagename][u'out'][key])
        old_edges = len(old_outs[key])

        for i in range(max(new_edges, old_edges)):

            # old data had more links, delete old
            if new_edges <= i:
                val = old_outs[key][i]

                del_out[pagename].append((key, val))

                # Only local pages will have edges and metadata
                if node_type(request, val) == 'page':
                    del_in.setdefault(val, list()).append((key, pagename))

            # new data has more links, add new
            elif old_edges <= i:
                val = new_data[pagename][u'out'][key][i]

                add_out[pagename].append((key, val))

                # Only save in-links to local pages, not eg. url or interwiki
                if node_type(request, val) == 'page':
                    add_in.setdefault(val, list()).append((key, pagename))

            # check if the link i has changed
            else:
                val = old_outs[key][i]
                new_val = new_data[pagename][u'out'][key][i]

                if val == new_val:
                    continue

                # link changed, replace old link with new
                # add and del out-links
                add_out[pagename].append((key, new_val))

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

            add_out[pagename].append((key, val))

            # Only save in-links to local pages, not eg. url or interwiki
            if node_type(request, val) == 'page':
                add_in.setdefault(val, list()).append((key, pagename))

    # Deleted edges
    for key in old_keys.difference(new_keys):
        for val in old_outs[key]:

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

    return add_out, del_out, add_in, del_in

def _clear_page(request, pagename):
    if hasattr(request.graphdata, 'clear_page'):
        request.graphdata.clear_page(pagename)
        return
    # Do not delete in-links! It will break graphs, categories and whatnot
    if not request.graphdata[pagename].get('in', {}):
        del request.graphdata[pagename]
    else:
        request.graphdata[pagename][u'saved'] = SAVED_NONE
        del request.graphdata[pagename][u'mtime']
        del request.graphdata[pagename][u'acl']
        del request.graphdata[pagename][u'meta']

def execute(pagename, request, text, pageitem, saved=SAVED_PAGE):
    # saved: 2 for normal pages, 1 for lazy, 0 for not saved at all
    try:
        return execute2(pagename, request, text, pageitem, saved)
    except:
        request.graphdata.abort()
        raise

def execute2(pagename, request, text, pageitem, saved):
    # Skip MoinEditorBackups
    if pagename.endswith('/MoinEditorBackup'):
        return
    
    # parse_text, add_link, add_meta return dict with keys like
    # 'BobPerson' -> {u'out': {'friend': ['GeorgePerson']}}
    # (ie. same as what graphdata contains)

    # Get new data from parsing the page
    new_data = parse_text(request, pageitem, text)

    # Get a copy of current data
    old_outs = request.graphdata.get_out(pagename)

    changed_new_out, changed_del_out, changed_new_in, changed_del_in = \
        changed_meta(request, pagename, old_outs, new_data)

    # Insert metas and other stuff from parsed content
    cur_time = time()

    request.graphdata.set_page_meta_and_acl_and_mtime_and_saved(pagename,
                                                                new_data.get(pagename, dict()).get(u'meta', dict()),
                                                                new_data.get(pagename, dict()).get(u'acl', ''),
                                                                cur_time, saved)

    # Save the links that have truly changed
    for page in changed_del_out:
        for edge in changed_del_out[page]:
            #print 'delout', repr(page), edge
            linktype, dst = edge
            remove_out(request.graphdata, [page, dst], [linktype])

    for page in changed_del_in:
        for edge in changed_del_in[page]:
            #print 'delin', repr(page), edge
            linktype, src = edge
            remove_in(request.graphdata, [src, page], [linktype])

    for page in changed_new_out:
        for i, edge in enumerate(changed_new_out[page]):
            linktype, dst = edge
            #print 'addout', repr(page), edge
            add_out(request.graphdata, [page, dst], linktype)

    for page in changed_new_in:
        for edge in changed_new_in[page]:
            #print 'addin', repr(page), edge
            linktype, src = edge
            add_in(request.graphdata, [src, page], linktype)


    ## Remove deleted pages from the shelve
    # 1. Removing data at the moment of deletion
    # Deleting == saving a revision with the text 'deleted/n', then 
    # removing the revision. This seems to be the only way to notice.
    if text == 'deleted\n':
        _clear_page(request, pagename)
    else:
        # 2. Removing data when rehashing. 
        # New pages do not exist, but return a revision of 99999999 ->
        # Check these both to avoid deleting new pages.
        pf, rev, exists = pageitem.get_rev() 
        if rev != 99999999:
            if not exists:
                _clear_page(request, pagename)
    
    delete_moin_caches(request, pageitem)
    request.graphdata.post_save(pagename)

# - code below lifted from MetaFormEdit -

# Override Page.py to change the parser. This method has the advantage
# that it works regardless of any processing instructions written on
# page, including the use of other parsers
class LinkCollectingPage(Page):
    def __init__(self, request, page_name, content, **keywords):
        # Cannot use super as the Moin classes are old-style
        apply(Page.__init__, (self, request, page_name), keywords)
        self.set_raw_body(content)

    # It's important not to cache this, as the wiki thinks we are
    # using the default parser
    def send_page_content(self, request, notparser, body, format_args='',
                          do_cache=0, **kw):
        self.parser = importPlugin(request.cfg, "parser",
                                   'link_collect', "Parser")

        kw['format_args'] = format_args
        kw['do_cache'] = 0
        apply(Page.send_page_content, (self, request, self.parser, body), kw)

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
