"""
    Graphingwiki editing functions
     - Saving page contents or relevant metadata

    @copyright: 2007 by Erno Kuusela and Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import os
import re
import string
import xmlrpclib
import urlparse

from urllib import quote as url_quote
from urllib import unquote as url_unquote

from MoinMoin.action.AttachFile import getAttachDir
from MoinMoin.PageEditor import PageEditor
from MoinMoin.request import RequestCLI
from MoinMoin import wikiutil
from MoinMoin import config

from graphingwiki.patterns import GraphData, encode, nonguaranteeds_p

def macro_rx(macroname):
    return re.compile(r'\[\[(%s)\((.*?)\)\]\]' % macroname)

regexp_re = re.compile('^/.+/$')
metadata_rx = macro_rx("MetaData")

def getpage(name):
    req = RequestCLI(pagename=name)
    page = PageEditor(req, name)
    return page

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
        vals.update(set((x, 'link') for x in page['out'][key]))
    return vals

def getmetavalues(globaldata, name, key):
    vals = getvalues(globaldata, name, key)
    
    default = []
    for val in vals:
        if val[1] == 'link':
            continue
        default.append(unicode(url_unquote(val[0]),
                               config.charset).strip('"'))

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

def edit(pagename, request, editfun):
    p = getpage(pagename)
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
    return msg

def edit_meta(request, pagename, metakey, oldval, newmetaval):
    def editfun(pagename, oldtext):
        if not oldval:
            # add new tag
            return oldtext.rstrip() + '\n[[MetaData(%s, %s)]]\n' % (metakey, newmetaval)
        
        def subfun(mo):
            old_keyval_pairs = mo.group(2).split(',')
            newargs=[]
            for key, val in zip(old_keyval_pairs[::2], old_keyval_pairs[1::2]):
                key = key.strip()
                if key.strip() == metakey.strip() and val.strip() == oldval.strip():
                    val = newmetaval
                newargs.append('%s,%s' % (key, val))
            return '[[MetaData(%s)]]' % (string.join(newargs, ','))

        return metadata_rx.sub(subfun, oldtext)

    return edit(pagename, request, editfun)

def savetext(request, pagename, newtext):
    def editfun(pagename, oldtext):
        return newtext
    return edit(pagename, request, newtext)

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
            # Nonexisting pages
            try:
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

def save_attachfile(request, pagename, srcname, aname):
    try:
        # Read the contents of the file
        filecontent = file(srcname).read()

        # Get the attachment directory for the page
        attach_dir = getAttachDir(request, pagename, create=1)
        fpath = os.path.join(attach_dir, aname)

        # Save the data to a file under the desired name
        stream = open(fpath, 'wb')
        stream.write(filecontent)
        stream.close()
    except:
        return False

    return True

def xmlrpc_attachfile(wiki, page, fname, content, username, password):
    scheme, netloc, path, _, _, _ = urlparse.urlparse(wiki)

    netloc = "%s:%s@%s" % (username, password, netloc)

    action = "action=xmlrpc2"
    url = urlparse.urlunparse((scheme, netloc, path, "", action, ""))
    srcWiki = xmlrpclib.ServerProxy(url)
    content = xmlrpclib.Binary(content)

    return srcWiki.AttachFile(page, fname, content)
