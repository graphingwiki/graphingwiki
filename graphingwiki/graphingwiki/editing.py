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

from urllib import quote as url_quote
from urllib import unquote as url_unquote

from MoinMoin.parser.wiki import Parser
from MoinMoin.action.AttachFile import getAttachDir, getFilename
from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page
from MoinMoin.request import RequestCLI
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin import caching
from MoinMoin.util.lock import ReadLock

from graphingwiki.patterns import encode, nonguaranteeds_p, getgraphdata

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
        table_keys.extend([url_unquote(encode(key))] * keyoccur[key])

    table = [table_keys]

    for vals in input[1:]:
        row = [url_unquote(encode(vals[0]))]
        for i, val in enumerate(vals[1:]):
            val = [encode(x) for x in val]
            val.extend([''] * (keyoccur[keys[i]] - len(val)))
            row.extend(val)
        table.append(row)

    return table    

def ordervalue(value):
    # IP addresses and numeric values get special treatment
    try:
        value = int(value.strip('"'))
    except ValueError:
        try:
            value = float(value.strip('"'))
        except ValueError:
            tmpval = value.lstrip('[').rstrip(']').strip('"')
            if value.replace('.', '').isdigit():
                try:
                    # 00 is stylistic to avoid this:
                    # >>> sorted(['a', socket.inet_aton('100.2.3.4'),
                    #     socket.inet_aton('1.2.3.4')])
                    # ['\x01\x02\x03\x04', 'a', 'd\x02\x03\x04']
                    value = '00' + socket.inet_aton(value.strip('"'))
                except socket.error:
                    pass
            pass
    except AttributeError:
        # If given an int to start with
        pass

    return value

def edit_categories(request, savetext, category_edit, catlist):
    # Original code copied from PageEditor

    # Filter out anything that is not a category
    newcategories = wikiutil.filterCategoryPages(request, catlist)
    # If no categories to set or add, bail out now
    if not newcategories and not category_edit == 'del':
        return savetext
        
    # strip trailing whitespace
    savetext = savetext.rstrip()

    confirmed = []

    # Add category separator if last non-empty line contains
    # non-categories.
    lines = filter(None, savetext.splitlines())
    if lines:
        #TODO: this code is broken, will not work for extended links
        #categories, e.g ["category hebrew"]
        categories = lines[-1].split()

        if categories:
            confirmed = wikiutil.filterCategoryPages(request, categories)

        if len(confirmed) < len(categories):
            # This was not a categories line, if deleting, our job is done
            if category_edit == 'del':
                return savetext + u'\n'
            
            # otherwise add separator
            savetext += u'\n----\n'
        elif category_edit == 'set':
            # Delete existing when setting categories
            savetext = '\n'.join(savetext.split('\n')[:-1]) + u'\n'
        elif category_edit == 'del':
            # Delete existing and separator when deleting categories
            savetext = '\n'.join(savetext.split('\n')[:-2])

    # Add is default
    if category_edit == 'set':
        # Delete existing categories
        confirmed = []
    elif category_edit == 'del':
        # Just in case, do not add anything
        newcategories = []

    if not lines:
        # add separator
        savetext += u'\n----\n'

    # Add categories
    for category in newcategories:
        if category in confirmed:
            continue
        if savetext and savetext[-1] != u'\n':
            savetext += ' '
        savetext += category
    savetext += u'\n' # Should end with newline!

    return savetext

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

def getpage(name, request=None):
    if not request:
        # RequestCLI does not like unicode input
        if isinstance(name, unicode):
            pagename = encode(name)
        else:
            pagename = name

        request = RequestCLI(pagename=pagename)

        formatter = TextFormatter(request)
        formatter.setPage(request.page)
        request.formatter = formatter

    page = PageEditor(request, name)

    return request, page

def getkeys(globaldata, name):
    page = globaldata.getpage(name)
    keys = set(page.get('meta', {}).keys())
    # Non-typed links are not included
    keys.update(set(x for x in page.get('out', {}).keys()
                    if x != '_notype'))
    keys = {}.fromkeys(keys, '')
    return keys

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
    abs_method = target.split(':')[0]

    # Pages from MetaRevisions may have ?action=recall, breaking attach links
    if '?' in quoted:
        quoted = quoted.split('?', 1)[0]

    if abs_method in Parser.attachment_schemas and not '/' in target:
        target = target.replace(':', ':%s/' % (quoted.replace(' ', '_')), 1)

    return target

