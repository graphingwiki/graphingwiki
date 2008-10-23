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

from MoinMoin.parser.wiki import Parser
from MoinMoin.action.AttachFile import getAttachDir, getFilename
from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin import caching
from MoinMoin.wikiutil import importPlugin,  PluginMissingError

from graphingwiki.patterns import nonguaranteeds_p, decode_page, encode_page
from graphingwiki.patterns import absolute_attach_name, filter_categories
from graphingwiki.patterns import NO_TYPE

CATEGORY_KEY = "gwikicategory"
TEMPLATE_KEY = "gwikitemplate"

def macro_re(macroname):
    return re.compile(r'(?<!#)\s*?\[\[(%s)\((.*?)\)\]\]' % macroname)

metadata_re = macro_re("MetaData")

regexp_re = re.compile('^/.+/$')
# Dl_re includes newlines, if available, and will replace them
# in the sub-function
dl_re = re.compile('(\n?^\s+(.+?):: (.+))$', re.M)
# From Parser, slight modification due to multiline usage
dl_proto = "^(\s+?%s::)\s*$"
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
        revlink = '%s?action=recall&rev=%d' % (pagename, rev)

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
                                         dict())[u'#rev'] = [unicode(rev)]
            # Do the cache. 
            request.graphdata.cacheset(revlink, alldata[pagename])

            # Add revision as meta so that it is shown in the table
            revisions[rev] = revlink

    pagelist = [revisions[x] for x in sorted(revisions.keys(), 
                                             key=ordervalue, 
                                             reverse=True)]

    metakeys = set()
    for page in pagelist:
        for key in getkeys(request, page):
            metakeys.add(key)
    metakeys = sorted(metakeys, key=ordervalue)

    return pagelist, metakeys

def underlay_to_pages(req, p):
    underlaydir = req.cfg.data_underlay_dir
    pagedir = os.path.join(req.cfg.data_dir, 'pages')

    pagepath = p.getPagePath()

    # If the page has not been created yet,
    # create its directory and save the stuff there
    if underlaydir in pagepath:
        pagepath = pagepath.replace(underlaydir, pagepath)
        if not os.path.exists(pagepath):
            os.makedirs(pagepath)

    return pagepath

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
            return lines, total_confirmed

        # It was a category line - add the categories
        total_confirmed.extend(confirmed)

        # Remove the category line
        lines.pop()

    return lines, confirmed

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

def getkeys(request, name):
    page = request.graphdata.getpage(name)
    keys = set(page.get('meta', {}).keys())
    # Non-typed links are not included
    keys.update(set(x for x in page.get('out', {}).keys()
                    if x != NO_TYPE))
    keys = {}.fromkeys(keys, '')
    return keys

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

# Deprecated, remains for backwards compability for now
def getmetas(request, name, metakeys, 
             display=True, abs_attach=True, checkAccess=True):
    return get_metas(request, name, metakeys, display, abs_attach, checkAccess)

# Deprecated, remains for backwards compability for now
def getvalues(request, name, key,
              display=True, abs_attach=True, checkAccess=True):
    return getmetas(request, name, [key], display, abs_attach, checkAccess)[key]

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

