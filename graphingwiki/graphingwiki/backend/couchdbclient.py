import itertools
import os, operator
from time import time
from collections import defaultdict

from graphingwiki.backend.basedb import GraphDataBase
from graphingwiki.util import encode_page, decode_page, encode
from graphingwiki import actionname
from graphingwiki.util import node_type, SPECIAL_ATTRS, NO_TYPE, log

import couchdb

class DbError(Exception):
    pass

def jsquote(s):
    return u''.join(['\\u%04x' % ord(c) for c in s])


class GraphData(GraphDataBase):
    def __init__(self, request):
        log.debug("shelve graphdb init")
        GraphDataBase.__init__(self, request)
        
        dbname = "gwiki"
        self.couch_server = couchdb.Server()
        try:
            self.couch_server.create(dbname)
        except couchdb.client.PreconditionFailed:
            pass

        self.couch_db = self.couch_server[dbname]

    def get_out(self, pagename):
        return self.getpage(pagename)["out"]

    def getpage(self, pagename):
        p = self.getpagedoc(pagename)
        if p is None:
            cid = self.couch_db.create(dict(pagename=pagename, out={}, unlinks={}, mtime=0, saved=True, acl=u''))
            p = self.getpagedoc(pagename)
            if p is None:
                raise DbError("created doc %s for page %s not found" % (cid, pagename))
        return p

    def getpagedoc(self, pagename):
        if not isinstance(pagename, unicode):
            pagename = unicode(pagename, 'utf-8')

        for row in self.couch_db.query(u"function(doc) { if (doc.pagename == '%s') emit(doc.pagename, null); }" % jsquote(pagename)):
            return self.couch_db[row.id]

    def pagenames(self):
        for row in paa.query(u"function(doc) { if (doc.pagename != null) emit(doc.pagename, null); }" % jsquote(pagename)):
            yield row.key

    def delpage(self, pagename):
        pagedoc = self.getpagedoc(pagename)
        if not pagedoc:
            raise KeyError(pagename)
        else:
            self.couch_db.delete(pagedoc)

    def set_page_meta_and_acl_and_mtime_and_saved(self, pagename, newmeta, acl, mtime, saved):
        pagedoc = self.getpagedoc(pagename)
        pagedoc[u'meta'] = newmeta
        pagedoc[u'acl'] = acl
        pagedoc[u'mtime'] = mtime
        pagedoc[u'saved'] = saved
        self.couch_db[pagedoc.id] = pagedoc

    def close(self):
        pass

    def abort(self):
        # couchdb can't abort, just close
        self.close()
        
    def add_in(self, (frm, to), linktype):
        pass

    def add_out(self, (frompage, topage), linktype):
        frompd = self.getpagedoc(frompage)
        pagelist = frompd["out"].setdefault(linktype, [])
        if topage not in pagelist:
            pagelist.append(topage)
        self.couch_db[frompd.id] = frompd
        
    def remove_out(self, (frompage, topage), types):
        frompd = self.getpagedoc(frompage)
        outlinks = ["out"]
        for tp in types:
            try:
                l = outlinks[tp]
            except KeyError:
                continue
            while to in l:
                l.remove(to)
            if not l:
                del outlinks[tp]
        
        self.couch_db[frompd.id] = frompd
