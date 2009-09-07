# -*- coding: utf-8 -*-

import sys
from opencollab.wiki import WikiFailure
from opencollab.meta import Metas

def importMetas(collab, metas, template, verbose, replace=True):
    for page, pmeta in metas.iteritems():
        try:
            status = collab.setMeta(page, pmeta, template=template, replace=replace)
        except WikiFailure, msg:
            error = page + " " + repr(msg)
            error += repr(pmeta)
            sys.exit(error)
        else:
            if verbose:
                print page, status

def getPages(collab, search_string):
    pages = Metas()
    try:
        search_string = unicode(search_string, 'utf-8')
    except UnicodeDecodeError:
        search_string = unicode(search_string, 'iso-8859-1')
    except UnicodeDecodeError:
        error = "Could not understand system default encoding."
        sys.exit(error)
    pages = collab.getMeta(search_string)
    return pages