def edit(pagename, editfun, oldmeta, newmeta, request,
         category_edit='', catlist=[], lock=None):
    p = PageEditor(request, pagename)

    oldtext = p.get_raw_body()

    #request.write(repr(oldtext) + '<br>' + repr(pre_replace))
    #request.write(repr(oldtext % pre_replace) + '<br>')
    #return '', p

    oldtext, pre_replace = remove_preformatted(oldtext)

    newtext = editfun(request, oldtext, oldmeta, newmeta)

    # Metas have been set, insert preformatted areas back
    for key in pre_replace:
        newtext = newtext.replace(key, pre_replace[key])

    # Add categories, if needed
    if category_edit:
        newtext = edit_categories(request, newtext, category_edit, catlist)

    graphsaver = wikiutil.importPlugin(request.cfg, 'action', 'savegraphdata')

    # PageEditor.saveText doesn't allow empty texts
    if not newtext:
        newtext = u" "

    try:
        msg = p.saveText(newtext, 0)
        graphsaver(pagename, request, newtext, p.getPagePath(), p)

        # delete pagelinks
        arena = p
        key = 'pagelinks'
        cache = caching.CacheEntry(request, arena, key)
        cache.remove()

        # forget in-memory page text
        p.set_raw_body(None)

        # clean the in memory acl cache
        p.clean_acl_cache()

        # clean the cache
        for formatter_name in ['text_html']:
            key = formatter_name
            cache = caching.CacheEntry(request, arena, key)
            cache.remove()

    except p.Unchanged:
        msg = u'Unchanged'

    return msg, p

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
    u'= @PAGE@ =\\n[[TableOfContents]]\\n[[LinkedIn]]\\n \xc3\xb6\xc3\xb6\xc3\xb6 \xc3\xa4\xc3\xa4:: blaa\\n----\\nCategoryIdentity\\n##fslsjdfldfj\\nCategoryBlaa\\n'
    >>> 
    >>> request.cfg.gwiki_meta_after = '^----'
    >>> 
    >>> add_meta_regex(request, u' ööö ää:: blaa', u'blaa', s)
    u'= @PAGE@ =\\n[[TableOfContents]]\\n[[LinkedIn]]\\n----\\n \xc3\xb6\xc3\xb6\xc3\xb6 \xc3\xa4\xc3\xa4:: blaa\\nCategoryIdentity\\n##fslsjdfldfj\\nCategoryBlaa\\n'
    >>> 
    >>> s = '\\n'.join(s.split('\\n')[:2])
    >>> 
    >>> add_meta_regex(request, u' ööö ää:: blaa', u'blaa', s)
    u'= @PAGE@ =\\n[[TableOfContents]]\\n \xc3\xb6\xc3\xb6\xc3\xb6 \xc3\xa4\xc3\xa4:: blaa\\n'
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
        oldtext = oldtext.rstrip('\n')
        oldtext += '\n%s\n' % (inclusion)
    else:
        oldtext = newtext

    return oldtext

def replace_metas(request, oldtext, oldmeta, newmeta):
    r"""
    Regression test: The following scenario probably shouldn't produce
    an empty result text.
    
    >>> replace_metas(object(), 
    ...               u" test:: 1\n test:: 1", 
    ...               dict(test=[u"1", u"1"]),
    ...               dict(test=[u"1", u""]))
    u' test:: 1\n'
    """

    oldtext = oldtext.rstrip()
    # Annoying corner case with dl:s
    if oldtext.endswith('::'):
        oldtext = oldtext + ' '

    #a = file('/tmp/log', 'a')
    #a.write(repr(oldtext) + '\n')
    #a.write(repr(oldmeta) + '\n')
    #a.write(repr(newmeta) + '\n')
    #a.flush()
    #a.close()

    # Keeps track on the keys added during this edit
    added_keys = set()

    def macro_subfun(mo):
        old_keyval_pair = mo.group(2).split(',')

        # Strip away empty metadatas [[MetaData()]]
        # and placeholders [[MetaData(%s,)]]
        # (Placeholders should become obsolete with MetaEdit)
        if len(old_keyval_pair) < 2:
            return ''

        # Check if the value has changed
        key = old_keyval_pair[0]
        key = key.strip()
        val = ','.join(old_keyval_pair[1:])

        if key.strip() == oldkey.strip() and val.strip() == oldval.strip():
            val = newval

        # Return dict variable
        return '\n %s:: %s' % (key, val)

    def dl_subfun(mo):
        all, key, val = mo.groups()

        # print repr(all), repr(key), repr(val)

        # Don't even start working on it if the key does not match
        if key.strip() != oldkey.strip():
            return all

        # print "Trying", repr(oldkey), repr(key), repr(oldval), repr(newval)

        # Check if the value has changed
        key = key.strip()
        # print repr(oldval), repr(val), repr(newval)
        # print repr(oldkey), repr(key)
        if key == oldkey.strip() and val.strip() == oldval.strip():
            val = newval

        # Do not return placeholders
        if not val.strip():
            return ''

        out = ' %s:: %s' % (key, val)

        if all.startswith('\n'):
            out = '\n' + out

        return out

    for key in newmeta:
        # print repr(key)
        oldkey = key
        dl_proto_re = re.compile(dl_proto % (oldkey), re.M)
        dl_add_re = re.compile(dl_add % (oldkey), re.M)

        for i, newval in enumerate(newmeta[key]):
            # print repr(newval)
            # Remove newlines from input, as they could really wreck havoc.
            newval = newval.replace('\n', ' ')
            inclusion = ' %s:: %s' % (oldkey, newval)

            #print repr(inclusion)

            #print "Meta change", repr(key), repr(newval)

            #print key, repr(oldmeta.has_key(key)), repr(oldmeta.get(key, '')), len(oldmeta.get(key, '')), repr(newval.strip())

            # If nothing to do, do nothing
            if (not oldmeta.has_key(key)
                and not newval.strip()):

                #print "Nothing to do\n"

                continue

            # If old meta has the key with i valus of it, 
            # replace its i:th value with the new key. Preserves order.
            elif (oldmeta.has_key(key) and len(oldmeta[key]) - 1 >= i):
                oldval = oldmeta[key][i]
                #print "Replace", repr(oldval), repr(newval)
                #print "# ", repr(oldval)
                oldkey = key
                # First try to replace the dict variable
                oldtext = dl_re.sub(dl_subfun, oldtext)
                # Then try to replace the MetaData macro on page
                oldtext = metadata_re.sub(macro_subfun, oldtext)

            # If prototypes ( key:: ) are present, replace them
            elif (dl_proto_re.search(oldtext + '\n')):

                # Do not replace with empties, i.e. status quo
                if not newval.strip():
                    continue

                oldkey = key

                oldtext = dl_proto_re.sub('\\1 %s' % (newval),
                                          oldtext + '\n', 1)

                added_keys.add(key)

                #print "Proto", repr(newval), '\n'

                continue

            # If the old text has this key (either before this edit
            # or added by this edit), add them (as dl).
            # Cluster values of same keys near
            elif (key in added_keys or
                  (oldmeta.has_key(key) and 
                   len(oldmeta[key]) - 1 < i)):

                #print "Cluster", repr(newval), repr(oldmeta.get(key, '')), '\n'

                # Easiest to strip excess line breaks in a function
                def cluster_metas(mo):
                    all = mo.group(0)
                    all = all.lstrip('\n')
                    return '%s\n%s' % (inclusion, all)

                # DL meta supported only, otherwise
                # fall back to just adding
                text, count = dl_add_re.subn(cluster_metas,
                                             oldtext, 1)

                if count:
                    oldtext = text
                    continue

                oldtext = add_meta_regex(request, inclusion, newval, oldtext)

            # If the old text does not have this key, add it (as dl)
            else:
                #print "Newval"
                oldtext = add_meta_regex(request, inclusion, newval, oldtext)
                added_keys.add(key)

            # print

    return oldtext

