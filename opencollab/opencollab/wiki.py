# -*- coding: utf-8 -*-
"""
    @copyright: 2008 by Joachim Viide, Pekka Pietikäinen, Mika Seppänen  
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import urlparse
import xmlrpclib
import urllib
import httplib
import base64
import re
from encodings import idna

class WikiFailure(Exception): pass
class AuthenticationFailed(WikiFailure): pass
class WikiAuthenticationFailed(AuthenticationFailed): pass
class HttpAuthenticationFailed(AuthenticationFailed): pass

class WikiFault(WikiFailure):
    def __init__(self, fault):
        message = "There was an error in the wiki side"

        lines = fault.faultString.splitlines()
        if lines:
            message += " (%s)" % lines[0]

        WikiFailure.__init__(self, message)
        self.fault = fault

class Wiki(object):
    WHOAMI_FORMAT = re.compile("^You are .*\. valid=(.+?)[\,\.]$", re.I)

    def __init__(self, url):
        scheme, host, path, _, _, _ = urlparse.urlparse(url)
        if isinstance(host, unicode):
            host = idna.ToASCII(host)
        if isinstance(path, unicode):
            path = urllib.quote(path.encode("utf-8"))

        self.host = idna.ToASCII(host)
        self.path = path + "?action=xmlrpc2"

        self.headers = dict(Connection="Keep-Alive")
        self.token = None

        if scheme.strip().lower() == "http":
            self.connection = httplib.HTTPConnection(self.host)
        else:
            self.connection = httplib.HTTPSConnection(self.host)
        self.connection.connect()
        
    def _wiki_auth(self, username, password):
        self.token = None
        token = self._request("getAuthToken", username, password)
        if not token:
            raise WikiAuthenticationFailed("wiki authentication failed")
        self.token = token, username, password
    
    def _authenticate(self, username, password):
        self.headers.pop("Authorization", None)
        self.token = None

        try:
            try:
                whoami = self._request("WhoAmI")
            except HttpAuthenticationFailed:
                auth = base64.b64encode(username + ":" + password)
                self.headers["Authorization"] = "Basic " + auth
                whoami = self._request("WhoAmI")
                
            match = self.WHOAMI_FORMAT.match(whoami)
            if match is None:
                raise WikiFailure("WhoAmI action returned invalid data")

            valid = match.group(1)
            if valid == "0":
                self._wiki_auth(username, password)
        except:
            self.headers.pop("Authorization", None)
            self.token = None
            raise

    def _dumps(self, name, args):
        if self.token is None:
            return xmlrpclib.dumps(args, name, allow_none=True)

        token, _, _ = self.token

        mc_list = list()
        mc_list.append(dict(methodName="applyAuthToken", params=(token,)))
        mc_list.append(dict(methodName=name, params=args))
        return xmlrpclib.dumps((mc_list,), "system.multicall", allow_none=True)

    def _loads(self, data):
        result, _ = xmlrpclib.loads(data)
        if self.token is None:
            return result[0]

        auth, other = result[0]
        if (not isinstance(auth, (dict, list)) or 
            not isinstance(other, (dict, list))):
            WikiFailure("unexpected type in multicall result")            

        if isinstance(auth, dict):
            code = auth.get("faultCode", None)
            string = auth.get("faultString", "<unknown fault>")
            if code == "INVALID":
                raise WikiAuthenticationFailed(string)
            raise xmlrpclib.Fault(code, string)
        
        if isinstance(other, dict):
            raise xmlrpclib.Fault(other["faultCode"], other["faultString"])
        return other[0]
            
    def _request(self, name, *args):
        body = self._dumps(name, args)
        self.connection.request("POST", self.path, body, self.headers)

        try:
            response = self.connection.getresponse()
        except httplib.BadStatusLine:
            self.connection.close()
            self.connection.connect()
            self.connection.request("POST", self.path, body, self.headers)
            response = self.connection.getresponse()

        data = response.read()
        if response.status == 401:
            raise HttpAuthenticationFailed(response.reason)
        elif response.status != 200:
            raise WikiFailure(response.reason)

        return self._loads(data)

    def request(self, name, *args):
        try:
            try:
                return self._request(name, *args)
            except WikiAuthenticationFailed:
                _, username, password = self.token
                self._wiki_auth(username, password)
                return self._request(name, *args)
        except xmlrpclib.Fault, fault:            
            raise WikiFault(fault)

    def authenticate(self, username, password):
        try:
            self._authenticate(username, password)
        except AuthenticationFailed:
            return False
        return True    

import re
import md5
import sys
import random
import getpass

from meta import Meta 

class GraphingWiki(Wiki):
    DEFAULT_CHUNK = 256 * 1024

    def getPage(self, page):
        return self.request("getPage", page)

    def getPageHTML(self, page):
        return self.request("getPageHTML", page)

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

        # If no categories specified, do not set categories to empty
        if not 'category' in keys:
            categoryMode = 'add'

        categories = keys.pop("category", list())
        createPageOnDemand = True

        return self.request("SetMeta", page, keys, metaMode,
                            createPageOnDemand, categoryMode, categories,
                            template)

def redirected(func, *args, **keys):
    oldStdout = sys.stdout
    sys.stdout = sys.stderr

    try:
        return func(*args, **keys)
    finally:
        sys.stdout = oldStdout

class CLIWiki(GraphingWiki):
    # A version of the GraphingWiki class intended for command line
    # usage. Automatically asks url, username and password should the
    # wiki need it.

    def __init__(self, url=None, username=None, password=None, **keys):

        if url is None: 
            url = redirected(raw_input, "Collab URL: ")
        super(CLIWiki, self).__init__(url, **keys)
        creds = username, password
        self.authenticate(*creds)

    def authenticate(self, username=None, password=None):
        if username is None:
            username = redirected(raw_input, "Username: ")
        if password is None:
            password = redirected(getpass.getpass, "Password: ")
        return super(CLIWiki, self).authenticate(username, password)

    def request(self, name, *args):
        while True:
            try:
                return super(CLIWiki, self).request(name, *args)
            except AuthenticationFailed, f:
                while True:
                    print >> sys.stderr, "Authorization required."
                    if self.authenticate():
                        break
