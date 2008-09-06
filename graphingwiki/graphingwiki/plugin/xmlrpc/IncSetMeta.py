"""
    Incremental SetMeta for multi-page updates (prototype).

    @copyright: 2008 by Joachim Viide
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import xmlrpclib

from MoinMoin.util import lock
from MoinMoin.formatter.text_plain import Formatter as TextFormatter

from graphingwiki.patterns import getgraphdata
from graphingwiki.editing import getmetas, edit_meta

def setMetas(request, cleared, discarded, added):
    globaldata = getgraphdata(request)

    pages = set(cleared) | set(discarded) | set(added)
    for page in pages:
        pageCleared = cleared.get(page, set())
        pageDiscarded = discarded.get(page, dict())
        pageAdded = added.get(page, dict())
        
        if "category" in pageCleared:
            pageCleared.remove("category")
            edit_meta(request, page, dict(), dict(), "set", list())
        deletedCategories = pageDiscarded.pop("category", list())
        edit_meta(request, page, dict(), dict(), "del", deletedCategories)
        addedCategories = pageAdded.pop("category", list())
        edit_meta(request, page, dict(), dict(), "add", addedCategories)

        metakeys = set(pageCleared) | set(pageDiscarded) | set(pageAdded)
        old = getmetas(request, globaldata, page, metakeys, checkAccess=False)

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
    _ = request.getText
    request.formatter = TextFormatter(request)

    # FIXME: Appropriate locking for the whole duration of this
    # operation.
    #request.lock = lock.WriteLock(request.cfg.data_dir, timeout=10.0)
    #request.lock.acquire()

    try:
        return setMetas(request, cleared, discarded, added)
    finally:
        #request.lock.release()
        pass