# Fetch requested metakey value for the given page.
def getmetas(request, globaldata, name, metakeys, 
             display=True, abs_attach=True, checkAccess=True):
    metakeys = set(metakeys)
    pageMeta = dict([(key, list()) for key in metakeys])

    quoted = unicode(url_unquote(name), config.charset)
    if checkAccess:
        if not request.user.may.read(quoted):
            return pageMeta

    loadedPage = globaldata.getpage(name)
    loadedMeta = loadedPage.get("meta", dict())

    # Add values and their sources
    for key in metakeys & set(loadedMeta):
        for value in loadedMeta[key]:
            value = unicode(value, config.charset).strip('"')
            value = value.replace('\\"', '"')
            pageMeta[key].append((value, "meta"))

    # Link values are in a list as there can be more than one edge
    # between two pages.
    if display:
        # Making things nice to look at.
        loadedOuts = loadedPage.get("out", dict())
        for key in metakeys & set(loadedOuts):
            for target in loadedOuts[key]:
                if abs_attach:
                    target = link_to_attachment(globaldata, target)

                pageMeta[key].append((target, "link"))
    else:
        # Showing things as they are
        loadedLits = loadedPage.get("lit", dict())
        for key in metakeys & set(loadedLits):
            for target in loadedLits[key]:
                if abs_attach:
                    target = absolute_attach_name(quoted, target)

                pageMeta[key].append((target, "link"))
            
    return pageMeta

# Currently, the values of metadata and link keys are
# considered additive in case of a possible overlap.
# Let's see how it turns out.
def getvalues(request, globaldata, name, key,
              display=True, abs_attach=True):

    quoted = unicode(url_unquote(name), config.charset)
    if not request.user.may.read(quoted):
        return set([])

    page = globaldata.getpage(name)
    vals = set()
    # Add values and their sources
    if key in page.get('meta', {}):
        for val in page['meta'][key]:
            val = unicode(val, config.charset).strip('"')
            val = val.replace('\\"', '"')
            vals.add((val, 'meta'))
    # Link values are in a list as there can be more than one
    # edge between two pages
    if display:
        # Making things nice to look at
        if key in page.get('out', {}):
            # Add values and their sources
            for target in page['out'][key]:
                if abs_attach:
                    target = link_to_attachment(globaldata, target)

                vals.add((target, 'link'))
    else:
        # Showing things as they are
        if key in page.get('lit', {}):
            # Add values and their sources
            for target in page['lit'][key]:
                if abs_attach:
                    target = absolute_attach_name(quoted, target)

                vals.add((target, 'link'))
            
    return vals

def get_pages(request):
    def filter(name):
        # aw crap, SystemPagesGroup is not a system page
        if name == 'SystemPagesGroup':
            return False
        return not wikiutil.isSystemPage(request, name)

    pages = set([])
    # It seems to help avoiding problems that the query
    # is made by request.rootpage instead of request.page
    for page in request.rootpage.getPageList(filter=filter):
        if not request.user.may.read(page):
            continue
        pages.add(url_quote(encode(page)))

    return pages

def edit(pagename, editfun, request=None,
         category_edit='', catlist=[], lock=None):
    request, p = getpage(pagename, request)

    oldtext = p.get_raw_body()
    newtext = editfun(pagename, oldtext)

    # print
    # print newtext
    # return '', p

    # Add categories, if needed
    if category_edit:
        newtext = edit_categories(request, newtext, category_edit, catlist)

    graphsaver = wikiutil.importPlugin(request.cfg,
                              'action',
                              'savegraphdata')

    # Release the possible readlock that template-savers may have acquired
    if hasattr(request, 'lock'):
        request.lock.release()

    if not newtext:
        return u'No data', p

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

    request.lock = ReadLock(request.cfg.data_dir, timeout=10.0)
    request.lock.acquire()

    return msg, p

