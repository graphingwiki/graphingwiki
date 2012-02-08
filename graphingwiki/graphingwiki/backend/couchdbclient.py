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

import os

from graphingwiki.backend.basedb import GraphDataBase
from graphingwiki.util import log

import couchdb
import couchdb.mapping

class DbError(Exception):
    pass

def jsquote(s):
    return u''.join(['\\u%04x' % ord(c) for c in s])

class GraphData(GraphDataBase):
    def __init__(self, request, dbname="gwiki", couchurl=None):
        log.debug("couchdb graphdb init")
        GraphDataBase.__init__(self, request)

        self.dbname = dbname
        if couchurl:
            self.couch_server = couchdb.Server(couchurl)
        else:
            self.couch_server = couchdb.Server()

        self.make_pagemeta_class()
        
        # we could really use db connection recycling/pooling...
        self.init_db()

        # use write cache/bulk update workaround for rehash slowness,
        # unsafe otherwise
        self.doing_rehash = False
        self.modified_pages = {}


    def make_pagemeta_class(self):
        # defining class here lets us use dbname in making viewfields
        dbname = self.dbname
        class PageMeta(couchdb.mapping.Document):
            pagename = couchdb.mapping.TextField()
            out = couchdb.mapping.DictField()
            meta = couchdb.mapping.DictField()
            mtime = couchdb.mapping.FloatField()
            saved = couchdb.mapping.BooleanField()
            acl = couchdb.mapping.TextField()

            by_pagename = couchdb.mapping.ViewField(dbname,
                             'function (doc) { emit(doc.pagename, doc); }')
            by_meta = couchdb.mapping.ViewField(dbname,
                             'function (doc) { for (var key in doc.meta) emit(key, doc); }')

            by_out = couchdb.mapping.ViewField(dbname,
                             'function (doc) { for (var linktype in doc.out) { for (var i in doc.out[linktype]) { emit(doc.pagename, doc.out[linktype][i]); } }')

            by_in = couchdb.mapping.ViewField(dbname,
                             'function(doc) { for (var lt in doc.out) { for (var i in doc.out[lt]) { emit(doc.out[lt][i], doc.pagename); }}}')

        self.pagemeta_class = PageMeta
        
    def savepage(self, pagedoc):
        if self.doing_rehash:
            pagename = pagedoc["pagename"]
            if not isinstance(pagename, unicode):
                pagename = unicode(pagename, 'utf-8')
            self.modified_pages[pagename] = pagedoc
        else:
            pagedoc.store(self.couch_db)

    def init_db(self):
        try:
            self.couch_server.create(self.dbname)
        except couchdb.PreconditionFailed:
            pass

        self.couch_db = self.couch_server[self.dbname]
        viewfields = []
        for xname in vars(self.pagemeta_class):
            if xname.startswith('by_'):
                x = getattr(self.pagemeta_class, xname)
                if isinstance(x, couchdb.design.ViewDefinition):
                    viewfields.append(x)

        couchdb.design.ViewDefinition.sync_many(self.couch_db, viewfields)

    def getpage(self, pagename):
        try:
            pagedoc = self.getpagedoc(pagename)
        except KeyError:
            pagedoc = self.pagemeta_class(pagename=pagename, out={}, meta={},
                               mtime=0, saved=True, acl=u'')
            self.savepage(pagedoc)

        return pagedoc

    def getpagedoc(self, pagename):
        if not isinstance(pagename, unicode):
            pagename = unicode(pagename, 'utf-8')

        if self.doing_rehash and pagename in self.modified_pages:
            return self.modified_pages[pagename]

        docs = list(self.pagemeta_class.by_pagename(self.couch_db, key=pagename))
        
        if len(docs) == 1:
            return docs[0]
        elif len(docs) == 0:
            raise KeyError(pagename)
        else:
            raise DbError("Multiple pages named " + repr(pagename))

    def pagenames(self):
        x = self.pagemeta_class.by_pagename(self.couch_db)
        return map(lambda m: m.pagename,
                   list(x))

    def is_saved(self, pagename):
        try:
            pagedoc = self.getpagedoc(pagename)
        except KeyError:
            return True
        else:
            return pagedoc.saved

    def delpage(self, pagename):
        pagedoc = self.getpagedoc(pagename)
        if not pagedoc:
            raise KeyError(pagename)
        else:
            self.couch_db.delete(pagedoc)

    def clear_page(self, pagename):
        if self.get_in(pagename):
            pagedoc = self.getpagedoc(pagename)
            pagedoc.saved = False
            pagedoc.out.clear()
            pagedoc.meta.clear()
            self.savepage(pagedoc)
        else:
            self.delpage(pagename)

    def set_page_meta_and_acl_and_mtime_and_saved(self, pagename, newmeta, acl, mtime, saved):
        pagedoc = self.getpagedoc(pagename)
        pagedoc.meta.clear()
        pagedoc.meta.update(newmeta)
        pagedoc.acl = acl
        pagedoc.mtime = mtime
        pagedoc.saved = saved

        self.savepage(pagedoc)

    def close(self):
        pass

    def abort(self):
        # couchdb can't abort, just close
        self.close()
        
        
    def get_out(self, pagename):
        return dict(self.getpage(pagename).out)

    def get_in(self, pagename):
        this_page = self.getpage(pagename)
        pages = self.pagemeta_class.by_in(self.couch_db, key=pagename, include_docs=True)
        indict = {}
        
        for p in pages:
            print 'get_in', p
            for lt, tolist in p.out.items():
                if pagename in tolist:
                    l = indict.setdefault(lt, [])
                    if p.pagename not in l:
                        l.append(p.pagename)

        return indict

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

        self.savepage(frompd)

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
        
        self.savepage(frompd)

    def clear_metas(self):
        log.debug("deleting db from couchdb: ", self.dbname)
        del self.couch_server[self.dbname]
        self.init_db()

    def commit(self):
        # Ha, puny gullible humans think I do transactions
        # .. instead, I abuse this metod for rehash mode & bulk update
        if self.doing_rehash:
            log.debug("commit in rehash mode, doing bulk update")
            for success, docid, rev_or_exc in self.couch_db.update(self.modified_pages.values()):
                if not success:
                    raise DbError(
                        "at least one update failed while writing updated docs at end of rehash. first exception docid: %s exception: %s" % (docid, rev_or_exc))
                
            self.modified_pages = {}

    abort = commit
        
