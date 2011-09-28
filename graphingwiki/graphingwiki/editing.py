# -*- coding: utf-8 -*-
"""
    Graphingwiki editing functions
     - Saving page contents or relevant metadata

    @copyright: 2007 by Juhani Eronen, Erno Kuusela and Joachim Viide
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import os
import re
import sys
import string
import socket
import copy
import operator

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from MoinMoin.action.AttachFile import getAttachDir, getFilename, _addLogEntry
from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin.wikiutil import importPlugin,  PluginMissingError, AbsPageName

from graphingwiki import underlay_to_pages, url_escape, url_unescape
from graphingwiki.util import nonguaranteeds_p, decode_page, encode_page
from graphingwiki.util import absolute_attach_name, filter_categories
from graphingwiki.util import NO_TYPE, SPECIAL_ATTRS, editable_p
from graphingwiki.util import category_regex, template_regex, encode

CATEGORY_KEY = "gwikicategory"
TEMPLATE_KEY = "gwikitemplate"

def macro_re(macroname):
    return re.compile(r'(?<!#)\s*?\[\[(%s)\((.*?)\)\]\]' % macroname)

metadata_re = macro_re("MetaData")

regexp_re = re.compile('^/.+/$')
# Dl_re includes newlines, if available, and will replace them
# in the sub-function
dl_re = re.compile('(^\s+(.+?):: (.+)$\n?)', re.M)
# From Parser, slight modification due to multiline usage
dl_proto_re = re.compile('(^\s+(.+?)::\s*$\n?)', re.M)
# Regex for adding new
dl_add = '^(\\s+?%s::\\s.+?)$'

default_meta_before = '^----'

# These are the match types for links that really should be noted
linktypes = ["wikiname_bracket", "word",
             "interwiki", "url", "url_bracket"]
def get_revisions(request, page):
    parse_text = importPlugin(request.cfg,
                              'action',
                              'savegraphdata',
                              'parse_text')
    
    alldata = dict()
    revisions = dict()

    pagename = page.page_name
    for rev in page.getRevList():
        revlink = '%s-gwikirevision-%d' % (pagename, rev)

        # Data about revisions is now cached to the graphdata
        # at the same time this is used.
        if request.graphdata.has_key(revlink):
            revisions[rev] = revlink
            continue

        # If not cached, parse the text for the page
        revpage = Page(request, pagename, rev=rev)
        text = revpage.get_raw_body()
        alldata = parse_text(request, revpage, text)
        if alldata.has_key(pagename):
            alldata[pagename].setdefault('meta', 
                                         dict())[u'gwikirevision'] = \
                                         [unicode(rev)]
            # Do the cache.
            request.graphdata.cacheset(revlink, alldata[pagename])

            # Add revision as meta so that it is shown in the table
            revisions[rev] = revlink

    pagelist = [revisions[x] for x in sorted(revisions.keys(), 
                                             key=ordervalue, 
                                             reverse=True)]

    metakeys = set()
    for page in pagelist:
        for key in request.graphdata.get_metakeys(page):
            metakeys.add(key)
    metakeys = sorted(metakeys, key=ordervalue)

    return pagelist, metakeys

def get_properties(request, key):
    properties = get_metas(request, '%sProperty' % (key), 
                           ['constraint', 'description', 'hint', 'hidden', 'default'])
    for prop in properties:
        if not properties[prop]:
            properties[prop] = ''
        else:
            properties[prop] = properties[prop][0]

    return properties

def getmeta_to_table(input):
    keyoccur = dict()

    keys = list()
    for key in input[0]:
        keyoccur[key] = 1
        keys.append(key)

    for row in input[1:]:
        for i, key in enumerate(row[1:]):
            keylen = len(key)
            if keylen > keyoccur[keys[i]]:
                keyoccur[keys[i]] = keylen

    table_keys = ['Page name']

    for key in input[0]:
        table_keys.extend([key] * keyoccur[key])

    table = [table_keys]

    for vals in input[1:]:
        row = [vals[0]]
        for i, val in enumerate(vals[1:]):
            val.extend([''] * (keyoccur[keys[i]] - len(val)))
            row.extend(val)
        table.append(row)

    return table    

def parse_categories(request, text):
    r"""
    Parse category names from the page. Return a list of parsed categories,
    list of the preceding text lines and a list of the lines with categories.

    >>> request = _doctest_request()
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

def edit_categories(request, savetext, action, catlist):
    """
    >>> request = _doctest_request()
    >>> s = "= @PAGE@ =\\n" + \
        "[[TableOfContents]]\\n" + \
        "[[LinkedIn]]\\n" + \
        "----\\n" + \
        "CategoryIdentity\\n" +\
        "##fslsjdfldfj\\n" +\
        "CategoryBlaa\\n"
    >>> edit_categories(request, s, 'add', ['CategoryEi'])
    u'= @PAGE@ =\\n[[TableOfContents]]\\n[[LinkedIn]]\\n----\\nCategoryBlaa CategoryIdentity CategoryEi\\n'
    >>> edit_categories(request, s, 'set', ['CategoryEi'])
    u'= @PAGE@ =\\n[[TableOfContents]]\\n[[LinkedIn]]\\n----\\nCategoryEi\\n'
    >>> s = "= @PAGE@ =\\n" + \
       "[[TableOfContents]]\\n" + \
       "[[LinkedIn]]\\n" + \
       "----\\n" + \
       "## This is not a category line\\n" +\
       "CategoryIdentity hlh\\n" +\
       "CategoryBlaa\\n"
    >>> 
    >>> edit_categories(request, s, 'add', ['CategoryEi'])
    u'= @PAGE@ =\\n[[TableOfContents]]\\n[[LinkedIn]]\\n----\\n## This is not a category line\\nCategoryIdentity hlh\\n----\\nCategoryBlaa CategoryEi\\n'
    >>> edit_categories(request, s, 'set', ['CategoryEi'])
    u'= @PAGE@ =\\n[[TableOfContents]]\\n[[LinkedIn]]\\n----\\n## This is not a category line\\nCategoryIdentity hlh\\n----\\nCategoryEi\\n'
    """

    # Filter out anything that is not a category
    catlist = filter_categories(request, catlist)
    confirmed, lines, _ = parse_categories(request, savetext)

    # Remove the empty lines from the end
    while lines and not lines[-1].strip():
        lines.pop()

    # Check out which categories we are going to write back
    if action == "set":
        categories = list(catlist)
    elif action == "del":
        categories = list(confirmed)
        for category in catlist:
            if category in categories:
                categories.remove(category)
    else:
        categories = list(confirmed)
        for category in catlist:
            if category not in categories:
                categories.append(category)

    if categories:
        lines.append(u"----")
        lines.append(" ".join(categories))

    return u"\n".join(lines) + u"\n"

