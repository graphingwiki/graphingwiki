# -*- coding: utf-8 -*-
"""
    DeletePage xmlrpc action for Graphingwiki
     - Delete pages with xmlrpc

    @copyright: 2008 by therauli <therauli@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import xmlrpclib

from MoinMoin.PageEditor import PageEditor

def delete(request, pagename, comment = None):
    _ = request.getText
    
    # check ACLs
    if not request.user.may.delete(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to delete this page"))
    
    # Deletes pages

    page = PageEditor(request, pagename, do_editor_backup=0)
    if not page.exists():
        return xmlrpclib.Fault(1, _('No such page %s' % pagename))

    page.deletePage(comment)

    return True

def execute(xmlrpcobj, pagename, comment = None):
    request = xmlrpcobj.request
    _ = request.getText

    pagename = xmlrpcobj._instr(pagename)

    if comment:
        comment = xmlrpcobj._instr(comment)
    else:
        comment = u''

    success = delete(request, pagename, comment)

    # Save, delete return True on success
    if success is True:
        return xmlrpclib.Boolean(1)

    # Other results include the faults and the binary attachments
    return success
