# -*- coding: utf-8 -*-
"""
    @copyright: 2008 by Joachim Viide, Pekka Pietikäinen, Mika Seppänen  
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import xmlrpclib
import httplib

class CustomTransport(xmlrpclib.Transport):
    # A custom transport class that tries to keep the connection alive
    # over several requests.

    HTTP = 0
    HTTPS = 1

    def __init__(self, scheme=HTTP, sslPeerVerify=False):
        if sslPeerVerify:
            error = "%s can not do SSL peer verification" % self.__class__
            raise ValueError, error

        # Python 2.4 version of xmlrpclib.Transport of doesn't have
        # the __init__ method, whereas python 2.5 version does.
        if hasattr(xmlrpclib.Transport, "__init__"):
            xmlrpclib.Transport.__init__(self)
        self.scheme = scheme
        self.connection = None
    
    def request(self, *args, **keys):
        try:
            result = self._request(*args, **keys)
        except httplib.BadStatusLine:
            self.connection.close()
            self.connection = None

            result = self._request(*args, **keys)

        return result

    def _request(self, host, handler, request_body, verbose=0):
        # Issue XML-RPC request
        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        self.send_request(h, handler, request_body)
        self.send_host(h, host)
        self.send_user_agent(h)
        self.send_content(h, request_body)

        response = h.getresponse()

        if response.status != 200:
            raise xmlrpclib.ProtocolError(
                host + handler,
                response.status, response.reason, response.getheaders()
                )

        self.verbose = verbose

        return self.parse_response(response)

    def make_connection(self, host):
        if self.connection is None:
            host, extra_headers, x509 = self.get_host_info(host)
            if self.scheme == self.HTTP:
                self.connection = httplib.HTTPConnection(host)
            else:
                if not x509:
                    x509 = dict()
                self.connection = httplib.HTTPSConnection(host, None, **x509)
        return self.connection
