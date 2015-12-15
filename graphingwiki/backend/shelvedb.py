# -*- coding: utf-8 -*-

"""
Shelve backend for gwiki

This is the original gwiki backend. It's slow, it occasionally
corrupts itself and it's pessimal at concurrency (uses a lock file).
Needless to say, it doesn't do ACID.

"""
import shelve
import random
import errno
import fcntl
import os

from graphingwiki.backend.basedb import GraphDataBase
from graphingwiki.util import encode_page, decode_page, log

from time import time, sleep

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
                    raise LockTimeout()
                sleep(timeout)
        except:
            if fd is not None:
                fcntl.lockf(fd, fcntl.LOCK_UN)
                os.close(fd)
            raise

        self._fd = fd

    def release(self):
        if self._fd is None:
            return False

        fcntl.lockf(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)
        self._fd = None
        return True

class GraphData(GraphDataBase):
    is_acid = False

    UNDEFINED = object()

    def __init__(self, request, **kw):
        log.debug("shelve graphdb init")
        GraphDataBase.__init__(self, request, **kw)

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
        self.out = dict()

        lock_path = os.path.join(gddir, "graphdata-lock")
        self._lock_timeout = getattr(request.cfg, 'graphdata_lock_timeout', None)
        self._readlock = _Lock(lock_path, exclusive=False)
        self._writelock = _Lock(lock_path, exclusive=True)

    def __getitem__(self, item):
        page = encode_page(item)

        if page in self.out:
            if self.out[page] is self.UNDEFINED:
                raise KeyError(page)
            return self.out[page]

        if page in self.cache:
            return self.cache[page]

        self.readlock()
        self.cache[page] = self.db[page]
        return self.cache[page]

    def __setitem__(self, item, value):
        self.savepage(item, value)

    def savepage(self, pagename, pagedict):
        log.debug("savepage %s = %s" % (repr(pagename), repr(pagedict)))
        page = encode_page(pagename)

        self.out[page] = pagedict
        self.cache.pop(page, None)

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
        page = encode_page(pagename)

        self.out[page] = self.UNDEFINED
        self.cache.pop(page, None)

    def __iter__(self):
        self.readlock()

        for key in self.db.keys():
            if self.out.get(key, None) is self.UNDEFINED:
                continue
            yield decode_page(key)

    def keys(self):
        return list(self.__iter__())

    def __contains__(self, item):
        page = encode_page(item)

        if page in self.out:
            return self.out[page] is not self.UNDEFINED

        if page in self.cache:
            return True

        self.readlock()
        return page in self.db

    def set_page_meta_and_acl_and_mtime_and_saved(self, pagename, newmeta,
                                                  acl, mtime, saved):
        pagedata = self.getpage(pagename)
        pagedata[u'meta'] = newmeta
        pagedata[u'acl'] = acl
        pagedata[u'mtime'] = mtime
        pagedata[u'saved'] = saved
        self.savepage(pagename, pagedata)

    def clear_page(self, pagename):
        if self.get_in(pagename):
            pagedata = self.getpage(pagename)
            pagedata[u'saved'] = False
            pagedata[u'meta'] = dict()
            pagedata[u'out'] = dict()
            self.savepage(pagename, pagedata)
        else:
            self.delpage(pagename)

    def readlock(self):
        if self._writelock.is_locked():
            return
        if self._readlock.is_locked():
            return

        log.debug("getting a read lock for %r" % (self.graphshelve,))
        try:
            self._readlock.acquire(self._lock_timeout)
        except LockTimeout:
            items = self.graphshelve, self._lock_timeout
            log.error("getting a read lock for %r timed out after %.02fs" % items)
            raise
        log.debug("got a read lock for %r" % (self.graphshelve,))

        self.db = self.shelveopen(self.graphshelve, "r")

    def writelock(self):
        if self._writelock.is_locked():
            return

        if self._readlock.is_locked():
            if self.db is not None:
                self.db.close()
                self.db = None
            self._readlock.release()
            log.debug("released a write lock for %r" % (self.graphshelve,))

        log.debug("getting a write lock for %r" % (self.graphshelve,))
        try:
            self._writelock.acquire(self._lock_timeout)
        except LockTimeout:
            items = self.graphshelve, self._lock_timeout
            log.error("getting a write lock for %r timed out after %.02fs" % items)
            raise
        log.debug("got a write lock for %r" % (self.graphshelve,))

        self.db = self.shelveopen(self.graphshelve, "c")

    def close(self):
        if self.out:
            self.writelock()

            for key, value in self.out.items():
                if value is self.UNDEFINED:
                    self.db.pop(key, None)
                else:
                    self.db[key] = value

            self.out = dict()

        self.cache.clear()

        if self.db is not None:
            self.db.close()
            self.db = None

        if self._writelock.release():
            log.debug("released a write lock for %r" % (self.graphshelve,))
        else:
            log.debug("did not release any write locks for %r" % (self.graphshelve,))

        if self._readlock.release():
            log.debug("released a read lock for %r" % (self.graphshelve,))
        else:
            log.debug("did not released any read locks for %r" % (self.graphshelve,))

    def commit(self):
        # Ha, puny gullible humans think I do transactions
        pass

    abort = commit

