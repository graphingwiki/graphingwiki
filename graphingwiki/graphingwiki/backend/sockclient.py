import itertools
import os
from time import time

from graphingwiki.backend.basedb import GraphDataBase
from graphingwiki.util import encode_page, decode_page, encode
from graphingwiki import actionname

from MoinMoin.util.lock import ReadLock, WriteLock

from graphingwiki.util import node_type, SPECIAL_ATTRS, NO_TYPE

from socket import socket, AF_UNIX, SOCK_STREAM, SHUT_RDWR, error as SocketError

from select import select, error as SelectError
import json

class SockClientError(Exception):
    pass

class ProtocolError(SockClientError):
    pass

class CommitError(SockClientError):
    pass

class GraphData(GraphDataBase):
    def __init__(self, request):
        GraphDataBase.__init__(self, request)

        self.sock_path = os.path.join(request.cfg.data_dir, 'graphserver.sock')
        self.sock = socket(AF_UNIX, SOCK_STREAM)
        self.sock.connect(self.sock_path)
        if 1:
            self.conn_file = self.sock.makefile("r+")
        else:
            self.conn_file = os.fdopen(os.dup(self.sock), "r+", 1)

    def make_req(self, opdict):
        f = self.conn_file
        j = json.dumps(opdict)
        f.write(j)
        f.write("\r\n")
        f.flush()
        resp_str = f.readline()
        return json.loads(resp_str)

    def __getitem__(self, item):
        resp = self.make_req({'op': 'getitem', 'name': item})
        try:
            return resp["value"]
        except KeyError:
            if resp.get("status") == "not-found":
                raise KeyError(item)
            else:
                raise ProtocolError("getitem request got response %s" % repr(resp))

    def __setitem__(self, item, value):
        resp = self.make_req({'op': 'setitem', 'name': item, 'value': value})

    def __delitem__(self, item):
        resp = self.make_req({'op': 'delitem', 'name': item})
        sts = resp.get("status") 
        if sts == "not-found":
            raise KeyError(item)
        elif sts == "ok":
            return
        else:
            raise ProtocolError("delitem request got response %s" % repr(resp))

    def keys(self):
        resp = self.make_req({'op': 'keys'})
        try:
            return resp["keys"]
        except KeyError:
            raise ProtocolError("keys request got response %s" % repr(resp))

    def __iter__(self):
        return self.keys()

    def __contains__(self, item):
        resp = self.make_req({'op': 'contains', 'name': item})
        try:
            return resp["result"]
        except KeyError:
            raise ProtocolError("contains request got response %s" % repr(resp))

    def commit(self):
        resp = self.make_req({'op': 'commit'})
        try:
            result = resp["status"]
        except KeyError:
            raise ProtocolError("commit request got response %s" % repr(resp))
        
        if result == "ok":
            return
        else:
            raise CommitError(result)

    def close(self):
        self.conn_file.close()
        self.sock.shutdown(SHUT_RDWR) #  work around bug in some 2.5 era pythons
        self.sock.close()

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

import cPickle
class PicklingGraphData(GraphData):
    def make_req(self, opdict):
        f = self.conn_file
        j = cPickle.dump(opdict, f, -1)
        return cPickle.load(f)