def link_to_attachment(globaldata, target):
    if isinstance(target, unicode):
        target = url_escape(encode(target))
    
    try:
        targetPage = globaldata.getpage(target)
    except KeyError:
        pass
    else:
        targetMeta = targetPage.get("meta", dict())
        url = targetMeta.get("gwikiURL", set([""]))
        if url:
            url = url.pop()
            # If the URL attribute of the target looks like the
            # target is a local attachment, correct the link
            if 'AttachFile' in url and url.startswith('".'):
                target = 'attachment:' + target.replace(' ', '_')

    target = target.strip('"')
    if not target.startswith('attachment:'):
        target = unicode(url_unescape(target), config.charset)
    else:
        target = unicode(target, config.charset)
    target = target.replace('\\"', '"')

    return target

def absolute_attach_name(quoted, target):
    abs_method = target.split(':')[0]

    # Pages from MetaRevisions may have ?action=recall, breaking attach links
    if '?' in quoted:
        quoted = quoted.split('?', 1)[0]

    if abs_method in ["attachment", "drawing"] and not '/' in target:
        target = target.replace(':', ':%s/' % (quoted.replace(' ', '_')), 1)

    return target

def inlinks_key(request, loadedPage, checkAccess=True):
    inLinks = set()
    # Gather in-links regardless of type
    for linktype in loadedPage.get("in", dict()):
        for page in loadedPage['in'][linktype]:
            if checkAccess:
                if not request.user.may.read(page):
                    continue
            inLinks.add((linktype, page))

    inLinks = ['[[%s]]' % (y) for x, y in inLinks]

    return inLinks

# Fetch only the link information for the selected page
def get_links(request, name, metakeys, checkAccess=True, **kw):
    metakeys = set([x for x in metakeys if not '->' in x])
    pageLinks = dict([(key, list()) for key in metakeys])

    loadedPage = request.graphdata.getpage(name)

    loadedOuts = loadedPage.get("out", dict())

    # Add values
    for key in metakeys & set(loadedOuts):
        for value in loadedOuts[key]:
            pageLinks[key].append(value)
            
    return pageLinks

def is_meta_link(value):
    from MoinMoin.parser.text_moin_wiki import Parser

    vals = Parser.scan_re.search(value)
    if not vals:
        return str()

    vals = [x for x, y in vals.groupdict().iteritems() if y]
    for val in vals:
        if val in ['word', 'link', 'transclude', 'url']:
            return 'link'
        if val in ['interwiki', 'email', 'include']:
            return val
    return str()

def metas_to_abs_links(request, page, values):
    new_values = list()
    stripped = False
    for value in values:
        if is_meta_link(value) != 'link':
            new_values.append(value)
            continue
        if ((value.startswith('[[') and value.endswith(']]')) or
            (value.startswith('{{') and value.endswith('}}'))):
            stripped = True
            value = value.lstrip('[')
            value = value.lstrip('{')
        attachment = ''
        for scheme in ('attachment:', 'inline:', 'drawing:'):
            if value.startswith(scheme):
                if len(value.split('/')) == 1:
                    value = ':'.join(value.split(':')[1:])
                    if not '|' in value:
                        # If page does not have descriptive text, try
                        # to shorten the link to the attachment name.
                        value = "%s|%s" % (value.rstrip(']').rstrip('}'), value)
                    value = "%s%s/%s" % (scheme, page, value)
                else:
                    att_page = value.split(':')[1]
                    if (att_page.startswith('./') or
                        att_page.startswith('/') or
                        att_page.startswith('../')):
                        attachment = scheme
                        value = ':'.join(value.split(':')[1:])
        if (value.startswith('./') or
            value.startswith('/') or
            value.startswith('../')):
            value = AbsPageName(page, value)
        if value.startswith('#'):
            value = page + value

        value = attachment + value
        if stripped:
            if value.endswith(']'):
                value = '[[' + value 
            elif value.endswith('}'):
                value = '{{' + value 
        new_values.append(value)

    return new_values

