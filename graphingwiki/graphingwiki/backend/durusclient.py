import os
from collections import defaultdict

import durus.client_storage, durus.connection
from durus.persistent_dict import PersistentDict
from durus.persistent_list import PersistentList
from durus.btree import BTree as DurusBTree
from durus.persistent import Persistent

from graphingwiki.util import log


class PageMeta(Persistent):
    def __init__(self):
        self.outlinks = Metas()
        self.unlinks = Metas()
        self.mtime = 0
        self.saved = True
        self.acl = u''

    def asdict(self):
        return {u'meta': self.unlinks.asdict(), u'out': self.outlinks.asdict()}

class Metas(PersistentDict):
    def add(self, typ, val):
        try:
            l = self[typ]
        except KeyError:
            l = self[typ] = PersistentList()
        l.append(val)

    def asdict(self):
        return dict([(k, list(v)) for (k, v) in self.items()])

    # xxx remove
    def set_single(self, typ, val):
        self[typ] = PersistentList([val])
        
    def get_single(self, typ, val, default=None):
        val = self[typ]
        if len(val) > 1:
            raise ValueError, typ, 'has multiple values'
        return val[0]

class GraphData:
    # durus has working transactions
    is_acid = True

    # enable users to access this using dict protocol (deprecated)?
    use_dict_api = False

    def __init__(self, request=None, address=None, **kw):
        if not address:
            address=os.path.join(request.cfg.data_dir, 'durus.sock')
        self.request = request
        self.durus_storage = durus.client_storage.ClientStorage(address=address)
        self.durus_conn = durus.connection.Connection(self.durus_storage)
        self.dbroot = self.durus_conn.get_root()
        self.init_db()

    def init_db(self):
        indices = 'metasbyname', 'pagename_by_metakey', 'pagename_by_metaval', 'pagename_by_regexp'
        for i in indices:
            if i not in self.dbroot:
                self.dbroot[i] = DurusBTree()
            t = self.dbroot[i]
            setattr(self, i, t)

    def clear_metas(self):
        self.dbroot.clear()
        self.init_db()

    def getpage(self, pagename):
        return self.metasbyname.setdefault(pagename, PageMeta())

    def get_out(self, pagename):
        return self.getpage(pagename).outlinks

    def get_in(self, pagename):
        "return mapping of metakey -> [frompage1, frompage2, ...]"
        inlinks = {}
        for pname in self.pagename_by_metaval.get(pagename, []):
            for k, vals in self.get_out(pname).iteritems():
                if pagename in vals:
                    inlinks.setdefault(k, []).append(pname)
        return inlinks


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

    def pagenames(self):
        return self.metasbyname.iterkeys()

    def __contains__(self, item):
        if not self.use_dict_api:
            raise NotImplementedError()
        return item in self.metasbyname

    def is_saved(self, pagename):
        return self.getpage(pagename).saved

    def get_metakeys(self, name):
        """
        Return the complete set of page's (non-link) meta keys, plus gwiki category.
        """

        page = self.getpage(name)
        keys = set(page.unlinks)
        if 'gwikicategory' in page.outlinks:
            keys.add('gwikicategory')
        return keys

    def get_meta(self, pagename):
        return self.getpage(pagename).unlinks

    def get_out(self, pagename):
        return self.getpage(pagename).outlinks

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
        #log.info("remove_out %s %s" % (frm, to))
        outlinks = self.getpage(frm).outlinks
        for tp in types:
            if tp not in outlinks or to not in outlinks[tp]:
                continue
            outlinks[tp].remove(to)
            if not outlinks[tp]:
                del outlinks[tp]

    def remove_in(self, (fromname, toname), types):
        pass

    def add_in(self, (frm, to), linktype):
        pass

    def add_out(self, (frompage, topage), linktype):
        self.getpage(frompage).outlinks.add(linktype, topage)
        #log.info("%s outlinks %s" % (frompage, self.metasbyname[frompage].outlinks.items()))
        
    def dump_db(self):
        log.debug("db dump:")
        log.debug(dict(self.dbroot.items()))

    def post_save(self, pagename):
        self.index_pagename(pagename)

    def get_vals_on_keys(self):
        "mapping of { metakey1: set(metaval1, metaval2, ...), ... }"
        out = defaultdict(set)
        for pm in self.metasbyname.itervalues():
            for mkey, mvals in pm.unlinks.iteritems():
                out[mkey].update(mvals)
        return out
                
    def index_pagename(self, pagename):
        pm = self.getpage(pagename)
        ol, ul = pm.outlinks, pm.unlinks

        # set-ify to eliminate dups
        for metakey in set(pm.outlinks.keys() + pm.unlinks.keys()):
            pl = self.pagename_by_metakey.setdefault(metakey, PersistentList())

            # add page name to metakey index
            if pagename not in pl:
                pl.append(pagename)

            # add page to metaval index
            for val in set(ol.get(metakey, []) + ul.get(metakey, [])):
                self.pagename_by_metaval.setdefault(
                    val, PersistentList()).append(pagename)

    def clear_page(self, pagename):
        pm = self.getpage(pagename)
        ol, ul = pm.outlinks, pm.unlinks
        for metakey in ol.keys() + ul.keys():
            self.pagename_by_metakey.get(metakey, []).remove(pagename)

            for val in ol.get(metakey, []) + ul.get(metakey, []):
                self.pagename_by_metaval[val].remove(pagename)