def edit_meta(request, pagename, oldmeta, newmeta,
              category_edit='', catlist=[]):

    msg, p = edit(pagename, replace_metas, oldmeta, newmeta, request, 
                  category_edit, catlist)

    return msg

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
            return xmlrpclib.Fault(2, request.getText(message))

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
        
        # Handle the magic duality between normal categories (CategoryBah)
        # and meta style categories
        if CATEGORY_KEY in pageCleared:
            edit_meta(request, page, dict(), dict(), "set", list())
        if CATEGORY_KEY in pageDiscarded:
            categories = pageDiscarded[CATEGORY_KEY]
            edit_meta(request, page, dict(), dict(), "del", categories)
        if CATEGORY_KEY in pageAdded:
            categories = set(pageAdded[CATEGORY_KEY])
            filtered = set(filter_categories(request, categories))
            edit_meta(request, page, dict(), dict(), "add", list(filtered))
            pageAdded[CATEGORY_KEY] = list(categories - filtered)

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

def process_meta_changes(request, input):
    changes = dict()
    keychanges = dict()
    keypage = ''

    # Key changes
    for key in input:
        if not key.startswith(':: '):
            continue

        newkey = input[key][0]
        key = key[3:]
        if key == newkey:
            continue

        # Form presents you with ' ' if the key box is empty
        if not newkey.strip():
            newkey = ''

        # Form keys not autodecoded from utf-8
        keychanges[key] = newkey
        # print repr(keychanges)

    for val in input:
        # At least the key 'save' may be there and should be ignored
        if not '?' in val:
            continue

        newvals = input[val]

        # Form keys not autodecoded from utf-8
        keypage, key = map(decode_page, val.split('?'))

        if not request.user.may.write(keypage):
            continue

        keymetas = get_metas(request, keypage, [key], abs_attach=False)
        oldvals = keymetas[key]

        if oldvals != newvals or keychanges:
            changes.setdefault(keypage, dict())
            if key in keychanges:

                # In case of new keys there is no old one
                if key.strip():
                    # print 'deleting key', repr(key)
                    # Otherwise, delete contents of old key
                    changes[keypage].setdefault('old', dict())[key] = oldvals
                    changes[keypage].setdefault('new', dict())[key] = \
                        [''] * len(oldvals)

                # If new key is empty, don't add anything
                if keychanges[key].strip():
                    # print 'adding key', repr(keychanges[key])
                    if not newvals:
                        newvals = ['']
                    # Otherwise, add old values under new key
                    changes[keypage].setdefault('new', dict())[keychanges[key]]\
                        = newvals
                                                
            else:
                if oldvals:
                    changes[keypage].setdefault('old', dict())[key] = oldvals
                changes[keypage].setdefault('new', dict())[key] = newvals

    return changes