# Fetch requested metakey value for the given page.
def get_metas(request, name, metakeys, checkAccess=True, 
              includeGenerated=True, formatLinks=False, **kw):
    if not includeGenerated:
        metakeys = [x for x in metakeys if not '->' in x]

    metakeys = set(metakeys)
    pageMeta = dict([(key, list()) for key in metakeys])

    if checkAccess:
        if not request.user.may.read(name):
            return pageMeta

    loadedPage = request.graphdata.getpage(name)

    # Make a real copy of loadedOuts and loadedMeta for tracking indirection
    loadedOuts = dict()
    outs = request.graphdata.get_out(name)
    for key in outs:
        loadedOuts[key] = list(outs[key])

    loadedMeta = dict()
    metas = request.graphdata.get_meta(name)
    for key in metas:
        loadedMeta.setdefault(key, list())
        if formatLinks:
            values = metas_to_abs_links(request, name, metas[key])
        else:
            values = metas[key]
        loadedMeta[key].extend(values)

    loadedOutsIndir = dict()
    for key in loadedOuts:
        loadedOutsIndir.setdefault(key, set()).update(loadedOuts[key])

    if includeGenerated:
        # Handle inlinks separately
        if 'gwikiinlinks' in metakeys:
            inLinks = inlinks_key(request, loadedPage, checkAccess=checkAccess)

            loadedOuts['gwikiinlinks'] = inLinks

        # Meta key indirection support
        for key in metakeys:
            def add_matching_redirs(curpage, curkey, prev=''):
                args = curkey.split('->')
                newkey = '->'.join(args[2:])
                
                last = False

                if not args:
                    return
                if len(args) in [1, 2]:
                    last = True

                if len(args) == 1:
                    linked, target_key = prev, args[0]
                else:
                    linked, target_key = args[:2]

                pages = request.graphdata.get_out(curpage).get(linked, set())

                for indir_page in set(pages):
                    # Relative pages etc
                    indir_page = \
                        wikiutil.AbsPageName(request.page.page_name, 
                                             indir_page)

                    if request.user.may.read(indir_page):
                        pagedata = request.graphdata.getpage(indir_page)

                        outs = pagedata.get('out', dict())
                        metas = pagedata.get('meta', dict())

                        # Add matches at first round
                        if last:
                            if target_key in metas:
                                loadedMeta.setdefault(key, list())
                                if formatLinks:
                                    values = metas_to_abs_links(
                                        request, indir_page, metas[target_key])
                                else:
                                    values = metas[target_key]
                                loadedMeta[key].extend(values)
                            continue

                        elif not target_key in outs:
                            continue

                        # Handle inlinks separately 
                        if 'gwikiinlinks' in metakeys: 
                            inLinks = inlinks_key(request, loadedPage,  
                                                  checkAccess=checkAccess) 

                            loadedOuts[key] = inLinks 
                            continue 

                        add_matching_redirs(indir_page, newkey, target_key)

            add_matching_redirs(name, key)

    # Add values
    for key in metakeys & set(loadedMeta):
        for value in loadedMeta[key]:
            pageMeta[key].append(value)

    # Add gwikicategory as a special case, as it can be metaedited
    if loadedOuts.has_key('gwikicategory'):
        # Empty (possible) current gwikicategory to fix a corner case
        pageMeta['gwikicategory'] = loadedOuts['gwikicategory']
            
    return pageMeta

def get_pages(request):
    def group_filter(name):
        # aw crap, SystemPagesGroup is not a system page
        if name == 'SystemPagesGroup':
            return False
        if wikiutil.isSystemPage(request, name):
            return False
        return request.user.may.read(name)

    return request.rootpage.getPageList(filter=group_filter)

def remove_preformatted(text):
    # Before setting metas, remove preformatted areas
    preformatted_re = re.compile('((^ [^:]+?:: )?({{{[^{]*?}}}))', re.M|re.S)
    wiki_preformatted_re = re.compile('{{{\s*\#\!wiki', re.M|re.S)

    keys_to_markers = dict()
    markers_to_keys = dict()

    # Replace with unique format strings per preformatted area
    def replace_preformatted(mo):
        key, preamble, rest = mo.groups()

        # Cases 594, 596, 759: ignore preformatted section starting on
        # the metakey line
        if preamble:
            return key

        # Do not remove wiki-formatted areas, we need the keys in them
        if wiki_preformatted_re.search(key):
            return key

        # All other areas should be removed
        marker = "%d-%s" % (mo.start(), md5(repr(key)).hexdigest())
        while marker in text:
            marker = "%d-%s" % (mo.start(), md5(marker).hexdigest())

        keys_to_markers[key] = marker
        markers_to_keys[marker] = key

        return marker

    text = preformatted_re.sub(replace_preformatted, text)

    return text, keys_to_markers, markers_to_keys

def edit_meta(request, pagename, oldmeta, newmeta):
    page = PageEditor(request, pagename)

    text = page.get_raw_body()
    text = replace_metas(request, text, oldmeta, newmeta)

    # PageEditor.saveText doesn't allow empty texts
    if not text:
        text = u" "

    try:
        msg = page.saveText(text, 0)
    except page.Unchanged:
        msg = u'Unchanged'

    return msg

def add_meta_regex(request, inclusion, newval, oldtext):
    """
    >>> request = _doctest_request()
    >>> s = "= @PAGE@ =\\n" + \
        "[[TableOfContents]]\\n" + \
        "[[LinkedIn]]\\n" + \
        "----\\n" + \
        "CategoryIdentity\\n" +\
        "##fslsjdfldfj\\n" +\
        "CategoryBlaa\\n"
    >>> 
    >>> add_meta_regex(request, u' ööö ää:: blaa', u'blaa', s)
    u'= @PAGE@ =\\n[[TableOfContents]]\\n[[LinkedIn]]\\n \\xc3\\xb6\\xc3\\xb6\\xc3\\xb6 \\xc3\\xa4\\xc3\\xa4:: blaa\\n----\\nCategoryIdentity\\n##fslsjdfldfj\\nCategoryBlaa\\n'
    >>> 
    >>> request.cfg.gwiki_meta_after = '^----'
    >>> 
    >>> add_meta_regex(request, u' ööö ää:: blaa', u'blaa', s)
    u'= @PAGE@ =\\n[[TableOfContents]]\\n[[LinkedIn]]\\n----\\n \\xc3\\xb6\\xc3\\xb6\\xc3\\xb6 \\xc3\\xa4\\xc3\\xa4:: blaa\\nCategoryIdentity\\n##fslsjdfldfj\\nCategoryBlaa\\n'
    >>> 
    >>> s = '\\n'.join(s.split('\\n')[:2])
    >>> 
    >>> add_meta_regex(request, u' ööö ää:: blaa', u'blaa', s)
    u'= @PAGE@ =\\n[[TableOfContents]]\\n \\xc3\\xb6\\xc3\\xb6\\xc3\\xb6 \\xc3\\xa4\\xc3\\xa4:: blaa\\n'
    """

    if not newval:
        return oldtext

    # print "Add", repr(newval), repr(oldmeta.get(key, ''))

    # patterns after or before of which the metadata
    # should be included
    pattern = getattr(request.cfg, 'gwiki_meta_after', '')
    repl_str = "\\1\n%s" % (inclusion)
    if not pattern:
        pattern = getattr(request.cfg, 'gwiki_meta_before', '')
        repl_str = "%s\n\\1" % (inclusion)
    if not pattern:
        pattern = default_meta_before

    # if pattern is not found on page, just append meta
    pattern_re = re.compile("(%s)" % (pattern), re.M|re.S)
    newtext, repls = pattern_re.subn(repl_str, oldtext, 1)
    if not repls:
        oldtext = oldtext.strip('\n')
        oldtext += '\n%s\n' % (inclusion)
    else:
        oldtext = newtext

    return oldtext