def _fix_key(key):
    if not isinstance(key, unicode):
        return unicode(url_unquote(key), config.charset)
    return key

def edit_meta(request, pagename, oldmeta, newmeta,
              category_edit='', catlist=[]):
    def editfun(pagename, oldtext):
        oldtext = oldtext.rstrip()
        # Annoying corner case with dl:s
        if oldtext.endswith('::'):
            oldtext = oldtext + ' '

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
            oldkey = _fix_key(key)
            dl_proto_re = re.compile(dl_proto % (oldkey), re.M)
            dl_add_re = re.compile(dl_add % (oldkey), re.M)

            for i, newval in enumerate(newmeta[key]):
                # print repr(newval)
                # Remove newlines from input, as they could really wreck havoc.
                newval = newval.replace('\n', ' ')
                inclusion = ' %s:: %s' % (oldkey, newval)

                # print repr(inclusion)

                def default_add(request, inclusion, newval, oldtext):
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

                # print "Meta change", repr(key), repr(newval)

                # print key, repr(oldmeta.has_key(key)), repr(oldmeta.get(key, '')), len(oldmeta.get(key, '')), repr(newval.strip())

                # If nothing to do, do nothing
                if (not oldmeta.has_key(key)
                    and not newval.strip()):

                    # print "Nothing to do\n"

                    continue

                # If prototypes ( key:: ) are present, replace them
                elif (dl_proto_re.search(oldtext + '\n')):
                #elif (re.search(dl_proto % (oldkey), oldtext + '\n')):

                    # Do not replace with empties, i.e. status quo
                    if not newval.strip():
                        continue

                    oldkey = _fix_key(key)

                    oldtext = dl_proto_re.sub('\\1 %s' % (newval),
                                              oldtext + '\n', 1)

                    added_keys.add(key)

                    # print "Proto", repr(newval), '\n'

                    continue

                # If the old text has this key (either in old revision
                # or added by this edit), add them (as dl).
                # Cluster values of same keys near
                elif (key in added_keys or
                      (oldmeta.has_key(key) and 
                       len(oldmeta[key]) - 1 < i)):

                    # print "Cluster", repr(newval), repr(oldmeta.get(key, '')), '\n'

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

                    oldtext = default_add(request, inclusion, newval, oldtext)

                # If the old text does not have this key, add it (as dl)
                elif not oldmeta.has_key(key):
                    # print "Newval"
                    oldtext = default_add(request, inclusion, newval, oldtext)
                    added_keys.add(key)

                # Else, replace old value with new value
                else:
                    oldval = oldmeta[key][i]
                    # print "Replace", repr(oldval), repr(newval)
                    # print "# ", repr(oldval)
                    oldkey = _fix_key(key)
                    # First try to replace the dict variable
                    oldtext = dl_re.sub(dl_subfun, oldtext)
                    # Then try to replace the MetaData macro on page
                    oldtext = metadata_re.sub(macro_subfun, oldtext)

                # print

        return oldtext

    msg, p = edit(pagename, editfun, request, category_edit, catlist)

    return msg

