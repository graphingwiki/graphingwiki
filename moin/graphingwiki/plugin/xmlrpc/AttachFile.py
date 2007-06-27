# -*- coding: utf-8 -*-
"""
    AttachFile xmlrpc action for Graphingwiki
     - Attach files with xmlrpc

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import os
import xmlrpclib

from tempfile import mkdtemp
from shutil import rmtree

from graphingwiki.editing import save_attachfile

def execute(xmlrpcobj, pagename, filename, content):
    request = xmlrpcobj.request

    # Using the same access controls as in MoinMoin's xmlrpc_putPage
    # as defined in MoinMoin/wikirpc.py
    if (request.cfg.xmlrpc_putpage_trusted_only and
        not request.user.trusted):
        return xmlrpclib.Fault(1, "You are not allowed to attach a file to this page %s %s %s" % (request.user.name, request.user.valid, request.user.trusted))

    # also check ACLs
    if not request.user.may.write(pagename):
        return xmlrpclib.Fault(1, "You are not allowed to attach a file to this page")

    pagename = xmlrpcobj._instr(pagename)
    # Create a temp file where to decode the data
    path = mkdtemp()
    try:
        tmp = os.path.join(path, filename)
        tmpf = file(tmp, 'wb')
        tmpf.write(content.data)
        tmpf.close()
    except:
        return xmlrpclib.Fault(2, "Unknown error in passed data")

    # Attach the decoded file
    success = save_attachfile(request, pagename, tmp, filename)
    
    rmtree(path)

    if success:
        return xmlrpclib.Boolean(1)
    else:
        return xmlrpclib.Fault(3, "Unknown error in attaching file")
