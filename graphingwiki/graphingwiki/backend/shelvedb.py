import itertools
import shelve
import random
import errno
import fcntl
import os

from graphingwiki.backend.basedb import GraphDataBase
from graphingwiki.util import encode_page, decode_page, encode, log
from graphingwiki import actionname

from time import time, sleep

from graphingwiki.util import node_type, SPECIAL_ATTRS, NO_TYPE

class LockTimeout(Exception):
    pass

class _Lock(object):
    CHECK_INTERVAL = 0.05

    def __init__(self, lock_path, exclusive=False):
        self._lock_path = lock_path
        self._exclusive = exclusive
        self._fd = None

    def is_locked(self):
        return self._fd is not None

    def acquire(self, timeout=None):
        if self._fd is not None:
            return

        if timeout is not None:
            expires = time() + timeout
        else:
            expires = None

        fd = None
        try:
            while True:
                if fd is None:
                    fd = os.open(self._lock_path, os.O_CREAT | os.O_RDWR)

                if fd is not None:
                    mode = fcntl.LOCK_SH
                    if self._exclusive:
                        mode = fcntl.LOCK_EX

                    try:
                        fcntl.lockf(fd, mode | fcntl.LOCK_NB)
                    except IOError, error:
                        if error.errno not in (errno.EAGAIN, errno.EACCES):
                            raise
                    else:
                        break

                timeout = self.CHECK_INTERVAL
                if expires is not None:
                    remaining = expires - time()
                    remaining -= 0.5 * remaining * random.random()
                    timeout = min(timeout, remaining)
                if timeout <= 0:
                    raise _LockTimeout()
                sleep(timeout)
        except:
            if fd is not None:
                fcntl.lockf(fd, fcntl.LOCK_UN)
                os.close(fd)
            raise

        self._fd = fd

    def release(self):
        if self._fd is None:
            return
        fcntl.lockf(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)
        self._fd = None

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
        self.cache = dict()

        lock_path = os.path.join(gddir, "graphdata-lock")
        self._readlock = _Lock(lock_path, exclusive=False)
        self._writelock = _Lock(lock_path, exclusive=True)

    def _lock(self):
        filename = os.path.join(gddir, 'graphdata.shelve')
        os.open()

    def __getitem__(self, item):
        page = encode_page(item)

        if page not in self.cache:
            self.readlock()
            self.cache[page] = self.db[page]

        return self.cache[page]

    def __setitem__(self, item, value):
        self.savepage(item, value)

    def savepage(self, pagename, pagedict):
        log.debug("savepage %s = %s" % (repr(pagename), repr(pagedict)))
        page = encode_page(pagename)

        self.writelock()
        self.db[page] = pagedict
        self.cache[page] = pagedict

    def is_saved(self, pagename):
        return self.getpage(pagename).get('saved', False)

    def get_out(self, pagename):
        return self.getpage(pagename).get(u'out', {})

    def get_in(self, pagename):
        return self.getpage(pagename).get(u'in', {})

    def get_meta(self, pagename):
        return self.getpage(pagename).get(u'meta', {})

    def get_metakeys(self, name):
        """
        Return the complete set of page's (non-link) meta keys, plus gwiki category.
        """

        page = self.getpage(name)
        keys = set(page.get('meta', dict()))

        if page.get('out', dict()).has_key('gwikicategory'):
            keys.add('gwikicategory')

        return keys

    def pagenames(self):
        return self.iterkeys()

    def cacheset(self, item, value):
        page = encode_page(item)

        self.cache[page] = value

    def __delitem__(self, item):
        self.delpage(item)

    def delpage(self, pagename):
        log.debug("delpage %s" % (repr(pagename),))
        self.writelock()
        page = encode_page(pagename)

        self.writelock()
        del self.db[page]
        self.cache.pop(page, None)

    def keys(self):
        self.readlock()
        return map(decode_page, self.db.keys())

    def __iter__(self):
        self.readlock()
        return itertools.imap(decode_page, self.db)

    def __contains__(self, item):
        page = encode_page(item)
        self.readlock()
        return page in self.cache or page in self.db

    def set_page_meta_and_acl_and_mtime_and_saved(self, pagename, newmeta, acl, mtime, saved):
        pagedata = self.getpage(pagename)
        pagedata[u'meta'] = newmeta
        pagedata[u'acl'] = acl
        pagedata[u'mtime'] = mtime
        pagedata[u'saved'] = saved
        self.savepage(pagename, pagedata)

    def readlock(self):
        self._readlock.acquire()
        if self.db is None:
            self.db = self.shelveopen(self.graphshelve, "r")

    def writelock(self):
        if not self._writelock.is_locked() and self.db is not None:
            self.db.close()
            self.db = None

        self._writelock.acquire()
        if self.db is None:
            self.db = self.shelveopen(self.graphshelve, "c")

    def close(self):
        if self.db is not None:
            self.db.close()
            self.db = None

        self._writelock.release()
        self._readlock.release()

        self.cache.clear()

    def commit(self):
        # Ha, puny gullible humans think I do transactions
        pass

    abort = commit


