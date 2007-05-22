"""
    Graphingwiki editing functions
     - Saving page contents or relevant metadata

    @copyright: 2007 by Erno Kuusela and Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import re
import string

from MoinMoin.PageEditor import PageEditor
from MoinMoin.request import RequestCLI
from MoinMoin import wikiutil, caching

def getpage(name):
    req = RequestCLI(pagename=name)
    page = PageEditor(req, name)
    return page

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

def macro_rx(macroname):
    return re.compile(r'\[\[(%s)\((.*?)\)\]\]' % macroname)

metadata_rx = macro_rx("MetaData")

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
