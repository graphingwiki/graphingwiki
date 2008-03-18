# -*- coding: utf-8 -*-
"""
    @copyright: 2008 by Joachim Viide, Pekka Pietikäinen, Mika Seppänen  
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Based on a pycurl example obtained from http://pycurl.sourceforge.net/,
    which is LGPLv2.1+.
 """
# vi:ts=4:et
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
   
    def __init__(self, scheme=HTTP, sslPeerVerify=False):
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
        if scheme == self.HTTPS:
            self.c.setopt(pycurl.SSL_VERIFYPEER, sslPeerVerify)
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
            raise xmlrpclib.ProtocolError(host + handler, v[0], v[1], None)

        if self.c.getinfo(pycurl.HTTP_CODE) != 200:
            raise xmlrpclib.ProtocolError(
                host + handler,
                self.c.getinfo(pycurl.HTTP_CODE), "Error", None
                )
        b.seek(0)
        return self.parse_response(b)
