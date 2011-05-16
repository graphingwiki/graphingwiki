import os
import shutil
import socket
import httplib
import tempfile

# A cert to make the ssl.wrap_socket to use the system CAs.
WRAP_CERT = """
-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----
"""

try:
    # Try to use the new ssl module included by default from Python
    # 2.6 onwards.
    import ssl
except ImportError:
    class HTTPSConnection(httplib.HTTPSConnection):
        def __init__(self, *args, **keys):
            if keys.pop("verify_cert", True):
                raise socket.sslerror("module 'ssl' required for "+
                                      "certificate verification")
            keys.pop("ca_certs", None)

            httplib.HTTPSConnection.__init__(self, *args, **keys)
else:
    def wrap_socket(sock, verify_cert, ca_certs):
        if not verify_cert:
            return ssl.wrap_socket(sock)

        if ca_certs is not None:
            return ssl.wrap_socket(sock, 
                                   cert_reqs=ssl.CERT_REQUIRED,
                                   ca_certs=ca_certs)

        tempdir = tempfile.mkdtemp()
        try:
            filename = os.path.join(tempdir, "cert")
            temp = open(filename, "w+b")
            try:
                temp.write(WRAP_CERT)
            finally:
                temp.close()

            return ssl.wrap_socket(sock,
                                   cert_reqs=ssl.CERT_REQUIRED,
                                   ca_certs=filename)
        finally:
            shutil.rmtree(tempdir)

    class HTTPSConnection(httplib.HTTPSConnection):
        def __init__(self, *args, **keys):
            self.verify_cert = keys.pop("verify_cert", False)
            self.ca_certs = keys.pop("ca_certs", None)
            
            httplib.HTTPSConnection.__init__(self, *args, **keys)

        def connect(self):
            for info in socket.getaddrinfo(self.host, self.port, 
                                           0, socket.SOCK_STREAM):
                family, type, proto, _, addr = info
                
                plain = socket.socket(family, type, proto)
                plain.connect(addr)
            
                self.sock = wrap_socket(plain,
                                        verify_cert=self.verify_cert,
                                        ca_certs=self.ca_certs)
                return
