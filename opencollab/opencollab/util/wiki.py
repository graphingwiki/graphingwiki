# -*- coding: utf-8 -*-

import sys
from opencollab.wiki import WikiFailure

def importMetas(collab, metas, template, verbose, replace=True):
    for page, pmeta in metas.iteritems():
        try:
            status = collab.setMeta(page, pmeta, template=template, replace=replace)
        except WikiFailure, msg:
            error = page + " " + msg
            sys.exit(error)
        else:
            if verbose:
                print page, status
