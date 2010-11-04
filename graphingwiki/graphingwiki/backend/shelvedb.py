import itertools
import shelve
import os

from graphingwiki.backend.basedb import GraphDataBase
from graphingwiki.util import encode_page, decode_page, encode, log
from graphingwiki import actionname

from MoinMoin.util.lock import ReadLock, WriteLock

from time import time

from graphingwiki.util import node_type, SPECIAL_ATTRS, NO_TYPE

class GraphData(GraphDataBase):
    def __init__(self, request):
        log.debug("shelve graphdb init")
        GraphDataBase.__init__(self, request)

        gddir = os.path.join(request.cfg.data_dir, 'graphdata')
        if not os.path.isdir(gddir):
            os.mkdir(gddir)
        self.graphshelve = os.path.join(gddir, 'graphdata.shelve')

        self.use_sq_dict = getattr(request.cfg, 'use_sq_dict', False)
        if self.use_sq_dict:
            import sq_dict
            self.shelveopen = sq_dict.shelve
        else:
            self.shelveopen = shelve.open

        # XXX (falsely) assumes shelve.open creates file with same name;
        # it happens to work with the bsddb backend.
        if not os.path.exists(self.graphshelve):
            db = self.shelveopen(self.graphshelve, 'c')
            db.close()

        self.db = None
        self.lock = None

        self.cache = dict()
        self.writing = False
        self.readlock()

    def __getitem__(self, item):
        page = encode_page(item)

        if page not in self.cache:
            self.cache[page] = self.db[page]

        return self.cache[page]

    def __setitem__(self, item, value):
        self.savepage(item, value)

    def savepage(self, pagename, pagedict):
        log.debug("savepage %s = %s" % (repr(pagename), repr(pagedict)))
        self.writelock()
        page = encode_page(pagename)

        self.db[page] = pagedict
        self.cache[page] = pagedict

    def cacheset(self, item, value):
        page = encode_page(item)

        self.cache[page] = value

    def __delitem__(self, item):
        self.delpage(item)

    def delpage(self, pagename):
        log.debug("delpage %s" % (repr(pagename),))
        self.writelock()
        page = encode_page(pagename)

        del self.db[page]
        self.cache.pop(page, None)

    def keys(self):
        return map(decode_page, self.db.keys())

    def __iter__(self):
        return itertools.imap(decode_page, self.db)

    def __contains__(self, item):
        page = encode_page(item)
        return page in self.cache or page in self.db

    def set_page_meta_and_acl_and_mtime_and_saved(self, pagename, newmeta, acl, mtime, saved):
        pagedata = self.getpage(pagename)
        pagedata[u'meta'] = newmeta
        pagedata[u'acl'] = acl
        pagedata[u'mtime'] = mtime
        pagedata[u'saved'] = saved
        self.savepage(pagename, pagedata)

    def readlock(self):
        if self.lock is None or not self.lock.isLocked():
            self.lock = ReadLock(self.request.cfg.data_dir, timeout=60.0)
            self.lock.acquire()

        if self.db is None:
            self.db = self.shelveopen(self.graphshelve, "r")
            self.writing = False

    def writelock(self):
        if self.db is not None and not self.writing:
            self.db.close()
            self.db = None
        
        if (self.lock is not None and self.lock.isLocked() and 
            isinstance(self.lock, ReadLock)):
            self.lock.release()
            self.lock = None

        if self.lock is None or not self.lock.isLocked():
            self.lock = WriteLock(self.request.cfg.data_dir, 
                                  readlocktimeout=60.0)
            self.lock.acquire()

        if self.db is None:
            self.db = self.shelveopen(self.graphshelve, "c")
            self.writing = True

    def close(self):
        if self.lock is not None and self.lock.isLocked():
            self.lock.release()
            self.lock = None

        if self.db is not None:
            self.db.close()
            self.db = None

        self.cache.clear()
        self.writing = False

    def commit(self):
        # Ha, puny gullible humans think I do transactions
        pass

    abort = commit