def replace_metas(request, text, oldmeta, newmeta):
    r"""
    >>> request = _doctest_request()

    Replacing metas:
    >>> replace_metas(request,
    ...               u" test:: 1\n test:: 2",
    ...               dict(test=[u"1"]),
    ...               dict(test=[u"3"]))
    u' test:: 3\n test:: 2\n'
    >>> replace_metas(request,
    ...               u" test:: 1\n test:: 2",
    ...               dict(test=[u"1"]),
    ...               dict(test=[u""]))
    u' test:: 2\n'
    >>> replace_metas(request,
    ...               u" test:: 1\n test:: 2",
    ...               dict(test=[u"2"]),
    ...               dict(test=[u""]))
    u' test:: 1\n'

    Prototypes:
    >>> replace_metas(request,
    ...               u"This is just filler\n test::\nYeah",
    ...               dict(),
    ...               dict(test=[u"1"]))
    u'This is just filler\n test:: 1\nYeah\n'

    Adding metas, clustering when possible:
    >>> replace_metas(request,
    ...               u"This is just filler\nYeah",
    ...               dict(test=[]),
    ...               dict(test=[u"1", u"2"]))
    u'This is just filler\nYeah\n test:: 1\n test:: 2\n'
    >>> replace_metas(request,
    ...               u"This is just filler\n test:: 1\nYeah",
    ...               dict(test=[u"1"]),
    ...               dict(test=[u"1", u"2"]))
    u'This is just filler\n test:: 1\n test:: 2\nYeah\n'

    Handling the magical duality normal categories (CategoryBah) and
    meta style categories. If categories in metas are actually valid
    according to category regexp, retain them as Moin-style
    categories. Otherwise, delete them.

    >>> replace_metas(request,
    ...               u"",
    ...               dict(),
    ...               dict(gwikicategory=[u"test"]))
    u'\n'
    >>> replace_metas(request,
    ...               u"",
    ...               dict(),
    ...               dict(gwikicategory=[u"CategoryTest"]))
    u'----\nCategoryTest\n'
    >>> replace_metas(request,
    ...               u" gwikicategory:: test",
    ...               dict(gwikicategory=[u"test"]),
    ...               dict(gwikicategory=[u"CategoryTest"]))
    u'----\nCategoryTest\n'
    >>> replace_metas(request,
    ...               u"CategoryTest",
    ...               dict(gwikicategory=[u"CategoryTest"]),
    ...               dict(gwikicategory=[u"CategoryTest2"]))
    u'----\nCategoryTest2\n'

    Regression test: The following scenario probably shouldn't produce
    an empty result text.
    
    >>> replace_metas(request,
    ...               u" test:: 1\n test:: 1", 
    ...               dict(test=[u"1", u"1"]),
    ...               dict(test=[u"1", u""]))
    u' test:: 1\n'

    Regression test empty categories should not be saved.

    >>> replace_metas(request,
    ...               u" test:: 1\n----\nCategoryFoo", 
    ...               {u'gwikicategory': [u'CategoryFoo']},
    ...               {u'gwikicategory': [u' ']})
    u' test:: 1\n'

    Regression on a metaformedit bug
    
    >>> replace_metas(request,
    ...               u' aa:: k\n ab:: a\n ab:: a\n----\nCategoryFoo\n',
    ...               {u'aa': [u'k'], u'ab': [u'a', u'a']},
    ...               {u'aa': [u'k'], u'ab': [u'', u'', u' ']})
    u' aa:: k\n----\nCategoryFoo\n'

    Regression test, bug #527: If the meta-to-be-replaced is not
    the first one on the page, it should still be replaced.
    
    >>> replace_metas(request,
    ...               u" bar:: 1\n foo:: 2",
    ...               dict(foo=[u"2"]),
    ...               dict(foo=[u""]))
    u' bar:: 1\n'

    Regression test, bug #594: Metas with preformatted values caused
    corruption.
    
    >>> replace_metas(request,
    ...               u" foo:: {{{a}}}\n",
    ...               dict(foo=[u"{{{a}}}"]),
    ...               dict(foo=[u"b"]))
    u' foo:: b\n'

    Regression test, bug #596: Replacing with empty breaks havoc

    >>> replace_metas(request,
    ...               u" a:: {{{}}}\n b:: {{{Password}}}",
    ...               {'a': [u'{{{}}}']},
    ...               {'a': [u'']})
    u' b:: {{{Password}}}\n'

    Regression test, bug #591 - empties erased

    >>> replace_metas(request,
    ...               u"blaa\n  a:: \n b:: \n c:: \n",
    ...               {u'a': [], u'c': [], u'b': []},
    ...               {u'a': [u'', u' '], u'c': [u'', u' '], u'b': [u'a', u' ']})
    u'blaa\n a:: \n b:: a\n c::\n'

    replace_metas(request, 
    ...           u' status:: open\n agent:: 127.0.0.1-273418929\n heartbeat:: 1229625387.57',
    ...           {'status': [u'open'], 'heartbeat': [u'1229625387.57'], 'agent': [u'127.0.0.1-273418929']},
    ...           {'status': [u'', 'pending'], 'heartbeat': [u'', '1229625590.17'], 'agent': [u'', '127.0.0.1-4124520965']})
    u' status:: pending\n heartbeat:: 1229625590.17\n agent:: 127.0.0.1-4124520965\n'

    Regression test, bug #672
    >>> replace_metas(request,
    ...               u'<<MetaTable(Case672/A, Case672/B, Case672/C)>>\n\n test:: a\n',
    ...               {u'test': [u'a']},
    ...               {u'test': [u'a', u'']})
    u'<<MetaTable(Case672/A, Case672/B, Case672/C)>>\n\n test:: a\n'

    Regression test, bug #739
    >>> replace_metas(request,
    ...               u' a:: k\n{{{\n#!wiki comment\n}}}\n b:: \n',
    ...               {'a': [u'k'], 'gwikicategory': []},
    ...               {'a': [u'', 'b'], 'gwikicategory': []})
    u' a:: b\n{{{\n#!wiki comment\n}}}\n b::\n'

    Metas should not have ':: ' as it could cause problems with dl markup
    >>> replace_metas(request, 
    ...               u' test:: 1\n test:: 2', 
    ...               {}, 
    ...               {u"koo:: ": [u"a"]})
    u' test:: 1\n test:: 2\n koo:: a\n'

    Tests for different kinds of line feeds. Metas should not have \r
    or \n as it would cause problems. This is contrary to general
    MoinMoin logic to minimise user confusion.
    >>> replace_metas(request, 
    ...               u' a:: text\n',
    ...               {u'a': [u'text']},
    ...               {u'a': [u'text\r\n\r\nmore text']})
    u' a:: text  more text\n'

    >>> replace_metas(request, 
    ...               u' a:: text\n',
    ...               {u'a': [u'text']},
    ...               {u'a': [u'text\r\rmore text']})
    u' a:: textmore text\n'

    >>> replace_metas(request, 
    ...               u' a:: text\n',
    ...               {u'a': [u'text']},
    ...               {u'a': [u'text\n\nmore text']})
    u' a:: text  more text\n'

    # Just in case - regression of spaces at the end of metas
    >>> replace_metas(request, 
    ...               u'kk\n a:: Foo \n<<MetaTable>>',
    ...               {u'a': [u'Foo']},
    ...               {u'a': [u'Foo ', u'']})
    u'kk\n a:: Foo\n<<MetaTable>>\n'

    # Case759 regressions

    >>> replace_metas(request, 
    ...               u' key:: {{{ weohweovd\nwevohwevoih}}}\n gwikilabel:: Foo Bar \n',
    ...               {u'gwikilabel': [u'Foo Bar'], u'key': [u'{{{ weohweovd']},
    ...               {u'gwikilabel': [u'Foo Bar', u''], u'key': [u'{{{ weohwe', u'']})
    u' key:: {{{ weohwe\nwevohwevoih}}}\n gwikilabel:: Foo Bar\n'

    >>> replace_metas(request, 
    ...               u' key:: {{{ \nweohweovd\nwevohwevoih}}}\n gwikilabel:: Foo Bar \n',
    ...               {u'gwikilabel': [u'Foo Bar'], u'key': [u'{{{']},
    ...               {u'gwikilabel': [u'Foo Bar', u''], u'key': [u'{{{ weohwe', u'']})
    u' key:: {{{ weohwe\nweohweovd\nwevohwevoih}}}\n gwikilabel:: Foo Bar\n'

    >>> replace_metas(request, 
    ...               u' key:: {{{#!wiki \nweohweovd\nwevohwevoih}}}\n gwikilabel:: Foo Bar \n',
    ...               {u'gwikilabel': [u'Foo Bar'], u'key': [u'{{{#!wiki']},
    ...               {u'gwikilabel': [u'Foo Bar', u''], u'key': [u'{{{#!wiki weohwe', u'']})
    u' key:: {{{#!wiki weohwe\nweohweovd\nwevohwevoih}}}\n gwikilabel:: Foo Bar\n'

    >>> replace_metas(request, 
    ...               u' key:: {{{#!wiki weohweovd\nwevohwevoih}}}\n gwikilabel:: Foo Bar \n',
    ...               {u'gwikilabel': [u'Foo Bar'], u'key': [u'{{{#!wiki weohweovd']},
    ...               {u'gwikilabel': [u'Foo Bar', u''], u'key': [u'{{{#!wiki weohwe', u'']})
    u' key:: {{{#!wiki weohwe\nwevohwevoih}}}\n gwikilabel:: Foo Bar\n'

    # Case 676, new behaviour
    >>> replace_metas(request, 
    ...               u' gwikicategory:: CategoryOne CategoryTwo',
    ...               {u'gwikicategory': [u'CategoryOne', u'CategoryTwo']},
    ...               {u'gwikicategory': [u'CategoryOnes', u'CategoryTwo', u'', u'']})
    u'----\nCategoryOnes CategoryTwo\n'

    """

    text = text.rstrip()
    # Annoying corner case with dl:s
    if text.endswith('::'):
        text = text + " \n"

    # Work around the metas whose values are preformatted fields (of
    # form {{{...}}})
    text, keys_to_markers, markers_to_keys = remove_preformatted(text)

    replaced_metas = dict()
    for key, values in oldmeta.iteritems():
        replaced_values = list()
        for value in values:
            replaced_values.append(keys_to_markers.get(value, value))
        replaced_metas[key] = replaced_values
    oldmeta = replaced_metas

    # Make clustering replaced and added values work
    # Example: Case739, where 
    # oldmeta['a'] = ['k'] and 
    # newmeta['a'] = ['', 'b']
    # need to revert the newmeta so that the value is replaced,
    # instead of first the value k getting removed and then the
    # value b cannot cluster as the key is there no more
    new_metas = dict()
    for key, values in newmeta.iteritems():
        # Keys should not end in ':: ' as this markup is reserved
        key = key.rstrip(':: ').strip()

        if len(newmeta.get(key, [])) > len(oldmeta.get(key, [])):
            if values[0] == '':
                values.reverse()

        newvalues = list()
        for value in values:
            # Convert \r and \n to safe values, 
            # strip leading and trailing spaces
            value = value.replace("\r\n", " ")
            value = value.replace("\n", " ")
            value = value.replace("\r", "").strip()
            newvalues.append(value)

        new_metas[key] = newvalues
    newmeta = new_metas

    # Replace the values we can
    def dl_subfun(mo):
        alltext, key, val = mo.groups()

        key = key.strip()
        val = val.strip()

        # Categories handled separately (see below)
        if key == CATEGORY_KEY:
            return ""

        # Don't touch unmodified keys
        if key not in oldmeta:
            return alltext

        # Don't touch placeholders
        if not val:
            return ""

        # Don't touch unmodified values
        try:
            index = oldmeta[key].index(val)
        except ValueError:
            return alltext
        
        newval = newmeta[key][index]

        del oldmeta[key][index]
        del newmeta[key][index]
        
        if not newval:
            return ""

        retval = " %s:: %s\n" % (key, newval)
        if alltext.startswith('\n'):
            retval = '\n' + retval

        return retval

    text = dl_re.sub(dl_subfun, text)

    # Handle the magic duality between normal categories (CategoryBah)
    # and meta style categories. Categories can be written on pages as
    # gwikicategory:: CategoryBlaa, and this should be supported as
    # long as the category values are valid. Categories should always
    # be written on pages as Moin-style, as a space-separated list on
    # the last line of the page
    oldcategories = oldmeta.get(CATEGORY_KEY, list())
    newcategories = newmeta.get(CATEGORY_KEY, list())

    added = filter_categories(request, newcategories)
    discarded = filter_categories(request, oldcategories)

    for index, value in reversed(list(enumerate(newcategories))):
        # Strip empty categories left by metaedit et al
        if not value.strip():
            del newcategories[index]

        if value not in added:
            continue

        if index < len(oldcategories):
            del oldcategories[index]
        del newcategories[index]

    if discarded:
        text = edit_categories(request, text, "del", discarded)
    if added:
        text = edit_categories(request, text, "add", added)

    # Fill in the prototypes
    def dl_fillfun(mo):
        alltext, key = mo.groups()
        key = key.strip()

        if key not in newmeta or not newmeta[key]:
            return alltext

        newval = newmeta[key].pop(0).replace("\n", " ").strip()

        return " %s:: %s\n" % (key, newval)
    text = dl_proto_re.sub(dl_fillfun, text)

    # Add clustered values
    def dl_clusterfun(mo):
        alltext, key, val = mo.groups()

        key = key.strip()
        if key not in newmeta:
            return alltext

        for value in newmeta[key]:
            value = value.replace("\n", " ").strip()
            if value:
                alltext += " %s:: %s\n" % (key, value)

        newmeta[key] = list()
        return alltext
    text = dl_re.sub(dl_clusterfun, text)

    # Add values we couldn't cluster
    for key, values in newmeta.iteritems():
        # Categories handled separately (see above)
        if key == CATEGORY_KEY:
            continue

        for value in values:
            # Empty values again supplied by metaedit and metaformedit
            if not value.strip():
                continue

            inclusion = " %s:: %s" % (key, value)
            text = add_meta_regex(request, inclusion, value, text)

    # Metas have been set, insert preformatted areas back
    for key in markers_to_keys:
        text = text.replace(key, markers_to_keys[key])

    # Add enter to the end of the line, as it was removed in the
    # beginning of this function, not doing so causes extra edits.
    return text.rstrip() + '\n'

