# -*- coding: utf-8 -*-
"""
    PageCache xmlrpc action for Graphingwiki
     - Modify the page cache over xmlrpc

    @copyright: 2012 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import xmlrpclib

from graphingwiki.editing import save_pagecachefile
from graphingwiki.editing import load_pagecachefile
from graphingwiki.editing import delete_pagecachefile
from graphingwiki.editing import list_pagecachefiles
from graphingwiki.util import cache_key

from MoinMoin.wikiutil import normalize_pagename

def list(request, pagename):
    _ = request.getText
    # check ACLs
    if not request.user.may.read(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to access this page"))

    # Grab the attachment
    result = list_pagecachefiles(request, pagename)

    return result

def load(request, pagename, filename):
    _ = request.getText
    # check ACLs
    if not request.user.may.read(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to access this page"))

    # Grab the attachment
    result = load_pagecachefile(request, pagename, filename)

    if not result:
        return xmlrpclib.Fault(2, "%s: %s" % (_("Nonexisting cache file"),
                                              filename))

    return xmlrpclib.Binary(result)

def delete(request, pagename, filename):
    _ = request.getText

    # check ACLs
    if not request.user.may.delete(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to delete a file on this page cache"))

    # Delete the attachment
    result = delete_pagecachefile(request, pagename, filename)

    if not result:
        return xmlrpclib.Fault(2, "%s: %s" % (_("Nonexisting attachment"),
                                              filename))

    return True

def save(request, pagename, filename, content, overwrite):
    _ = request.getText

    # also check ACLs
    if not request.user.may.write(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to cache a file to this page"))

    # Attach the decoded file
    success = save_pagecachefile(request, pagename, content, 
                                 filename, overwrite)
    
    if success is True:
        return success
    elif overwrite == False:
        return xmlrpclib.Fault(2, _("Cache file not saved, file exists"))

    return xmlrpclib.Fault(3, _("Unknown error while caching file"))

def execute(xmlrpcobj, pagename, filename=None, action='save',
            content=None, overwrite=False):
    request = xmlrpcobj.request
    _ = request.getText

    pagename = xmlrpcobj._instr(pagename)
    pagename = normalize_pagename(pagename, request.cfg)
    # Fault at empty pagenames
    if not pagename:
        return xmlrpclib.Fault(3, _("No page name entered"))

    # It is possible just to attach data to the cache
    if not filename:
        filename = cache_key(request, (pagename, content))
    else:
        filename = xmlrpcobj._instr(filename)

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

    # Save, delete return the file name on success
    if success is True:
        return xmlrpclib.Binary(filename)

    # Other results include the faults and the binary pagecachefiles
    return success