def process_edit(request, input,
                 category_edit='', categories={}):
    _ = request.getText
    # request.write(repr(request.form) + '<br>')
    # print repr(input) + '<br>'

    def urlquote(s):
        if isinstance(s, unicode):
            s = s.encode(config.charset)
        return urllib.quote(s)

    def url_unquote(s):
        s = urllib.unquote(s)
        if not isinstance(s, unicode):
            s = unicode(s, config.charset)
        return s

    globaldata = getgraphdata(request)

    changes = dict()
    keychanges = dict()
    keypage = ''

    # Key changes
    for key in input:
        if not key.startswith(':: '):
            continue

        newkey = encode(input[key][0])
        key = key[3:]
        if key == newkey:
            continue

        # Form presents you with ' ' if the key box is empty
        if not newkey.strip():
            newkey = ''

        keychanges[urlquote(key)] = urlquote(newkey)
        # print repr(keychanges)

    for val in input:
        # At least the key 'save' may be there and should be ignored
        if not '!' in val:
            continue

        newvals = input[val]

        keypage, key = val.split('!')

        if not request.user.may.write(url_unquote(keypage)):
            continue

        keypage, key = map(urlquote, [keypage, key])

        oldvals = list()
        for val, typ in getvalues(request, globaldata, keypage,
                                  key, display=False, abs_attach=False):
            # Skip default labels
            if key == 'label' and val == url_unquote(keypage):
                pass
            else:
                oldvals.append(val)

        if oldvals != newvals or keychanges:
            changes.setdefault(keypage, {})
            if key in keychanges:
                # In case of new keys there is no old one
                if key.strip():
                    # print 'deleting key', repr(key)
                    # Otherwise, delete contents of old key
                    changes[keypage].setdefault('old', {})[key] = oldvals
                    changes[keypage].setdefault('new',
                                                {})[key] = [''] * len(oldvals)
                # If new key is empty, don't add anything
                if keychanges[key].strip():
                    # print 'adding key', repr(keychanges[key])
                    if not newvals:
                        newvals = ['']
                    # Otherwise, add old values under new key
                    changes[keypage].setdefault('new',
                                                {})[keychanges[key]] = newvals
            else:
                if oldvals:
                    changes[keypage].setdefault('old', {})[key] = oldvals
                changes[keypage].setdefault('new', {})[key] = newvals

    msg = []
    
    # For category-only changes
    if not changes and category_edit:
        for keypage in categories:
            msg.append('%s: ' % url_unquote(keypage) + \
                       edit_meta(request, url_unquote(keypage),
                                 {}, {},
                                 category_edit, categories[keypage]))
                                 
    elif changes:
        for keypage in changes:
            catlist = categories.get(keypage, [])
            msg.append('%s: ' % url_unquote(keypage) + \
                       edit_meta(request, url_unquote(keypage),
                                 changes[keypage].get('old', dict()),
                                 changes[keypage]['new'],
                                 category_edit, catlist))
    else:
        if keypage:
            msg.append('%s: %s' % (url_unquote(keypage), _("Unchanged")))
        else:
            msg.append(_('No pages changed'))

        # When pages are unchanged, there might be a lock that needs
        # to be released at this stage
        if hasattr(request, 'lock'):
            request.lock.release()

    return msg

def save_template(request, page, template):
    # Get body, or template if body is not available, or ' '
    raw_body = Page(request, page).get_raw_body()
    msg = ''
    if not raw_body:
        raw_body = ' '
        p = PageEditor(request, page)
        template_page = wikiutil.unquoteWikiname(template)
        if request.user.may.read(template_page):
            temp_body = Page(request, template_page).get_raw_body()
            if temp_body:
                raw_body = temp_body

        msg = p.saveText(raw_body, 0)

    return msg

def order_meta_input(request, page, input, action):
    def urlquote(s):
        if isinstance(s, unicode):
            s = s.encode(config.charset)
        return urllib.quote(s)

    # Expects MetaTable arguments
    globaldata, pagelist, metakeys, _ = metatable_parseargs(request, page)

    globaldata.getpage(urlquote(page))

    output = {}
    # Add existing metadata so that values would be added
    for key in input:
        # Strip spaces
        pair = '%s!%s' % (page, key.strip())
        output[pair] = [x.strip() for x in input[key]]

        if key in metakeys:
            if action == 'repl':

                # Add similar, purge rest
                # Do not add a meta value twice
                old = list()
                for val, typ in getvalues(request, globaldata,
                                          urlquote(page),
                                          key, display=False):
                    old.append(val)
                src = set(output[pair])
                tmp = set(src).intersection(set(old))

                dst = []
                # Due to the structure of the edit function,
                # the order of the added values is significant:
                # We want to have the common keys
                # in the same 'slot' of the 'form'
                for val in old:
                    # If we have the common key, keep it
                    if val in tmp:
                        dst.append(val)
                        tmp.remove(val)
                        src.discard(val)
                    # If we don't have the common key,
                    # but still have keys, add a non-common one
                    elif src:
                        added = False
                        for newval in src:
                            if not newval in tmp:
                                dst.append(newval)
                                src.remove(newval)
                                added = True
                                break
                        # If we only had common keys left, add empty
                        if not added:
                            dst.append(u'')
                    else:
                        dst.append(u'')
                if src:
                    dst.extend(src)
                output[pair] = dst
            else:
                # Do not add a meta value twice
                src = list()
                for val, typ in getvalues(request, globaldata,
                                          urlquote(page),
                                          key, display=False):
                    src.append(val)
                for val in src:
                    if val in output[pair]:
                        output[pair].remove(val)
                output[pair].extend(src)

    return output