def set_metas(request, cleared, discarded, added):
    pages = set(cleared) | set(discarded) | set(added)

    # Discard empties and junk
    pages = [x.strip() for x in pages if x.strip()]

    msg = list()

    # We don't have to check whether the user is allowed to read
    # the page, as we don't send any info on the pages out. Only
    # check that we can write to the requested pages.
    for page in pages:
        if not request.user.may.write(page):
            message = "You are not allowed to edit page '%s'" % page
            return False, request.getText(message)

    for page in pages:
        pageCleared = cleared.get(page, set())
        pageDiscarded = discarded.get(page, dict())
        pageAdded = added.get(page, dict())
        
        # Template clears might make sense at some point, not implemented
        if TEMPLATE_KEY in pageCleared:
            pageCleared.remove(TEMPLATE_KEY)
        # Template changes might make sense at some point, not implemented
        if TEMPLATE_KEY in pageDiscarded:
            del pageDiscarded[TEMPLATE_KEY]
        # Save templates for empty pages
        if TEMPLATE_KEY in pageAdded:
            save_template(request, page, ''.join(pageAdded[TEMPLATE_KEY]))
            del pageAdded[TEMPLATE_KEY]

        metakeys = set(pageCleared) | set(pageDiscarded) | set(pageAdded)
        # Filter out uneditables, such as inlinks
        metakeys = editable_p(metakeys)

        old = get_metas(request, page, metakeys, 
                        checkAccess=False, includeGenerated=False)

        new = dict()
        for key in old:
            values = old.pop(key)
            old[key] = values
            new[key] = set(values)
        for key in pageCleared:
            new[key] = set()
        for key, values in pageDiscarded.iteritems():
            for v in values:
                new[key].difference_update(values) 

        for key, values in pageAdded.iteritems():
            new[key].update(values)

        for key, values in new.iteritems():
            ordered = copy.copy(old[key])
            
            for index, value in enumerate(ordered):
                if value not in values:
                    ordered[index] = u""

            values.difference_update(ordered)
            ordered.extend(values)
            new[key] = ordered

        msg.append(edit_meta(request, page, old, new))

    return True, msg

