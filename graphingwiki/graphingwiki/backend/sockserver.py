import asyncore, asynchat, socket, json, collections, os, logging, pprint, errno

log = logging.getLogger("graphingwiki.backend.socketserver")

# configure default logger as advised in logger docs
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


class GraphChat(asynchat.async_chat):
    # asynchat interface
    def __init__(self, sock, db):
        asynchat.async_chat.__init__(self, sock)
        self.db = db
        self.outbuf = []
        self.inbuf = []
        self.set_terminator("\r\n")

    def collect_incoming_data(self, data):
        log.debug("incoming data")
        self.inbuf.append(data)

    def handle_close(self):
        log.debug("closing")
        self.close()

    def found_terminator(self):
        log.debug("found terminator")
        json_str = ''.join(self.inbuf)
        #log.debug('<-- ' + json_str.rstrip())
        try:
            req = json.loads(json_str)
        except ValueError, what:
            log.error("json error: %s" % what)
            return

        self.inbuf = []
        try:
            response = self.handle_request(req)
        except:
            import traceback
            for line in traceback.format_exc().split('\n'):
                log.error(line)
            response = {'status': 'internal error'}
        response_json = json.dumps(response)
        self.push(response_json)
        log.debug('--> ' + response_json)
        self.push("\r\n")

    # /asynchat interface

    def handle_request(self, opdict):
        log.debug("do req")

        def errmsg(s):
            log.error(s)
            return dict(status=s)
        
        try:
            op = opdict["op"]
        except KeyError:
            return errmsg("bad request, missing op: %s" % repr(opdict))

        del opdict["op"]
        try:
            fun = getattr(self.db, op)
        except AttributeError:
            return errmsg("bad request, no such op: %s" % op)
            
        try:
            return apply(fun, (), opdict)
        except TypeError, what:
            return errmsg("bad arguments: %s" % what)
            
    def send(self, data):
        try:
            return asynchat.async_chat.send(self, data)
        except socket.error, what:
            if what.errno == errno.EPIPE:
                self.handle_close()
            else:
                raise

class MockDB:
    def __init__(self):
        self.dbdict = dict()
        self.stack = [] # for transactions
        self.in_tx = False

    def getitem(self, name):
        try:
            return {'value': self.dbdict[name], 'name': name, 'status': 'ok'}
        except KeyError:
            return {'status': 'not-found', 'name': name}
        else:
            return {'status': sts, 'name': name}
            

    def setitem(self, name, value):
        self.dbdict.__setitem__(name, value)
        return {'status': 'ok'}

    def keys(self):
        return {'keys': self.dbdict.keys()}

    def contains(self, name):
        return {'result': self.dbdict.__contains__(name)}

    def delitem(self, name):
        try:
            del self.dbdict[name]
        except KeyError:
            sts = 'not-found'
        else:
            sts = 'ok'
        return {'status': sts, 'name': name}

    # below is a toy transaction scheme that could work if there was only one concurrent connection

    def begin(self):
        if self.stack:
            # could support nested transactions by just removing this check
            return {'status': 'transaction already in progress'}
        else:
            self.stack.append(self.dbdict)
            self.dbdict = self.dbdict.copy()
            return {'status': 'ok'}
    
    def commit(self):
        try:
            self.stack.pop()
        except IndexError:
            return {'status': 'transaction stack empty'}
        else:
            return {'status': 'ok'}

    def abort(self):
        try:
            self.dbdict = self.stack.pop()
        except IndexError:
            return {'status': 'transaction stack empty'}
        else:
            return {'status': 'ok'}

class SqiteDB:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)

class GraphServer(asyncore.dispatcher):
    def __init__(self, sockpath, db):
        asyncore.dispatcher.__init__(self)
        self.sockpath = sockpath
        self.db = db
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if os.path.exists(self.sockpath) and not os.path.isfile(self.sockpath):
            log.debug("unlinking old socket")
            os.unlink(self.sockpath)
        self.bind(self.sockpath)
        self.listen(5)
        log.debug("listening on " + self.sockpath)

    def handle_accept(self):
        sock, addr = self.accept()
        GraphChat(sock, self.db)

    def writable(self):
        return False

if __name__ == '__main__':
    #logging.basicConfig(level=logging.DEBUG, format="%(asctime)-15s %(levelname)-5s %(message)s")
    import sys
    s = GraphServer(sys.argv[1], MockDB())
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        log.info("break")