def savetext(pagename, newtext):
    """ Savetext - a function to be used by local CLI scripts that
    modify page content directly.

    """
    def editfun(pagename, oldtext):
        return newtext

    # For some reason when saving a page with RequestCLI,
    # the pagelinks will present problems with patterns
    # unless explicitly cached
    msg, p = edit(pagename, editfun)
    if msg != u'Unchanged':
        req = p.request
        req.page = p
        p.getPageLinks(req)

    return msg

def metatable_parseargs(request, args,
                        globaldata=None,
                        get_all_keys=False,
                        get_all_pages=False):
    if not args:
        # If called from a macro such as MetaTable,
        # default to getting the current page
        if not get_all_pages and request.page.page_name is not None:
            args = request.page.page_name
        else:
            args = ""

    # Category, Template matching regexps
    cat_re = re.compile(request.cfg.page_category_regex)
    temp_re = re.compile(request.cfg.page_template_regex)

    # Placeholder for list of all pages
    all_pages = []

    # Arg placeholders
    argset = set([])
    keyspec = []
    orderspec = []
    limitregexps = {}

    # list styles
    styles = {}

    # Flag: were there page arguments?
    pageargs = False

    if not globaldata:
        globaldata = getgraphdata(request)

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
                                                     encode(key[1:]), '>')
                    key = key[key.index('>') + 1:].strip()

                    if style:
                        styles[key] = style[0]

                keyspec.append(url_quote(encode(key.strip())))

            continue

        # Metadata regexp, move on
        if '=' in arg:
            data = arg.split("=")
            key = url_quote(encode(data[0]))
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
        all_pages = [unicode(url_unquote(x), config.charset)
                     for x in globaldata]
        for page in all_pages:
            if page_re.match(page):
                argset.add(page)

    def unquote_name(name):
        return unicode(url_unquote(name), config.charset)        

    def is_saved(name):
        return globaldata.getpage(name).has_key('saved')

    def can_be_read(name):
        return request.user.may.read(unquote_name(name))
    
    # If there were no page args, default to all pages
    if not pageargs and not argset:
        # Filter nonexisting pages and the pages the user may not read
        pages = set(filter(can_be_read, filter(is_saved, globaldata)))

    # Otherwise check out the wanted pages
    else:
        # Filter pages the user may not read
        argset = set(url_quote(encode(x)) for x in
                     filter(request.user.may.read, argset))

        pages = set([])

        for arg in argset:
            if cat_re.search(arg):
                # Nonexisting categories
                try:
                    page = globaldata.getpage(arg)
                except KeyError:
                    continue

                if not page.has_key('in'):
                    # no such category
                    continue
                for type in page['in']:
                    for newpage in page['in'][type]:
                        # If page already added
                        if newpage in argset:
                            continue

                        if not (cat_re.search(newpage) or
                                temp_re.search(newpage)):
                            unqname = unquote_name(newpage)
                            # Check that user may view any added pages
                            if request.user.may.read(unqname):
                                pages.add(newpage)
            elif arg:
                # Filter out nonexisting pages
                try:
                    page = globaldata.getpage(arg)
                except KeyError:
                    continue

                # Added filtering of nonexisting and non-local pages
                if not page.has_key('saved'):
                    continue
                
                pages.add(arg)
            
    pagelist = set([])

    for page in pages:
        clear = True
        # Filter by regexps (if any)
        if limitregexps:
            # We're sure we have access to read the page, don't check again
            metas = getmetas(request, globaldata, page, limitregexps,
                             checkAccess=False)

            for key, re_limits in limitregexps.iteritems():

                values = metas[key]
                if not values:
                    clear = False
                    break

                for re_limit in re_limits:
                    clear = False

                    # Iterate all the keys for the value for a match
                    for value, _ in values:
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
                for key in getkeys(globaldata, name):
                    # One further check, we probably do not want
                    # to see categories in our table by default
                    if key != 'WikiCategory':
                        metakeys.add(key)
            else:
                # For MetaTable etc
                for key in nonguaranteeds_p(getkeys(globaldata, name)):
                    # One further check, we probably do not want
                    # to see categories in our table by default
                    if key != 'WikiCategory':
                        metakeys.add(key)

        metakeys = sorted(metakeys, key=str.lower)
    else:
        metakeys = keyspec

    # sorting pagelist
    if not orderspec:
        orderpages = dict()
        for page in pagelist:
            orderpages[ordervalue(page)] = page
        sortlist = sorted(orderpages.keys())
        pagelist = [orderpages[x] for x in sortlist]
    else:
        s_list = dict()
        for dir, key in orderspec:
            s_list[key] = dict()
            for page in pagelist:
                # get all vals of a key in order
                s_list[key][page] = [x for x, y in
                                     sorted(getvalues(request,
                                                      globaldata,
                                                      page,
                                                      url_quote(encode(key))))]
        ordvals = dict()
        byval = dict()
        ord = [x for _, x in orderspec]
        pages = set()

        for dir, key in orderspec:
            byval[key] = dict()

            if not key in s_list:
                continue
            ordvals[key] = set()
            reverse = dir == '>>' and True or False

            for page in s_list[key]:
                pages.add(page)

                if not s_list[key][page]:
                   vals = [None]
                else:
                    vals = s_list[key][page]

                # Patch: no value not included in sorting
                #        break glass if necessary
                # vals = s_list[key][page]
                vals = [ordervalue(x) for x in vals]
                s_list[key][page] = vals

                # Make equivalence classes of key-value pairs
                for val in vals:
                    byval[key].setdefault(val, list()).append(page)

                ordvals[key].update(vals)

            ordvals[key] = sorted(ordvals[key], reverse=reverse)

        # Subfunction to add pages to ordered list and remove
        # them from the pages yet to be sorted
        def olist_add(orderlist, pages, page, key, val):
            if page in pages:
                # print "Adding %s (%s=%s)" % (page, key, val)
                orderlist.append(page)
                pages.remove(page)
            return orderlist, pages

        def order(pages, s_list, byval, ord, orderlist):
            # print "entering order", pages, ord
            for key in ord:
                for val in ordvals[key]:
                    if not pages:
                        return orderlist, pages

                    if not byval[key].has_key(val):
                        # print "Not existing: %s %s" % (key, val)
                        continue

                    # If equivalence class only has one
                    # member, it's the next one in order
                    if len(byval[key][val]) == 1:
                        page = byval[key][val][0]
                        # Skip if already added
                        orderlist, pages = olist_add(orderlist, pages,
                                                     page, key, val)
                    elif len(byval[key][val]) > 1:
                        # print byval[key][val], len(ord)
                        if len(ord) < 2:
                            for page in sorted(byval[key][val]):
                                # print "Adding unsorted", page
                                orderlist, pages = olist_add(orderlist, pages,
                                                             page, key, val)
                        else:
                            newround = list()
                            for page in byval[key][val]:
                                if page in pages:
                                    newround.append(page)
                            if not newround:
                                continue
                        
                            for page in newround:
                                # print 'removing', page
                                pages.remove(page)

                            # print "Next round"
                            orderlist, unord = order(newround, s_list,
                                                     byval, ord[1:], orderlist)

                            for page in sorted(unord):
                                # print "Adding unsorted", page
                                orderlist, _ = olist_add(orderlist, unord,
                                                         page, key, val)

                        # print "and out"

            return orderlist, pages

        pagelist, pages = order(pages, s_list, byval, ord, [])

        # Add the rest of the pages in alphabetical order
        # Should not be needed
        if pages:
            #print "extending with %s" % (pages)
            pagelist.extend(sorted(pages))

    return globaldata, pagelist, metakeys, styles

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