def save_template(request, page, template):
    # Get body, or template if body is not available, or ' '
    raw_body = Page(request, page).get_raw_body()
    msg = ''
    if not raw_body:
        # Start writing

        ## TODO: Add data on template to the text of the saved page?

        raw_body = ' '
        p = PageEditor(request, page)
        template_page = wikiutil.unquoteWikiname(template)
        if request.user.may.read(template_page):
            temp_body = Page(request, template_page).get_raw_body()
            if temp_body:
                raw_body = temp_body

        msg = p.saveText(raw_body, 0)

    return msg

def savetext(request, pagename, newtext, **kw):
    """ Savetext - a function to be used by local CLI scripts that
    modify page content directly.

    """

    page = PageEditor(request, pagename)

    try:
        msg = page.saveText(newtext, 0, **kw)
    except page.Unchanged:
        msg = u'Unchanged'

    return msg

def string_aton(value):
    # Regression: without this, '\d+ ' is an IP according to this func
    if not '.' in value:
        raise TypeError

    # Strips links syntax and stuff
    value = value.lstrip('[').rstrip(']')

    # Support for CIDR notation, eg. 10.10.1.0/24
    end = ''
    if '/' in value:
        value, end = value.split('/', 1)
        end = '/' + end

    # 00 is stylistic to avoid this: 
    # >>> sorted(['a', socket.inet_aton('100.2.3.4'), 
    #             socket.inet_aton('1.2.3.4')]) 
    # ['\x01\x02\x03\x04', 'a', 'd\x02\x03\x04'] 
    return u'00' + unicode(socket.inet_aton(value).replace('\\', '\\\\'), 
                           "unicode_escape") + end