# Handle input from a MetaEdit-form
def process_edit(request, input,
                 category_edit='', categories={}):
    _ = request.getText
    # request.write(repr(request.form) + '<br>')
    # print repr(input) + '<br>'

    changes = process_meta_changes(request, input)

    msg = list()

    # For category-only changes
    if not changes and category_edit:
        for keypage in categories:
            msg.append('%s: ' % keypage + \
                       edit_meta(request, keypage,
                                 dict(), dict(),
                                 category_edit, categories[keypage]))
                                 
    elif changes:
        for keypage in changes:
            catlist = categories.get(keypage, list())
            msg.append('%s: ' % keypage + \
                       edit_meta(request, keypage,
                                 changes[keypage].get('old', dict()),
                                 changes[keypage]['new'],
                                 category_edit, catlist))
    else:
        msg.append(_('No pages changed'))

    return msg

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

def savetext(pagename, newtext):
    """ Savetext - a function to be used by local CLI scripts that
    modify page content directly.

    """
    def replace_metas(pagename, oldtext):
        return newtext

    # For some reason when saving a page with RequestCLI,
    # the pagelinks will present problems with patterns
    # unless explicitly cached
    msg, p = edit(pagename, replace_metas, {}, {}, request)
    if msg != u'Unchanged':
        req = p.request
        req.page = p
        p.getPageLinks(req)

    return msg

def string_aton(value):
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
                        checkAccess = True):
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
            limitregexps.setdefault(key, set()).add(re.compile(val))
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
            # Filter nonexisting pages and the pages the user may not read
            pages = filter(can_be_read, pages)

        pages = set(pages)

    # Otherwise check out the wanted pages
    else:
        if checkAccess:
            # Filter pages the user may not read
            argset = set(filter(request.user.may.read, argset))

        pages = set()

        categories = set(filter_categories(request, argset))
        other = argset - categories

        for arg in categories:
            # Nonexisting categories
            try:
                page = request.graphdata.getpage(arg)
            except KeyError:
                continue
            
            newpages = page.get("in", dict()).get(CATEGORY_KEY, list())
            for newpage in newpages:
                # Check that the page is not a category or template page
                if cat_re.match(newpage) or temp_re.search(newpage):
                    continue
                if checkAccess and request.user.may.read(newpage):
                    # Check that user may view any the page
                    pages.add(newpage)
                else:
                    pages.add(newpage)

        for name in other:
            # Filter out nonexisting pages
            try:
                page = request.graphdata.getpage(name)
            except KeyError:
                continue

            # Added filtering of nonexisting and non-local pages
            if not page.has_key('saved'):
                continue
                
            pages.add(name)

    pagelist = set([])

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
                for key in getkeys(request, name):
                    metakeys.add(key)
            else:
                # For MetaTable etc
                for key in nonguaranteeds_p(getkeys(request, name)):
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

def save_attachfile(request, pagename, srcname, aname, overwrite=False):
    try:
        fpath, exists = check_attachfile(request, pagename, aname)
        if not overwrite and exists:
            return False

        # Read the contents of the file
        filecontent = file(srcname).read()

        # Save the data to a file under the desired name
        stream = open(fpath, 'wb')
        stream.write(filecontent)
        stream.close()
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

def _doctest_request():
    class Request(object):
        pass
    class Config(object):
        pass
    
    request = Request()
    request.cfg = Config()
    request.cfg.page_category_regex = u'^Category[A-Z]'

    return request

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()