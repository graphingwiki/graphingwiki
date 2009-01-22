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
import xmlrpclib
import urlparse
import socket
import urllib
import getpass
import copy
import md5

from MoinMoin.action.AttachFile import getAttachDir, getFilename, _addLogEntry
from MoinMoin.PageEditor import PageEditor
from MoinMoin.request.request_cli import Request as RequestCLI
from MoinMoin.Page import Page
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin.wikiutil import importPlugin,  PluginMissingError

from graphingwiki.patterns import nonguaranteeds_p, decode_page, encode_page
from graphingwiki.patterns import absolute_attach_name, filter_categories
from graphingwiki.patterns import NO_TYPE, SPECIAL_ATTRS

CATEGORY_KEY = "gwikicategory"
TEMPLATE_KEY = "gwikitemplate"

def underlay_to_pages(req, p):
    underlaydir = req.cfg.data_underlay_dir
    pagedir = os.path.join(req.cfg.data_dir, 'pages')

    pagepath = p.getPagePath()

    # If the page has not been created yet, create its directory and
    # save the stuff there
    if underlaydir in pagepath:
        pagepath = pagepath.replace(underlaydir, pagepath)
        if not os.path.exists(pagepath):
            os.makedirs(pagepath)

    return pagepath

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
        for key in get_keys(request, page):
            metakeys.add(key)
    metakeys = sorted(metakeys, key=ordervalue)

    return pagelist, metakeys

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
    Parse category names from the page. Return a list of the preceding
    text lines and a list of parsed categories.

    >>> request = _doctest_request()
    >>> parse_categories(request, "CategoryTest")
    ([], ['CategoryTest'])

    Take into account only the categories that come after all other text
    (excluding whitespaces):

    >>> parse_categories(request, "Blah\nCategoryNot blah\nCategoryTest\n")
    (['Blah', 'CategoryNot blah'], ['CategoryTest'])

    Regression test, bug #540: Pages with only categories (or whitespaces) 
    on several lines don't get parsed correctly:

    >>> parse_categories(request, "\nCategoryTest")
    ([], ['CategoryTest'])
    """

    # We want to parse only the last non-empty line of the text
    lines = text.rstrip().splitlines()
    if not lines:
        return lines, list()

    # All the categories on the multiple ending lines of 
    total_confirmed = list()
    # Start looking at lines from the end to the beginning
    while lines:
        confirmed = list()
        # Skip empty lines, comments
        if not lines[-1].strip() or lines[-1].startswith('##'):
            lines.pop()
            continue

        # TODO: this code is broken, will not work for extended links
        # categories, e.g ["category hebrew"]
        candidates = lines[-1].split()
        confirmed.extend(filter_categories(request, candidates))

        # A category line is defined as a line that contains only categories
        if len(confirmed) < len(candidates):
            # The line was not a category line
            break

        # It was a category line - add the categories
        total_confirmed.extend(confirmed)

        # Remove the category line
        lines.pop()

    return lines, total_confirmed

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
    lines, confirmed = parse_categories(request, savetext)

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

    # Check whether the last line is a separator; add and remove it if needed
    if not lines:
        if categories:
            lines.append(u"----")
    elif not (len(lines[-1]) >= 4 and set(lines[-1].strip()) == set("-")):
        if categories:
            lines.append(u"----")
    else:
        if not categories:
            lines.pop()
        
    if categories:
        lines.append(" ".join(categories))

    return u"\n".join(lines) + u"\n"

def formatting_rules(request, parser):
    from MoinMoin.parser.text_moin_wiki import Parser

    rules = parser.formatting_rules.replace('\n', '|')

    if request.cfg.bang_meta:
        rules = ur'(?P<notword>!%(word_rule)s)|%(rules)s' % {
            'word_rule': Parser.word_rule,
            'rules': rules,
            }

    # For versions with the deprecated config variable allow_extended_names
    if not '?P<wikiname_bracket>' in rules:
        rules = rules + ur'|(?P<wikiname_bracket>\[".*?"\])'

    return re.compile(rules, re.UNICODE)


def link_to_attachment(globaldata, target):
    if isinstance(target, unicode):
        target = url_quote(encode(target))
    
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
        target = unicode(url_unquote(target), config.charset)
    else:
        target = unicode(target, config.charset)
    target = target.replace('\\"', '"')

    return target

def absolute_attach_name(quoted, target):
    from MoinMoin.parser.text_moin_wiki import Parser

    abs_method = target.split(':')[0]

    # Pages from MetaRevisions may have ?action=recall, breaking attach links
    if '?' in quoted:
        quoted = quoted.split('?', 1)[0]

    if abs_method in ["attachment", "drawing"] and not '/' in target:
        target = target.replace(':', ':%s/' % (quoted.replace(' ', '_')), 1)

    return target

# Fetch requested metakey value for the given page.
def get_metas(request, name, metakeys, 
             display=False, abs_attach=True, checkAccess=True):
    metakeys = set(metakeys)
    pageMeta = dict([(key, list()) for key in metakeys])

    if checkAccess:
        if not request.user.may.read(name):
            return pageMeta

    loadedPage = request.graphdata.getpage(name)
    loadedMeta = loadedPage.get("meta", dict())

    # Add values and their sources
    for key in metakeys & set(loadedMeta):
        for value in loadedMeta[key]:
            pageMeta[key].append(value)

    # Link values are in a list as there can be more than one edge
    # between two pages.
    if display:
        # Making things nice to look at.
        loadedOuts = loadedPage.get("out", dict())
        for key in metakeys & set(loadedOuts):
            for target in loadedOuts[key]:

                pageMeta[key].append(target)
    else:
        # Showing things as they are
        loadedLits = loadedPage.get("lit", dict())

        for key in metakeys & set(loadedLits):
            for target in loadedLits[key]:
                if abs_attach:
                    target = absolute_attach_name(name, target)

                pageMeta[key].append(target)
            
    return pageMeta

def get_keys(request, name):
    """
    Return the complete set of page's meta keys.
    """

    page = request.graphdata.getpage(name)
    keys = set(page.get('meta', dict()))

    # Non-typed links are not included
    keys.update([x for x in page.get('out', dict()) if x != NO_TYPE])
    return keys

def get_pages(request):
    def filter(name):
        # aw crap, SystemPagesGroup is not a system page
        if name == 'SystemPagesGroup':
            return False
        if wikiutil.isSystemPage(request, name):
            return False
        return request.user.may.read(name)

    return request.rootpage.getPageList(filter=filter)

def remove_preformatted(text):
    # Before setting metas, remove preformatted areas
    preformatted_re = re.compile('({{{.+?}}})', re.M|re.S)
    pre_replace = dict()
    def get_hashkey(val):
        return md5.new(repr(val)).hexdigest()

    # Enumerate preformatted areas
    for val in preformatted_re.findall(text):
        key = get_hashkey(val)
        pre_replace[key] = val

    # Replace with unique format strings per preformatted area
    def replace_preformatted(mo):
        val = mo.group(0)
        key = get_hashkey(val)
        return '%s' % (key)

    text = preformatted_re.sub(replace_preformatted, text)

    return text, pre_replace

def edit_meta(request, pagename, oldmeta, newmeta):
    page = PageEditor(request, pagename)

    text = page.get_raw_body()
    text, pre_replace = remove_preformatted(text)

    text = replace_metas(request, text, oldmeta, newmeta)

    # Metas have been set, insert preformatted areas back
    for key in pre_replace:
        text = text.replace(key, pre_replace[key])

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

def replace_metas(request, oldtext, oldmeta, newmeta):
    r"""
    >>> request = _doctest_request()

    Replacing metas:
    >>> replace_metas(request,
    ...               u" test:: 1\n test:: 2",
    ...               dict(test=[u"1"]),
    ...               dict(test=[u"3"]))
    u' test:: 3\n test:: 2'
    >>> replace_metas(request,
    ...               u" test:: 1\n test:: 2",
    ...               dict(test=[u"1"]),
    ...               dict(test=[u""]))
    u' test:: 2'
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
    u'This is just filler\n test:: 1\nYeah'

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
    u'This is just filler\n test:: 1\n test:: 2\nYeah'

    Handling the magical duality normal categories (CategoryBah)
    and meta style categories:
    >>> replace_metas(request,
    ...               u"",
    ...               dict(),
    ...               dict(gwikicategory=[u"test"]))
    u'\n gwikicategory:: test\n'
    >>> replace_metas(request,
    ...               u"",
    ...               dict(),
    ...               dict(gwikicategory=[u"CategoryTest"]))
    u'----\nCategoryTest\n'
    >>> replace_metas(request,
    ...               u" gwikicategory:: test",
    ...               dict(gwikicategory=[u"test"]),
    ...               dict(gwikicategory=[u"CategoryTest"]))
    u' gwikicategory:: CategoryTest\n'
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
    u' aa:: k\n----\nCategoryFoo'

    Regression test, bug #527: If the meta-to-be-replaced is not
    the first one on the page, it should still be replaced.
    
    >>> replace_metas(request,
    ...               u" bar:: 1\n foo:: 2",
    ...               dict(foo=[u"2"]),
    ...               dict(foo=[u""]))
    u' bar:: 1\n'

    replace_metas(request, 
    ...           u' status:: open\n agent:: 127.0.0.1-273418929\n heartbeat:: 1229625387.57',
    ...           {'status': [u'open'], 'heartbeat': [u'1229625387.57'], 'agent': [u'127.0.0.1-273418929']},
    ...           {'status': [u'', 'pending'], 'heartbeat': [u'', '1229625590.17'], 'agent': [u'', '127.0.0.1-4124520965']})
    u' status:: pending\n heartbeat:: 1229625590.17\n agent:: 127.0.0.1-4124520965\n'
    """

    oldtext = oldtext.rstrip()
    # Annoying corner case with dl:s
    if oldtext.endswith('::'):
        oldtext = oldtext + " \n"

    # Replace the values we can
    def dl_subfun(mo):
        all, key, val = mo.groups()

        key = key.strip()
        val = val.strip()

        # Don't touch unmodified keys
        if key not in oldmeta:
            return all

        # Don't touch placeholders
        if not val:
            return ""

        # Don't touch unmodified values
        try:
            index = oldmeta[key].index(val)
        except ValueError:
            return all
        
        newval = newmeta[key][index].replace("\n", " ").strip()
        del oldmeta[key][index]
        del newmeta[key][index]

        if not newval:
            return ""

        return " %s:: %s\n" % (key, newval)
    oldtext = dl_re.sub(dl_subfun, oldtext)

    # Handle the magic duality between normal categories (CategoryBah)
    # and meta style categories
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
        oldtext = edit_categories(request, oldtext, "del", discarded)
    if added:
        oldtext = edit_categories(request, oldtext, "add", added)

    # Fill in the prototypes
    def dl_fillfun(mo):
        all, key = mo.groups()
        key = key.strip()

        if key not in newmeta or not newmeta[key]:
            return ""

        newval = newmeta[key].pop(0).replace("\n", " ").strip()
        if not newval:
            return ""

        return " %s:: %s\n" % (key, newval)
    oldtext = dl_proto_re.sub(dl_fillfun, oldtext)

    # Add clustered values
    def dl_clusterfun(mo):
        all, key, val = mo.groups()

        key = key.strip()
        if key not in newmeta:
            return all

        for value in newmeta[key]:
            value = value.replace("\n", " ").strip()
            all += " %s:: %s\n" % (key, value)

        newmeta[key] = list()
        return all
    oldtext = dl_re.sub(dl_clusterfun, oldtext)

    # Add values we couldn't cluster
    for key, values in newmeta.iteritems():
        for value in values:
            # Empty values again supplied by metaedit and metaformedit
            if not value.strip():
                continue

            inclusion = " %s:: %s" % (key, value)
            oldtext = add_meta_regex(request, inclusion, value, oldtext)

    return oldtext

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
            del pageCleared[TEMPLATE_KEY]
        # Template changes might make sense at some point, not implemented
        if TEMPLATE_KEY in pageDiscarded:
            del pageDiscarded[TEMPLATE_KEY]
        # Save templates for empty pages
        if TEMPLATE_KEY in pageAdded:
            save_template(request, page, ''.join(pageAdded[TEMPLATE_KEY]))
            del pageAdded[TEMPLATE_KEY]

        metakeys = set(pageCleared) | set(pageDiscarded) | set(pageAdded)
        old = get_metas(request, page, metakeys, checkAccess=False)

        new = dict()
        for key in old:
            values = old.pop(key)
            key = key
            old[key] = values
            new[key] = set(values)
        for key in pageCleared:
            new[key] = set()
        for key, values in pageDiscarded.iteritems():
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
        request.graphdata.writelock()

        raw_body = ' '
        p = PageEditor(request, page)
        template_page = wikiutil.unquoteWikiname(template)
        if request.user.may.read(template_page):
            temp_body = Page(request, template_page).get_raw_body()
            if temp_body:
                raw_body = temp_body

        msg = p.saveText(raw_body, 0)

        # Stop writing
        request.graphdata.readlock()

    return msg

def savetext(request, pagename, newtext):
    """ Savetext - a function to be used by local CLI scripts that
    modify page content directly.

    """

    page = PageEditor(request, pagename)

    try:
        msg = page.saveText(newtext, 0)
    except page.Unchanged:
        msg = u'Unchanged'

    return msg

def string_aton(value):
    # Regression: without this, '\d+ ' is an IP according to this func
    if not '.' in value:
        raise TypeError

    value = value.lstrip('[').rstrip(']').strip('"')

    # 00 is stylistic to avoid this: 
    # >>> sorted(['a', socket.inet_aton('100.2.3.4'), 
    #             socket.inet_aton('1.2.3.4')]) 
    # ['\x01\x02\x03\x04', 'a', 'd\x02\x03\x04'] 
    return u'00' + unicode(socket.inet_aton(value).replace('\\', '\\\\'), 
                           "unicode_escape")

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

def metatable_parseargs(request, args,
                        get_all_keys=False,
                        get_all_pages=False,
                        checkAccess=True):
    if not args:
        # If called from a macro such as MetaTable,
        # default to getting the current page
        req_page = request.page
        if get_all_pages or req_page is None or req_page.page_name is None:
            args = ""
        else:
            args = req_page.page_name

    # Category, Template matching regexps
    cat_re = re.compile(request.cfg.page_category_regex)
    temp_re = re.compile(request.cfg.page_template_regex)

    # Arg placeholders
    argset = set([])
    keyspec = []
    orderspec = []
    limitregexps = {}

    # list styles
    styles = {}

    # Flag: were there page arguments?
    pageargs = False

    # Regex preprocessing
    for arg in (x.strip() for x in args.split(',') if x.strip()):
        # metadata key spec, move on
        if arg.startswith('||') and arg.endswith('||'):
            # take order, strip empty ones, look at styles
            #keyspec = [url_quote(encode(x)) for x in arg.split('||') if x]
            keyspec = []
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

        # Metadata regexp, move on
        if '=' in arg:
            data = arg.split("=")
            key = data[0]
            val = '='.join(data[1:])

            # Assume that value limits are regexps, if
            # not, escape them into exact regexp matches
            if not regexp_re.match(val):
                val = "^%s$" % (re.escape(val))
            # else strip the //:s
            elif len(val) > 1:
                val = val[1:-1]
            limitregexps.setdefault(key, set()).add(re.compile(val, re.I))
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
        return request.graphdata.getpage(name).has_key('saved')

    def can_be_read(name):
        return request.user.may.read(name)

    # If there were no page args, default to all pages
    if not pageargs and not argset:
        pages = filter(is_saved, request.graphdata)
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
            page = request.graphdata.getpage(arg)
            newpages = page.get("in", dict()).get(CATEGORY_KEY, list())

            for newpage in newpages:
                # Check that the page is not a category or template page
                if cat_re.match(newpage) or temp_re.search(newpage):
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
            metas = get_metas(request, page, limitregexps, 
                              display=True, checkAccess=False)
                             
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

        # Add page if all the regexps have matched
        if clear:
            pagelist.add(page)

    metakeys = set([])

    if not keyspec:
        for name in pagelist:
            # MetaEdit wants all keys by default
            if get_all_keys:
                for key in get_keys(request, name):
                    metakeys.add(key)
            else:
                # For MetaTable etc
                for key in (x for x in get_keys(request, name)
                            if not x in SPECIAL_ATTRS):
                    metakeys.add(key)

        metakeys = sorted(metakeys, key=ordervalue)
    else:
        metakeys = keyspec

    # sorting pagelist
    if not orderspec:
        pagelist = sorted(pagelist, key=ordervalue)
    else:
        orderkeys = [key for (dir, key) in orderspec]
        orderpages = dict()

        for page in pagelist:
            ordermetas = get_metas(request, page, orderkeys, 
                                   display=True, checkAccess=False)
            for key, values in ordermetas.iteritems():
                values = map(ordervalue, values)
                ordermetas[key] = values
            orderpages[page] = ordermetas

        def comparison(page1, page2):
            for dir, key in orderspec:
                values1 = orderpages[page1][key]
                values2 = orderpages[page2][key]
            
                result = cmp(values1, values2)
                if result == 0:
                    continue
            
                if not values1:
                    return 1
                if not values2:
                    return -1

                if dir == ">>":
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

def xmlrpc_conninit(wiki, username, password):
    # Action-unrelated connection code
    scheme, netloc, path, _, _, _ = urlparse.urlparse(wiki)

    netloc = "%s:%s@%s" % (username, password, netloc)

    action = "action=xmlrpc2"
    url = urlparse.urlunparse((scheme, netloc, path, "", action, ""))
    srcWiki = xmlrpclib.ServerProxy(url)

    return srcWiki, url

def xmlrpc_connect(func, wiki, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except xmlrpclib.ProtocolError, e:
        return {'faultCode': 4,
                'faultString': 'Cannot connect to server at %s (%d %s)' %
                (wiki, e.errcode, e.errmsg)}
    except socket.error, e:
        # Socket.error does not return two values consistently
        # it might return also ('timed out',), so I'm preparing
        # for the flying elephants here
        args = getattr(e, 'args', [])
        if len(args) != 2:
            return {'faultCode': '666',
                    'faultString': ''.join(args)}
        else:
            return {'faultCode': args[0],
                    'faultString': args[1]}
    except socket.gaierror, e:
        args = getattr(e, 'args', [])
        if len(args) != 2:
            return {'faultCode': '666',
                    'faultString': ''.join(args)}
        else:
            return {'faultCode': args[0],
                    'faultString': args[1]}

def xmlrpc_attach(wiki, page, fname, username, password, method,
                  content='', overwrite=False):
    srcWiki, _ = xmlrpc_conninit(wiki, username, password)
    if content:
        content = xmlrpclib.Binary(content)

    return xmlrpc_connect(srcWiki.AttachFile, wiki, page, fname,
                          method, content, overwrite)

def xmlrpc_error(error):
    return error['faultCode'], error['faultString']

def getuserpass(username=''):
    # Redirecting stdout to stderr for these queries
    old_stdout = sys.stdout
    sys.stdout = sys.stderr

    if not username:
        username = raw_input("Username:")
    password = getpass.getpass("Password:")

    sys.stdout = old_stdout
    return username, password

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
    request.cfg.page_category_regex = u'^Category[A-Z]'
    request.cfg.cache.page_category_regex = re.compile(u'^Category[A-Z]', re.UNICODE)
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