ORDER_FUNCS = [
    # (conversion function, ignored exception type(s))
    # integers
    (int, ValueError),
    # floats
    (float, ValueError),
    # ipv4 addresses
    (string_aton, (socket.error, UnicodeEncodeError, TypeError)),
    # strings (unicode or otherwise)
    (lambda x: x.lower(), AttributeError)
    ]

def ordervalue(value):
    for func, ignoredExceptionTypes in ORDER_FUNCS:
        try:
            return func(value)
        except ignoredExceptionTypes:
            pass
    return value

# You can implement different coordinate formats here
COORDINATE_REGEXES = [
    # long, lat -> to itself
    ('(-?\d+\.\d+,-?\d+\.\d+)', lambda x: x.group())
    ]
def verify_coordinates(coords):
    for regex, replacement in COORDINATE_REGEXES:
        if re.match(regex, coords):
            try:
                retval = re.sub(regex, replacement, coords)
                return retval
            except:
                pass

def metatable_parseargs(request, args,
                        get_all_keys=False,
                        get_all_pages=False,
                        checkAccess=True,
                        include_unsaved=False):
    if not args:
        # If called from a macro such as MetaTable,
        # default to getting the current page
        req_page = request.page
        if get_all_pages or req_page is None or req_page.page_name is None:
            args = ""
        else:
            args = req_page.page_name

    # Category, Template matching regexps
    cat_re = category_regex(request)
    temp_re = template_regex(request)

    # Standard Python operators
    operators = {'<': operator.lt, 
                 '<=': operator.le, 
                 '==': operator.eq,
                 '!=': operator.ne, 
                 '>=': operator.ge, 
                 '>': operator.gt}

    # Arg placeholders
    argset = set([])
    keyspec = []
    orderspec = []
    limitregexps = {}
    limitops = {}

    # Capacity for storing indirection keys in metadata comparisons
    # and regexps, eg. k->c=/.+/
    indirection_keys = []

    # list styles
    styles = {}

    # Flag: were there page arguments?
    pageargs = False

    # Regex preprocessing
    for arg in (x.strip() for x in args.split(',') if x.strip()):
        # metadata key spec, move on
        if arg.startswith('||') and arg.endswith('||'):
            # take order, strip empty ones, look at styles
            for key in arg.split('||'):
                if not key:
                    continue
                # Grab styles
                if key.startswith('<') and '>' in key:
                    style = wikiutil.parseAttributes(request,
                                                     key[1:], '>')
                    key = key[key.index('>') + 1:].strip()

                    if style:
                        styles[key] = style[0]

                keyspec.append(key.strip())

            continue

        op_match = False
        # Check for Python operator comparisons
        for op in operators:
            if op in arg:
                data = arg.rsplit(op)
                
                # If this is not a comparison but indirection,
                # continue. Good: k->s>3, bad: k->s=/.+/
                if op == '>' and data[0].endswith('-'):
                    continue

                # Must have real comparison
                if not len(data) == 2:
                    continue

                key, comp = map(string.strip, data)

                # Add indirection key
                if '->' in key:
                    indirection_keys.append(key)

                limitops.setdefault(key, list()).append((comp, op))
                op_match = True

            # One of the operators matched, no need to go forward
            if op_match:
                break

        # One of the operators matched, process next arg
        if op_match:
            continue

        # Metadata regexp, move on
        if '=' in arg:
            data = arg.split("=")
            key = data[0]

            # Add indirection key
            if '->' in key:
                indirection_keys.append(key)

            val = '='.join(data[1:])

            # Assume that value limits are regexps, if
            # not, escape them into exact regexp matches
            if not regexp_re.match(val):
                from MoinMoin.parser.text_moin_wiki import Parser

                # If the value is a page, make it a non-matching
                # regexp so that all link variations will generate a
                # match. An alternative would be to match from links
                # also, but in this case old-style metalinks, which
                # cannot be edited, would appear in metatables, which
                # is not wanted (old-style eg. [[Page| key: Page]])

                # Only allow non-matching regexp for values if they
                # are WikiWords. Eg. 'WikiWord some text' would match
                # 'WikiWord', emulating ye olde matching behaviour,
                # but 'nonwikiword some text' would not match
                # 'nonwikiword'
                if re.match(Parser.word_rule_js, val):
                    re_val = "(%s|" % (re.escape(val)) 
                else:
                    re_val = "(^%s$|" % (re.escape(val)) 
                # or as bracketed link
                re_val += "(?P<sta>\[\[)%s(?(sta)\]\])|" % (re.escape(val)) 

                # or as commented bracketed link
                re_val += "(?P<stb>\[\[)%s(?(stb)\|[^\]]*\]\]))" % \
                    (re.escape(val)) 
                
                limitregexps.setdefault(
                    key, set()).add(re.compile(re_val, re.UNICODE))

            # else strip the //:s
            else:
                if len(val) > 1:
                    val = val[1:-1]

                limitregexps.setdefault(
                    key, set()).add(re.compile(val, 
                                               re.IGNORECASE | re.UNICODE))
            continue

        # order spec
        if arg.startswith('>>') or arg.startswith('<<'):
            # eg. [('<<', 'koo'), ('>>', 'kk')]
            orderspec = re.findall('(?:(<<|>>)([^<>]+))', arg)
            continue

        # Ok, we have a page arg, i.e. a page or page regexp in args
        pageargs = True

        # Normal pages, check perms, encode and move on
        if not regexp_re.match(arg):
            # If it's a subpage link eg. /Koo, we must add parent page
            if arg.startswith('/'):
                arg = request.page.page_name + arg

            argset.add(arg)
            continue

        # Ok, it's a page regexp

        # if there's something wrong with the regexp, ignore it and move on
        try:
            page_re = re.compile("%s" % arg[1:-1])
        except:
            continue

        # Get all pages, check which of them match to the supplied regexp
        for page in request.graphdata:
            if page_re.match(page):
                argset.add(page)

    def is_saved(name):
        if include_unsaved:
            return True
        return request.graphdata.is_saved(name)

    def can_be_read(name):
        return request.user.may.read(name)

    # If there were no page args, default to all pages
    if not pageargs and not argset:
        pages = filter(is_saved, request.graphdata.pagenames())
        if checkAccess:
            # Filter out the pages the user may not read
            pages = filter(can_be_read, pages)
        pages = set(pages)
    # Otherwise check out the wanted pages
    else:
        pages = set()
        categories = set(filter_categories(request, argset))
        other = argset - categories

        for arg in categories:
            newpages = request.graphdata.get_in(arg).get(CATEGORY_KEY, list())

            for newpage in newpages:
                # Check that the page is not a category or template page
                if cat_re.search(newpage) or temp_re.search(newpage):
                    continue
                if not is_saved(newpage):
                    continue
                if checkAccess and not can_be_read(newpage):
                    continue
                pages.add(newpage)

        for name in other:
            if not is_saved(name):
                continue
            if checkAccess and not can_be_read(name):
                continue
            pages.add(name)

    pagelist = set()
    for page in pages:
        clear = True
        # Filter by regexps (if any)
        if limitregexps:
            # We're sure we have access to read the page, don't check again
            metas = get_metas(request, page, limitregexps, checkAccess=False)

            for key, re_limits in limitregexps.iteritems():

                values = metas[key]
                if not values:
                    clear = False
                    break

                for re_limit in re_limits:
                    clear = False

                    # Iterate all the keys for the value for a match
                    for value in values:
                        if re_limit.search(value):

                            clear = True
                            # Single match is enough
                            break

                    # If one of the key's regexps did not match
                    if not clear:
                        break

                # If all of the regexps for a single page did not match
                if not clear:
                    break

        if not clear:
            continue

        if limitops:
            # We're sure we have access to read the page, don't check again
            metas = get_metas(request, page, limitops, checkAccess=False)

            for key, complist in limitops.iteritems():
                values = metas[key]

                for (comp, op) in complist:
                    clear = True

                    # The non-existance of values is good for not
                    # equal, bad for the other comparisons
                    if not values:
                        if op == '!=':
                            continue

                        clear = False

                    # Must match all
                    for value in values:
                        value, comp = ordervalue(value), ordervalue(comp)

                        if not operators[op](value, comp):
                            clear = False
                            break

                    # If one of the comparisons for a single key were not True
                    if not clear:
                        break

                # If all of the comparisons for a single page were not True
                if not clear:
                    break
                            

        # Add page if all the regexps and operators have matched
        if clear:
            pagelist.add(page)

    metakeys = set([])

    if not keyspec:
        for name in pagelist:
            # MetaEdit wants all keys by default
            if get_all_keys:
                for key in request.graphdata.get_metakeys(name):
                    metakeys.add(key)
            else:
                # For MetaTable etc
                for key in (x for x in request.graphdata.get_metakeys(name)
                            if not x in SPECIAL_ATTRS):
                    metakeys.add(key)

        # Add gathered indirection metakeys
        metakeys.update(indirection_keys)

        metakeys = sorted(metakeys, key=ordervalue)
    else:
        metakeys = keyspec

    # sorting pagelist
    if not orderspec:
        pagelist = sorted(pagelist, key=ordervalue)
    else:
        orderkeys = [key for (direction, key) in orderspec]
        orderpages = dict()

        for page in pagelist:
            ordermetas = get_metas(request, page, orderkeys, checkAccess=False)

            for key, values in ordermetas.iteritems():
                values = map(ordervalue, values)
                ordermetas[key] = values
            orderpages[page] = ordermetas

        def comparison(page1, page2):
            for direction, key in orderspec:
                reverse = False
                if direction == ">>":
                    reverse = True

                if key == "gwikipagename":
                    values1 = [page1]
                    values2 = [page2]
                else:
                    values1 = sorted(orderpages[page1][key], reverse=reverse)
                    values2 = sorted(orderpages[page2][key], reverse=reverse)
            
                result = cmp(values1, values2)
                if result == 0:
                    continue
            
                if not values1:
                    return 1
                if not values2:
                    return -1

                if reverse:
                    return -result
                return result
            return cmp(ordervalue(page1), ordervalue(page2))

        pagelist = sorted(pagelist, cmp=comparison)

    return pagelist, metakeys, styles

