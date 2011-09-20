# -*- coding: utf-8 -*-

"""
CouchDB backend for gwiki

There are some data integrity and performance problems with CouchDB:

 1. On the ACID front everything looks peachy in when you read the
first sentence in the CouchDB overview: "The CouchDB file layout and
commitment system features all Atomic Consistent Isolated Durable
(ACID) properties". But then it then goes on to explain the CouchDB
variety of ACID. There are no transactions, the only primitive is the
atomicity of single operations on documents. The only ACID op is
reading or writing a single CouchDB document! You don't even get a
read-modify-write. To keep data ACIDity the application would have to
use these weak building blocks and pile on additional code and
complexity to invent a safe way of encoding the application data per
use case (as witnessed by the bank account balance recipe in the docs
where they suggest creating a new document per account transaction).

 2. You need to use views to get any kind of meaningful use out of
CouchDB, but they're horribly broken development-wise. The JS views
fail silently. You'll never know your view function is failing, you'll
just get wrong answers. To further comfort you, the documentation
states "Playing with (malformed) views is currently the best way to
bring the couchdb server in an unstable state.".

 3. The performance is in some cases abysmal unless you spend effort
and code complexity on perf hacks. For example, rehashing performance
is about one gwiki page per second without jumping through the bulk
API hoops. Using bulk API is tricky in gwiki since we want to do
read-modify-writes and see previous RMW:s on subsequent update
operations.

The consistency/integrity picture is further muddied by the so-called
"all-or-nothing" bulk update API. You can slightly increase your luck
if you want to take your chances with the data in this mode. This
requires you to reoganise your application code to accumulate your
writes and perform them in one "atomic" (not really) operation. Even
if this worked, it still wouldn't let you perform eg updaes, since you
couldn't perform updates (read value and write a derived value). But,
even with this half-assed route your data is still not safe, according
to docs.

To quote Damien Katz: "It's possible (trivial almost) for CouchDB to
do multi-document transactions, but they don't make any sense in the
distributed case, a primary goal of CouchDB. CouchDB might someday
have multi-document commits, but for now CouchDB is focusing on the
distributed edit model."

"""

import itertools
import os, operator
from time import time
from collections import defaultdict

from graphingwiki.backend.basedb import GraphDataBase
from graphingwiki.util import encode_page, decode_page, encode
from graphingwiki import actionname
from graphingwiki.util import node_type, SPECIAL_ATTRS, NO_TYPE, log

import couchdb
import couchdb.mapping

class DbError(Exception):
    pass

def jsquote(s):
    return u''.join(['\\u%04x' % ord(c) for c in s])

class PageMeta(couchdb.mapping.Document):
    pagename = couchdb.mapping.TextField()
    out = couchdb.mapping.DictField()
    meta = couchdb.mapping.DictField()
    mtime = couchdb.mapping.FloatField()
    saved = couchdb.mapping.BooleanField()
    acl = couchdb.mapping.TextField()

    by_pagename = couchdb.mapping.ViewField('gwiki',
                 'function (doc) { emit(doc.pagename, doc); }')
    by_meta = couchdb.mapping.ViewField('gwiki',
                'function (doc) { for (var key in doc.meta) emit(key, doc); }')
    by_out = couchdb.mapping.ViewField('gwiki',
                'function (doc) { for (var key in doc.out) emit(key, doc); }')
    by_in = couchdb.mapping.ViewField('gwiki',
                'function (doc) { for (var key in doc.out) emit(doc[key], null); }')

class GraphData(GraphDataBase):
    def __init__(self, request, dbname="gwiki"):
        log.debug("couchdb graphdb init")
        GraphDataBase.__init__(self, request)
        
        self.dbname = dbname
        self.couch_server = couchdb.Server()
        self.init_db()

        viewfields = []
        PageMeta.by_in
        for xname in vars(PageMeta):
            if xname.startswith('by_'):
                x = getattr(PageMeta, xname)
                if isinstance(x, couchdb.design.ViewDefinition):
                    viewfields.append(x)

        couchdb.design.ViewDefinition.sync_many(self.couch_db, viewfields)

    def init_db(self):
        try:
            self.couch_server.create(self.dbname)
        except couchdb.PreconditionFailed:
            pass

        self.couch_db = self.couch_server[self.dbname]


    def get_out(self, pagename):
        return dict(self.getpage(pagename).out)

    def getpage(self, pagename):
        try:
            pagedoc = self.getpagedoc(pagename)
        except KeyError:
            pagedoc = PageMeta(pagename=pagename, out={}, meta={},
                               mtime=0, saved=True, acl=u'')
            pagedoc.store(self.couch_db)
        return pagedoc

    def getpagedoc(self, pagename):
        if not isinstance(pagename, unicode):
            pagename = unicode(pagename, 'utf-8')

        docs = list(PageMeta.by_pagename(self.couch_db, key=pagename))
        
        if len(docs) == 1:
            return docs[0]
        elif len(docs) == 0:
            raise KeyError(pagename)
        else:
            raise DbError("Multiple pages named " + repr(pagename))

    def pagenames(self):
        x = PageMeta.by_pagename(self.couch_db)
        return map(lambda m: m.pagename,
                   list(x))

    def is_saved(self, pagename):
        pagedoc = self.getpagedoc(pagename)
        return pagedoc.saved

    def delpage(self, pagename):
        pagedoc = self.getpagedoc(pagename)
        if not pagedoc:
            raise KeyError(pagename)
        else:
            self.couch_db.delete(pagedoc)

    def set_page_meta_and_acl_and_mtime_and_saved(self, pagename, newmeta, acl, mtime, saved):
        pagedoc = self.getpagedoc(pagename)
        pagedoc.meta.clear()
        pagedoc.meta.update(newmeta)
        pagedoc.acl = acl
        pagedoc.mtime = mtime
        pagedoc.saved = saved
        pagedoc.store(self.couch_db)

    def close(self):
        pass

    def abort(self):
        # couchdb can't abort, just close
        self.close()
        
        
    def get_out(self, pagename):
        return dict(self.getpage(pagename).out)

    def get_in(self, pagename):
        res = PageMeta.out_in(self.couch_db, key=pagename, include_docs=True)
        out = {}
        for row in res:
            in_key = row.key
            in_pagename = row.value
            out[in_key] = in_pagename
        return out

    def get_meta(self, pagename):
        return self.getpage(pagename).get(u'meta', {})

    def get_metakeys(self, pagename):
        """
        Return the complete set of page's (non-link) meta keys, plus gwiki category.
        """
        # todo: move this to basedb & remove from impls
        return set(self.get_meta(pagename).keys()) | set([u'gwikicategory'])

    def add_in(self, (frm, to), linktype):
        pass

    def add_out(self, (frompage, topage), linktype):
        frompd = self.getpagedoc(frompage)
        pagelist = frompd.out.setdefault(linktype, [])
        if topage not in pagelist:
            pagelist.append(topage)

        frompd.store(self.couch_db)

    def remove_in(self, (frompage, topage), linktype):
        pass
        
    def remove_out(self, (frompage, topage), types):
        frompd = self.getpagedoc(frompage)
        outlinks = frompd.out
        for tp in types:
            try:
                l = outlinks[tp]
            except KeyError:
                continue
            while topage in l:
                l.remove(topage)
            if not l:
                del outlinks[tp]
        
        frompd.store(self.couch_db)

    def clear_metas(self):
        del self.couch_server[self.dbname]
        self.init_db()

    def commit(self):
        # Ha, puny gullible humans think I do transactions
        pass

    abort = commit
        
