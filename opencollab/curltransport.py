#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id: xmlrpc_curl.py,v 1.13 2007/03/04 19:26:59 kjetilja Exp $

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
# the libcurl tutorial for more info.
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import xmlrpclib, pycurl

class CURLTransport(xmlrpclib.Transport):
    """Handles a cURL HTTP transaction to an XML-RPC server."""

    xmlrpc_h = [ "Content-Type: text/xml" ]
    HTTP = 0
    HTTPS = 1
    
    def __init__(self, scheme=HTTP):
        # Python 2.4 version of xmlrpclib.Transport of doesn't have
        # the __init__ method, whereas python 2.5 version does.
        if hasattr(xmlrpclib.Transport, "__init__"):
            xmlrpclib.Transport.__init__(self)

        if scheme == self.HTTP:
            self.scheme='http'
        else:
            self.scheme='https'
        self.c = pycurl.Curl()
        self.c.setopt(pycurl.POST, 1)
        self.c.setopt(pycurl.NOSIGNAL, 1)
        self.c.setopt(pycurl.CONNECTTIMEOUT, 30)
        self.c.setopt(pycurl.HTTPHEADER, self.xmlrpc_h)
        self._use_datetime = False

    def request(self, host, handler, request_body, verbose=0):
        b = StringIO()
        self.c.setopt(pycurl.URL, '%s://%s%s' % (self.scheme, host, handler))
        self.c.setopt(pycurl.POSTFIELDS, request_body)
        self.c.setopt(pycurl.WRITEFUNCTION, b.write)
        self.c.setopt(pycurl.VERBOSE, verbose)
        self.verbose = verbose
        try:
           self.c.perform()
        except pycurl.error, v:
            raise xmlrpclib.ProtocolError(
                host + handler,
                v[0], v[1], None
                )
        b.seek(0)
        return self.parse_response(b)


if __name__ == "__main__":
    ## Test
    server = xmlrpclib.ServerProxy("http://wiki.cabal.fi/?action=xmlrpc2",
                                   transport=CURLTransport())
    try:
        print server.GetMeta("FrontPage", False)
    except xmlrpclib.Error, v:
        print "ERROR", v