def check_attachfile(request, pagename, aname):
    # Check that the attach dir exists
    getAttachDir(request, pagename, create=1)
    aname = wikiutil.taintfilename(aname)
    fpath = getFilename(request, pagename, aname)

    # Trying to make sure the target is a regular file
    if os.path.isfile(fpath) and not os.path.islink(fpath):
        return fpath, True

    return fpath, False

def save_attachfile(request, pagename, content, aname, overwrite=False, log=False):
    try:
        fpath, exists = check_attachfile(request, pagename, aname)
        if not overwrite and exists:
            return False

        # Save the data to a file under the desired name
        stream = open(fpath, 'wb')
        stream.write(content)
        stream.close()

        if log:
            _addLogEntry(request, 'ATTNEW', pagename, aname)
    except:
        return False

    return True

def load_attachfile(request, pagename, aname):
    try:
        fpath, exists = check_attachfile(request, pagename, aname)
        if not exists:
            return None

        # Save the data to a file under the desired name
        stream = open(fpath)
        adata = stream.read()
        stream.close()
    except:
        return None

    return adata

def delete_attachfile(request, pagename, aname):
    try:
        fpath, exists = check_attachfile(request, pagename, aname)
        if not exists:
            return False

        os.unlink(fpath)
    except:
        return False

    return True

def list_attachments(request, pagename):
    # Code from MoinMoin/action/AttachFile._get_files
    attach_dir = getAttachDir(request, pagename)
    if os.path.isdir(attach_dir):
        files = map(lambda a: a.decode(config.charset), os.listdir(attach_dir))
        files.sort()
        return files

    return []

def _doctest_request(graphdata=dict(), mayRead=True, mayWrite=True):
    class Request(object):
        pass
    class Config(object):
        pass
    class Object(object):
        pass
    class Cache(object):
        pass
    class GraphData(dict):
        def getpage(self, page):
            return self.get(page, dict())
    
    request = Request()
    request.cfg = Config()
    request.cfg.cache = Cache()
    request.cfg.cache.page_category_regex = category_regex(request)
    request.cfg.cache.page_category_regexact = category_regex(request, act=True)
    request.graphdata = GraphData(graphdata)

    request.user = Object()
    request.user.may = Object()
    request.user.may.read = lambda x: mayRead
    request.user.may.write = lambda x: mayWrite

    return request

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
