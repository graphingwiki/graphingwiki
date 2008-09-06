"""
    Incremental SetMeta for multi-page updates (prototype).

    @copyright: 2008 by Joachim Viide
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import xmlrpclib

from MoinMoin import wikiutil
from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from graphingwiki.editing import getmetas, edit_meta
from graphingwiki.patterns import getgraphdata

CATEGORY_KEY = "category"

def setMetas(request, cleared, discarded, added):
    globaldata = getgraphdata(request)

    pages = set(cleared) | set(discarded) | set(added)
    for page in pages:
        pageCleared = cleared.get(page, set())
        pageDiscarded = discarded.get(page, dict())
        pageAdded = added.get(page, dict())
        
        metakeys = set(pageCleared) | set(pageDiscarded) | set(pageAdded)
        old = getmetas(request, globaldata, page, metakeys, checkAccess=False)

        # Handle the magic duality between normal categories (CategoryBah)
        # and meta style categories
        if CATEGORY_KEY in pageCleared:
            edit_meta(request, page, dict(), dict(), "set", list())
        if CATEGORY_KEY in pageDiscarded:
            categories = pageDiscarded[CATEGORY_KEY]
            edit_meta(request, page, dict(), dict(), "del", categories)
        if CATEGORY_KEY in pageAdded:
            categories = set(pageAdded[CATEGORY_KEY])
            filtered = wikiutil.filterCategoryPages(request, categories)
            filtered = set(filtered) - set(old.get(CATEGORY_KEY, set()))
            edit_meta(request, page, dict(), dict(), "add", list(filtered))
            pageAdded[CATEGORY_KEY] = list(categories - filtered)

        new = dict()
        for key, values in old.iteritems():
            values = [value for (value, _) in values]
            old[key] = list(values)
            new[key] = set(values)
        for key in pageCleared:
            new[key] = set()
        for key, values in pageDiscarded.iteritems():
            new[key].difference_update(values)
        for key, values in pageAdded.iteritems():
            new[key].update(values)

        for key, values in new.iteritems():
            ordered = list(old[key])

            for index, value in enumerate(ordered):
                if value not in values:
                    ordered[index] = u""
                values.discard(value)

            ordered.extend(values)
            new[key] = ordered

        edit_meta(request, page, old, new)

    return True

def execute(xmlrpcobj, cleared, discarded, added, query="", handle=None):
    request = xmlrpcobj.request
    request.formatter = TextFormatter(request)

    return setMetas(request, cleared, discarded, added)
