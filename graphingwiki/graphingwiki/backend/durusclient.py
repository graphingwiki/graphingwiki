import itertools
import os
from time import time

from graphingwiki.backend.basedb import GraphDataBase
from graphingwiki.util import encode_page, decode_page, encode
from graphingwiki import actionname

from graphingwiki.util import node_type, SPECIAL_ATTRS, NO_TYPE, log

import durus.client_storage, durus.connection
from durus.persistent_dict import PersistentDict
from durus.persistent_list import PersistentList
from durus.btree import BTree as DurusBTree
from durus.persistent import Persistent

class PageMeta(Persistent):
    def __init__(self):
        self.outlinks = Metas()
        self.unlinks = Metas()
        self.mtime = 0
        self.saved = True
        self.acl = u''

    def asdict(self):
        return {u'meta': self.unlinks.asdict(), u'out': self.outlinks.asdict()}

    def get(self, what, default=None):
        if what == 'out':
            return self.outlinks
        else:
            raise ValueError(what)

class Metas(PersistentDict):
    def add(self, typ, val):
        try:
            l = self[typ]
        except KeyError:
            l = self[typ] = PersistentList()
        l.append(val)

    def asdict(self):
        return dict([(k, list(v)) for (k, v) in self.items()])

    def set_single(self, typ, val):
        self[typ] = PersistentList([val])
        
    def get_single(self, typ, val, default=None):
        val = self[typ]
        if len(val) > 1:
            raise ValueError, typ, 'has multiple values'
        return val[0]

class GraphData:
    use_dict_api = False

    def __init__(self, request):
        self.durus_storage = durus.client_storage.ClientStorage(address=os.path.join(request.cfg.data_dir, 'durus.sock'))
        self.durus_conn = durus.connection.Connection(self.durus_storage)
        self.dbroot = self.durus_conn.get_root()
        self.request = request

        indices = 'metasbyname', 'pagename_by_metakey', 'pagename_by_metaval', 'pagename_by_regexp'
        for i in indices:
            if i not in self.dbroot:
                self.dbroot[i] = DurusBTree()
            t = self.dbroot[i]
            setattr(self, i, t)

    def getpage(self, pagename):
        return self.metasbyname.setdefault(pagename, PageMeta())

    def get_out(self, pagename):
        return self.getpage(pagename).outlinks

    def __getitem__(self, item):
        if not self.use_dict_api:
            raise NotImplementedError()
        return self.metasbyname[item]

    def __setitem__(self, item, value):
        if not self.use_dict_api:
            raise NotImplementedError()

        if not isinstance(value, PageMeta):
            value = PageMeta.fromdict(value)

        self.metasbyname[item] = value

    def delpage(self, pagename):
        del self.metasbyname[pagename]

    def __delitem__(self, item):
        if not self.use_dict_api:
            raise NotImplementedError()
        
        self.delpage(item)

    def keys(self):
        if not self.use_dict_api:
            raise NotImplementedError()

        return self.metasbyname.keys()

    def __iter__(self):
        if not self.use_dict_api:
            raise NotImplementedError()
        return self.keys()

    def __contains__(self, item):
        if not self.use_dict_api:
            raise NotImplementedError()
        return item in self.metasbyname

    def commit(self):
        log.info("commit")
        self.durus_conn.commit()

    def close(self):
        self.durus_storage.close()

    def abort(self):
        log.info("abort")
        self.durus_conn.abort()

    # implement savegraphdata-ish api

    def set_page_meta_and_acl_and_mtime_and_saved(self, pagename, newmeta, acl, mtime, saved):
        p = self.getpage(pagename)
        p.unlinks.update(newmeta)
        p.acl = acl
        p.mtime = mtime
        p.saved = saved

    def remove_out(self, (frm, to), types):
        assert self is ignored
        log.info("remove_out %s %s" % (fromname, toname))
        outlinks = self.getpage(fromname).outlinks
        for tp in types:
            if tp not in outlinks or toname not in outlinks[tp]:
                continue
            outlinks[tp].remove(toname)
            if not outlinks[tp]:
                del outlinks[tp]
    
    def remove_in(self, (fromname, toname), types):
        pass

    def add_in(self, (frm, to), linktype):
        pass

    def add_out(self, (frompage, topage), linktype):
        self.getpage(frompage).outlinks.add(linktype, topage)
        log.info("%s outlinks %s" % (frompage, self.metasbyname[frompage].outlinks.items()))
        
    def dump_db(self):
        from pprint import pformat
        log.debug("db dump:")
        log.debug(dict(self.dbroot.items()))
