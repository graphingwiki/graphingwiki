import itertools
import shelve
import os

from graphingwiki.backend.basedb import GraphDataBase
from graphingwiki.util import encode_page, decode_page, encode
from graphingwiki import actionname

from MoinMoin.util.lock import ReadLock, WriteLock

from time import time

from graphingwiki.util import node_type, SPECIAL_ATTRS, NO_TYPE

class GraphData(GraphDataBase):
    def __init__(self, request):
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
        self.writelock()
        page = encode_page(item)

        self.db[page] = value
        self.cache[page] = value

    def cacheset(self, item, value):
        page = encode_page(item)

        self.cache[page] = value

    def __delitem__(self, item):
        self.writelock()
        page = encode_page(item)

        del self.db[page]
        self.cache.pop(page, None)

    def keys(self):
        return map(decode_page, self.db.keys())

    def __iter__(self):
        return itertools.imap(decode_page, self.db)

    def __contains__(self, item):
        page = encode_page(item)
        return page in self.cache or page in self.db

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

    def add_link(self, new_data, pagename, nodename, linktype):
        edge = [pagename, nodename]

        self.add_in(new_data, edge, linktype)
        self.add_out(new_data, edge, linktype)

    
    def add_in(self, new_data, (frm, to), linktype):
        "Add in-links from current node to local nodes"
        if not linktype:
            linktype = NO_TYPE

        temp = new_data.get(to, {})

        if not temp.has_key(u'in'):
            temp[u'in'] = {linktype: [frm]}
        elif not temp[u'in'].has_key(linktype):
            temp[u'in'][linktype] = [frm]
        else:
            temp[u'in'][linktype].append(frm)

        # Notification that the destination has changed
        temp[u'mtime'] = time()

        new_data[to] = temp

    
    def add_out(self, new_data, (frm, to), linktype):
        "Add out-links from local nodes to current node"
        if not linktype:
            linktype = NO_TYPE

        temp = new_data.get(frm, {})

        if not temp.has_key(u'out'):
            temp[u'out'] = {linktype: [to]}
        elif not temp[u'out'].has_key(linktype):
            temp[u'out'][linktype] = [to]
        else:
            temp[u'out'][linktype].append(to)

        new_data[frm] = temp

    
    def remove_in(new_data, (frm, to), linktype):
        "Remove in-links from local nodes to current node"

        temp = new_data.get(to, {})
        if not temp.has_key(u'in'):
            return

        for type in linktype:
            # sys.stderr.write("Removing %s %s %s\n" % (frm, to, linktype))
            # eg. when the shelve is just started, it's empty
            if not temp[u'in'].has_key(type):
                # sys.stderr.write("No such type: %s\n" % type)
                continue
            if frm in temp[u'in'][type]:
                temp[u'in'][type].remove(frm)

                # Notification that the destination has changed
                temp[u'mtime'] = time()

            if not temp[u'in'][type]:
                del temp[u'in'][type]


        # sys.stderr.write("Hey man, I think I did it!\n")
        new_data[to] = temp

    def remove_out(new_data, (frm, to), linktype):
        "remove outlinks"
        temp = new_data.get(frm, {})

        if not temp.has_key(u'out'):
            return 

        for type in linktype:
            # print "Removing %s %s %s" % (frm, to, linktype)
            # eg. when the shelve is just started, it's empty
            if not temp[u'out'].has_key(type):
                # print "No such type: %s" % type
                continue
            if to in temp[u'out'][type]:
                i = temp[u'out'][type].index(to)
                del temp[u'out'][type][i]

                # print "removed %s" % (repr(to))

            if not temp[u'out'][type]:
                del temp[u'out'][type]
                # print "%s empty" % (type)
                # print "Hey man, I think I did it!"

        new_data[frm] = temp

