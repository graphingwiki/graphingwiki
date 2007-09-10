"""
    Graphingwiki editing functions
     - Saving page contents or relevant metadata

    @copyright: 2007 by Juhani Eronen, Erno Kuusela and Joachim Viide
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import os
import re
import string
import xmlrpclib
import urlparse
import socket
import urllib

from urllib import quote as url_quote
from urllib import unquote as url_unquote

from MoinMoin.parser.wiki import Parser
from MoinMoin.action.AttachFile import getAttachDir, getFilename
from MoinMoin.PageEditor import PageEditor
from MoinMoin.request import RequestCLI
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin import caching

from graphingwiki.patterns import GraphData, encode, nonguaranteeds_p

def macro_re(macroname):
    return re.compile(r'\[\[(%s)\((.*?)\)\]\]' % macroname)

metadata_re = macro_re("MetaData")

regexp_re = re.compile('^/.+/$')
# Include \s except for newlines
dl_re = re.compile('\s+(.*?)::\s(.+)')

# These are the match types that really should be noted
linktypes = ["wikiname_bracket", "word",
             "interwiki", "url", "url_bracket"]

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

def check_link(all_re, item):
    # Go through the string with formatting operations,
    # return true if it matches a known linktype
    for match in all_re.finditer(item):
        for type, hit in match.groupdict().items():
            if hit is None:
                continue
            if type in linktypes:
                return (type, hit)

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

# Currently, the values of metadata and link keys are
# considered additive in case of a possible overlap.
# Let's see how it turns out.
def getvalues(globaldata, name, key):
    page = globaldata.getpage(name)
    vals = set()
    # Add values and their sources
    if key in page.get('meta', {}):
        vals = set((x, 'meta') for x in page['meta'][key])
    # Link values are in a list as there can be more than one
    # edge between two pages
    if key in page.get('out', {}):
        # Add values and their sources
        for target in page['out'][key]:
            # Handling attachment URL:s
            try:
                # Try to get the URL attribute of the link target
                dst = globaldata.getpage(target)
                url = dst.get('meta', {}).get('URL', set(['']))
                url = list(url)[0]
                
                # If the URL attribute of the target looks like the
                # target is a local attachment, correct the link
                if 'AttachFile' in url and url.startswith('".'):
                    target = url_unquote(target)
                    target = 'attachment:' + target.replace(' ', '_')
            except:
                pass
            vals.add((target, 'link'))
    return vals

def getmetavalues(globaldata, name, key):
    vals = getvalues(globaldata, name, key)

    default = []
    for val in vals:
        if val[1] == 'link':
            continue
        # Do all the unwrapping, including unquoting, encoding
        # stripping outer quotes and inner quote escapes
        tmp = unicode(url_unquote(val[0]), config.charset).strip('"')
        default.append(tmp.replace('\\"', '"'))

    return default

def getmetalinkvalues(globaldata, name, key):
    vals = getvalues(globaldata, name, key)

    default = []
    for val in vals:
        default.append(val[0])

    return default

def get_pages(request):

    def filter(name):
        # aw crap, SystemPagesGroup is not a system page
        if name == 'SystemPagesGroup':
            return False
        return not wikiutil.isSystemPage(request, name)

    # It seems to help avoiding problems that the query
    # is made by request.rootpage instead of request.page
    pages = set(url_quote(encode(x)) for x in
                request.rootpage.getPageList(filter=filter))

    return pages

def edit(pagename, editfun, request=None):
    request, p = getpage(pagename, request)

    oldtext = p.get_raw_body()
    newtext = editfun(pagename, oldtext)

    graphsaver = wikiutil.importPlugin(request.cfg,
                              'action',
                              'savegraphdata')
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

def _fix_key(key):
    if not isinstance(key, unicode):
        return unicode(url_unquote(key), config.charset)
    return key

def edit_meta(request, pagename, oldmeta, newmeta):
    def editfun(pagename, oldtext):
        oldtext = oldtext.rstrip()

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
            key, val = mo.groups()

            # Check if the value has changed
            key = key.strip()
            if key.strip() == oldkey.strip() and val.strip() == oldval.strip():
                val = newval

            # Do not return placeholders
            if not val.strip():
                return ''

            return '\n %s:: %s' % (key, val)

        for key in newmeta:
            for i, newval in enumerate(newmeta[key]):
                # If the old text does not have this key, add it (as dl)
                if not oldmeta.has_key(key) or not oldmeta[key]:
                    oldkey = _fix_key(key)
                    oldtext += '\n %s:: %s\n' % (oldkey, newval)
                # If the new values has more values, add them (as dl)
                elif len(oldmeta[key]) - 1 < i:
                    oldkey = _fix_key(key)
                    oldtext += '\n %s:: %s\n' % (oldkey, newval)
                # Else, replace old value with new value
                else:
                    oldval = oldmeta[key][i]
                    oldkey = _fix_key(key)
                    # First try to replace the dict variable
                    oldtext = dl_re.sub(dl_subfun, oldtext)
                    # Then try to replace the MetaData macro on page
                    oldtext = metadata_re.sub(macro_subfun, oldtext)

        return oldtext

    msg, p = edit(pagename, editfun, request)

    return msg

def process_edit(request, input):
    # request.write(repr(request.form) + '<br>')

    def urlquote(s):
        if isinstance(s, unicode):
            s = s.encode(config.charset)
        return urllib.quote(s)

    def url_unquote(s):
        s = urllib.unquote(s)
        if not isinstance(s, unicode):
            s = unicode(s, config.charset)
        return s

    globaldata = GraphData(request)

    changes = {}

    for val in input:
        # At least the key 'save' may be there and should be ignored
        if not '!' in val:
            continue

        newvals = input[val]

        keypage, key = [urlquote(x) for x in val.split('!')]

        if not request.user.may.write(url_unquote(keypage)):
            continue

        oldvals = getmetalinkvalues(globaldata, keypage, key)
        print oldvals

        if oldvals != newvals:
            changes.setdefault(keypage, {})
            if not oldvals:
                changes[keypage].setdefault('old', {})[key] = []
            else:
                changes[keypage].setdefault('old', {})[key] = oldvals

            changes[keypage].setdefault('new', {})[key] = newvals
        print changes

    # Done reading, will start writing now
    globaldata.closedb()

    msg = []
    for keypage in changes:
        msg.append('%s: ' % url_unquote(keypage) + \
                   edit_meta(request, url_unquote(keypage),
                             changes[keypage]['old'],
                             changes[keypage]['new']))

    return msg

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

def metatable_parseargs(request, args, globaldata=None):
    # Category, Template matching regexps
    cat_re = re.compile(request.cfg.page_category_regex)
    temp_re = re.compile(request.cfg.page_template_regex)

    # Placeholder for list of all pages
    all_pages = []

    # Arg placeholders
    arglist = []
    keyspec = []

    # Flag: were there page arguments?
    pageargs = False

    # Regex preprocessing
    for arg in (x.strip() for x in args.split(',') if x.strip()):
        # Metadata regexp, move on
        if '=' in arg:
            arglist.append(arg)
            continue

        # metadata key spec, move on
        if arg.startswith('||') and arg.endswith('||'):
            # take order, strip empty ones
            keyspec = [url_quote(encode(x)) for x in arg.split('||') if x]
            continue

        # Ok, we have a page arg, i.e. a page or page regexp in args
        pageargs = True

        # Normal pages, encode and move on
        if not regexp_re.match(arg):
            # If it's a subpage link eg. /Koo, we must add parent page
            if arg.startswith('/'):
                arg = request.page.page_name + arg
            arglist.append(url_quote(encode(arg)))
            continue

        # Ok, it's a page regexp

        # if there's something wrong with the regexp, ignore it and move on
        try:
            page_re = re.compile("%s" % arg[1:-1])
        except:
            continue

        # Get all pages, check which of them match to the supplied regexp
        all_pages = get_pages(request)
        for page in all_pages:
            if page_re.match(page):
                arglist.append(encode(page))

    if not globaldata:
        globaldata = GraphData(request)

    pages = set([])
    metakeys = set([])
    limitregexps = {}

    for arg in arglist:
        if cat_re.search(arg):
            # Nonexisting categories
            try:
                if not request.user.may.read(unicode(url_unquote(arg),
                                                     config.charset)):
                    continue

                page = globaldata.getpage(arg)
            except KeyError:
                continue

            if not page.has_key('in'):
                # no such category
                continue
            for type in page['in']:
                for newpage in page['in'][type]:
                    if not (cat_re.search(newpage) or
                            temp_re.search(newpage)):
                        pages.add(encode(newpage))
        elif '=' in arg:
            data = arg.split("=")
            key = url_quote(encode(data[0]))
            val = encode('='.join(data[1:]))
            # If val starts and ends with /
            if len(val) > 1 and val[::len(val)-1] == '//':
                val = val[1:-1]
            limitregexps.setdefault(key, set()).add(re.compile(val))
        elif arg:
            # Filter out nonexisting pages
            try:
                if not request.user.may.read(unicode(url_unquote(arg),
                                                     config.charset)):
                    continue

                page = globaldata.getpage(arg)
            except KeyError:
                continue
            
            pages.add(arg)

    # If there were no page args, get all non-system pages
    if not pageargs and not pages:
        if not all_pages:
            pages = get_pages(request)
        else:
            pages = all_pages

    pagelist = set([])

    for page in pages:
        clear = True
        # Filter by regexps (if any)
        if limitregexps:
            for key in limitregexps:
                if not clear:
                    break

                # Get values from keys, regardless of their
                # location (meta, link)
                data = string.join(x for x, y in
                                   getvalues(globaldata, page, key))

                # If page does not have the required key, do not add page
                if not data:
                    clear = False
                    break

                # If the found key does not match, do not add page
                for re_limit in limitregexps[key]:
                    if not re_limit.search(data):
                        clear = False
                        break

        # Add page if all the regexps have matched
        if clear:
            pagelist.add(page)

    if not keyspec:
        for name in pagelist:
            for key in nonguaranteeds_p(getkeys(globaldata, name)):
                # One further check, we probably do not want
                # to see categories in our table by default
                if key != 'WikiCategory':
                    metakeys.add(key)

        metakeys = sorted(metakeys, key=str.lower)
    else:
        metakeys = keyspec

    return globaldata, pagelist, metakeys

def check_attachfile(request, pagename, aname):
    # Get the attachment directory for the page
    attach_dir = getAttachDir(request, pagename, create=1)
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
        return {'faultCode': e.args[0],
                'faultString': e.args[1]}
    except socket.gaierror, e:
        return {'faultCode': e[0],
                'faultString': e[1]}

def xmlrpc_attach(wiki, page, fname, username, password, method,
                  content='', overwrite=False):
    srcWiki, _ = xmlrpc_conninit(wiki, username, password)
    if content:
        content = xmlrpclib.Binary(content)

    return xmlrpc_connect(srcWiki.AttachFile, wiki, page, fname,
                          method, content, overwrite)

def xmlrpc_error(error):
    return error['faultCode'], error['faultString']
