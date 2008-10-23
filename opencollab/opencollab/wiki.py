# -*- coding: utf-8 -*-
"""
    @copyright: 2008 by Joachim Viide, Pekka Pietikäinen, Mika Seppänen  
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import urlparse
import xmlrpclib
import urllib
import socket
import httplib
import re
import md5
import sys
import random
import getpass
import ConfigParser

from meta import Meta

try:
    from curltransport import CURLTransport as CustomTransport
except ImportError:
    from transport import CustomTransport

class WikiFailure(Exception):
    pass

class AuthorizationRequired(WikiFailure):
    pass

class UrlRequired(WikiFailure):
    pass

DEFAULT_CHUNK = 256 * 1024

def urlQuote(string):
    if isinstance(string, unicode):
        string = string.encode("utf-8")
    return urllib.quote(string, "/:")
                               
def mangleFaultString(faultString):
    return faultString
    faultString = faultString.strip()
    faultLines = faultString.split("\n")
    if faultLines:
        faultString = faultLines[0]
    else:
        faultString = ""
    message = "There was an error in the wiki side (%s)" % faultString
    return message

class GraphingWiki(object):
    def __init__(self, url, username=None, password=None,
                 sslPeerVerify=False, config=None):
        object.__init__(self)

        self.sslPeerVerify = sslPeerVerify
        self._proxy = None

        if config is not None:
            self.loadConfig(config)

        if not hasattr(self, 'url'):
            self.setUrl(url)

        if not hasattr(self, 'username'):
            self.username = username

        if not hasattr(self, 'password'):
            self.password = password

    def setUrl(self, url):
        if not url:
            raise UrlRequired

        self.url = urlQuote(url)
        self._proxy = None

    def loadConfig(self, filenames, section="creds"):
        configparser = ConfigParser.ConfigParser()
        if not configparser.read(filenames):
            return False

        self._proxy = None

        try:
            self.username = configparser.get(section, "username")
            self.password = configparser.get(section, "password")
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            pass

        try:
            url = configparser.get(section, "url")
            self.setUrl(url)
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            pass
        except UrlRequired:
            pass

        return True

    def _getProxy(self):
        if self._proxy is not None:
            return self._proxy

        action = "action=xmlrpc2"
        scheme, netloc, path, _, _, _ = urlparse.urlparse(self.url)

        if scheme.lower() == "https":
            transport = CustomTransport(CustomTransport.HTTPS,
                                        sslPeerVerify=self.sslPeerVerify)
            if None not in (self.username, self.password):
                netloc = "%s:%s@%s" % (urlQuote(self.username), 
                                       urlQuote(self.password), 
                                       netloc)
        else:
            transport = CustomTransport(CustomTransport.HTTP)
        
        url = urlparse.urlunparse((scheme, netloc, path, "", action, ""))
        try:
            self._proxy = xmlrpclib.ServerProxy(url, transport, allow_none=True)
        except IOError, msg:
            raise WikiFailure(msg)

        return self._proxy

    def request(self, name, *args):
        proxy = self._getProxy()
        method = getattr(proxy, name)

        try:
            result = method(*args)
        except xmlrpclib.Fault, f:
            raise WikiFailure(mangleFaultString(f.faultString))
        except xmlrpclib.ProtocolError, e:
            if e.errcode == 401:
                raise AuthorizationRequired(e.errmsg)
            raise WikiFailure(e.errmsg)
        except (socket.gaierror, socket.error), (code, msg):
            raise WikiFailure(msg)
        except httplib.HTTPException, msg:
            raise WikiFailure(msg)

        if isinstance(result, dict) and "faultString" in result:
            faultString = result["faultString"]
            raise WikiFailure(faultString)

        return result

    def getPage(self, page):
        return self.request("getPage", page)

    def putPage(self, page, content):
        return self.request("putPage", page, content)

    def deletePage(self, page, comment=None):
        return self.request("DeletePage", page, comment)

    def putAttachment(self, page, filename, data, overwrite=False):
        data = xmlrpclib.Binary(data)
        return self.request("AttachFile", page, filename, 
                            "save", data, overwrite)

    def listAttachments(self, page):
        return self.request("AttachFile", page, "", "list", "", False)

    def getAttachment(self, page, filename):
        result = self.request("AttachFile", page, filename, "load", "", False)
        return str(result)

    def getAttachmentInfo(self, page, filename):
        return self.request("ChunkedAttachFile", page, filename, "info")

    def putAttachmentChunked(self, page, filename, seekableStream, 
                             chunksPerCheck=10, chunkSize=DEFAULT_CHUNK):
        count = 0
        total = 0
        digests = list()
        offsets = dict()
        
        while True:
            data = seekableStream.read(chunkSize)
            if not data:
                break

            digest = md5.new(data).hexdigest()
            digests.append(digest)

            length = len(data)
            offsets[digest] = total, length
            total += length

        while True:
            missing = self.request("ChunkedAttachFile", page, filename, 
                                   "reassembly", chunkSize, digests)
            if not missing:
                return

            done = total
            for digest in missing:
                offset, length = offsets[digest]
                done -= length

            yield done, total

            missing = random.sample(missing, min(len(missing), chunksPerCheck))
            for digest in missing:
                offset, length = offsets[digest]
                
                seekableStream.seek(offset)
                data = seekableStream.read(length)

                self.putAttachment(page, digest, data, overwrite=True)

                count += 1
                done += length
                yield done, total
                    
    def getAttachmentChunked(self, page, filename, chunkSize=DEFAULT_CHUNK):
        digest, size = self.getAttachmentInfo(page, filename)

        dataDigest = md5.new()
        current = 0

        while True:
            data = self.request("ChunkedAttachFile", page, filename, "load", 
                                current, current+chunkSize)
            data = str(data)
            if not data:
                break

            current += len(data)
            yield data, current, size

            dataDigest.update(data)
            if current > size:
                break

        if current != size:
            raise WikiFailure("data changed while reading")

        dataDigest = dataDigest.hexdigest()
        if dataDigest != digest:
            raise WikiFailure("data changed while reading")

    def getMeta(self, value):
        keysOnly = False
        results = self.request("GetMeta", value, keysOnly)

        keys = results.pop(0)
        pages = dict()

        for result in results:
            # Page names and meta keys seem to come from the wiki
            # UTF-8 encoded in contrast to the actual key values
            page = result.pop(0)
            meta = Meta()

            for key, values in zip(keys, result):
                if not values:
                    continue
                meta[key].update(values)

            pages[page] = meta

        return pages

    def setMeta(self, page, meta, replace=False, template=""):
        if replace:
            metaMode, categoryMode = "repl", "set"
        else:
            metaMode, categoryMode = "add", "add"

        keys = dict()
        for key, values in meta.iteritems():
            keys[key] = list(values)

        categories = keys.pop("category", list())
        createPageOnDemand = True

        return self.request("SetMeta", page, keys, metaMode,
                            createPageOnDemand, categoryMode, categories,
                            template)

class CLIWiki(GraphingWiki):
    # A version of the GraphingWiki class intended for command line
    # usage. Automatically asks username and password should the wiki
    # need it.

    def __init__(self, name='', *args, **kw):
        while True:
            try:
                super(CLIWiki, self).__init__(name, *args, **kw)
            except UrlRequired:
                # Redirecting stdout to stderr for these queries
                oldStdout = sys.stdout
                sys.stdout = sys.stderr

                name = raw_input("Wiki:")

                sys.stdout = oldStdout
            else:
                return

    def request(self, name, *args):
        while True:
            try:
                result = GraphingWiki.request(self, name, *args)
            except AuthorizationRequired:
                # Redirecting stdout to stderr for these queries
                oldStdout = sys.stdout
                sys.stdout = sys.stderr

                if not getattr(self, 'username', ''):
                  self.username = raw_input("Username:")
                self.password = getpass.getpass("Password:")
                self._proxy = None

                sys.stdout = oldStdout
            else:
                return result