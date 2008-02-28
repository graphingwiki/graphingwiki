# -*- coding: utf-8 -*-
"""
    DeletePage xmlrpc action for Graphingwiki
     - Delete pages with xmlrpc

    @copyright: 2008 by therauli <therauli@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import os
import xmlrpclib

from MoinMoin.PageEditor import PageEditor
from MoinMoin import config

def delete(request, pagename, comment = None):
    _ = request.getText
    # Using the same access controls as in MoinMoin's xmlrpc_putPage
    # as defined in MoinMoin/wikirpc.py
    if (request.cfg.xmlrpc_putpage_trusted_only and
        not request.user.trusted):
        return xmlrpclib.Fault(1, _("You are not allowed to delete this page"))
    
    # check ACLs
    if not request.user.may.delete(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to delete this page"))
    
    #Deletespages
    page = PageEditor(request, pagename, do_editor_backup=0)
    if comment:
        comment = unicode(comment, config.charset))
        
    page.deletePage(comment)

    return True

def execute(xmlrpcobj, pagename, comment = None):
    request = xmlrpcobj.request
    _ = request.getText

    pagename = xmlrpcobj._instr(pagename)

    success = delete(request, pagename, comment)


    # Save, delete return True on success
    if success is True:
        return xmlrpclib.Boolean(1)

    # Other results include the faults and the binary attachments
    return success
