# -*- coding: utf-8 -*-
"""
    AttachFile xmlrpc action for Graphingwiki
     - Attach files with xmlrpc

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import os
import xmlrpclib

from tempfile import mkdtemp, mkstemp
from shutil import rmtree

import traceback

from graphingwiki.editing import save_attachfile
from graphingwiki.editing import load_attachfile
from graphingwiki.editing import delete_attachfile
from graphingwiki.editing import list_attachments

def list(request, pagename):
    _ = request.getText
    # check ACLs
    if not request.user.may.read(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to access this page"))

    # Grab the attachment
    result = list_attachments(request, pagename)

    return result

def load(request, pagename, filename):
    _ = request.getText
    # check ACLs
    if not request.user.may.read(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to access this page"))

    # Grab the attachment
    result = load_attachfile(request, pagename, filename)

    if not result:
        return xmlrpclib.Fault(2, "%s: %s" % (_("Nonexisting attachment"),
                                              filename))

    return xmlrpclib.Binary(result)

def delete(request, pagename, filename):
    _ = request.getText

    # check ACLs
    if not request.user.may.delete(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to delete a file on this page"))

    # Delete the attachment
    result = delete_attachfile(request, pagename, filename)

    if not result:
        return xmlrpclib.Fault(2, "%s: %s" % (_("Nonexisting attachment"),
                                              filename))

    return True

def save(request, pagename, filename, content, overwrite):
    _ = request.getText

    # also check ACLs
    if not request.user.may.write(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to attach a file to this page"))

    # Create a temp file where to decode the data
    path = mkdtemp()
    try:
        tmpfd, tmp = mkstemp(dir = path)
        os.write(tmpfd, content)
        os.close(tmpfd)
    except Exception, e:
        desc = "Unknown error"
        #there has been some problems with xmlrpclib and str() .. so this try: ... is for em
        try:
            desc = traceback.format_exc()
        except:
            pass
        return xmlrpclib.Fault(3, _(desc))

    # Attach the decoded file
    success = save_attachfile(request, pagename, tmp, filename, overwrite)
    
    rmtree(path)

    if success is True:
        return success
    elif overwrite == False:
        return xmlrpclib.Fault(2, _("Attachment not saved, file exists"))

    return xmlrpclib.Fault(3, _("Unknown error while attaching file"))

def execute(xmlrpcobj, pagename, filename, action='save',
            content=None, overwrite=False):
    request = xmlrpcobj.request
    _ = request.getText

    pagename = xmlrpcobj._instr(pagename)

    if action == 'list':
        success = list(request, pagename)
    elif action == 'load':
        success = load(request, pagename, filename)
    elif action == 'delete':
        success = delete(request, pagename, filename)
    elif action == 'save' and content:
        success = save(request, pagename, filename, content.data, overwrite)
    else:
        success = xmlrpclib.Fault(3, _("No method specified or empty data"))

    # Save, delete return True on success
    if success is True:
        return xmlrpclib.Boolean(1)

    # Other results include the faults and the binary attachments
    return success