def test_category(gd):
    categories = filter(lambda x: x.startswith("Category"), gd.pagenames())
    for c in categories:
        catmembers = gd.get_in(c)
        print 'pages in', c + ':', len(catmembers)
        for p in catmembers:
            assert c in p.out[u"gwikicategory"], "%s member %s doesn't have cat in links: %s " % (c, p.pagename, repr(p.out["gwikicategory"]))

def test_inlink(gd):
    print 'cross checking inlinks'
    for i, pn in enumerate(gd.pagenames()):
        print i, pn
        out = gd.getpage(pn).out
        if out:
            for olt, onames in out.items():
                for oname in onames:
                    print '   ', olt, oname
                    ins = gd.get_in(oname)
                    assert pn in ins.get(olt, []), "%s has link to %s but inlinks from there don't match, outlinkss=%s" % (pn, oname, repr(out))
        if i == 5000:
            print 'stopping after 500 checks'
            break

    
def test():
    dbname = os.getenv("USER") + "dev-standalone"
    from graphingwiki import RequestCLI
    req = RequestCLI()
    gd = GraphData(req, dbname)

    if 0:
        test_inlink(gd)

    if 0:
        test_category(gd)

    print "get_in(FrontPage) ->", gd.get_in(u"FrontPage")
    print "get_out(FrontPage) ->", gd.get_out(u"FrontPage")

    if 0:
        print "FrontPage in pagenames() ->", u"FrontPage" in gd.pagenames()


    if 0:
        print 'db dump:'
        pagelist = gd.pagenames()
        pagelist.sort()

        for pn in pagelist:
            
            o = gd.get_out(pn)
            i = gd.get_in(pn)
            m = gd.get_meta(pn)
            if not (i or o):
                continue

            print pn
            if o:
                print '  outgoing links:'
                for key, link in sorted(o.items()):
                    print ' '*4, key, '->', link
            if i:
                print '  incoming links:'
                for key, link in sorted(i.items()):
                    print ' '*4, key, '<-[' + link + ']', pn

            if m:
                print '  metas:'
                for key, link in sorted(m.items()):
                    print ' '*4, key, '->', link
                
            print

if __name__ == '__main__':
    test()
