# -*- coding: utf-8 -*-

from opencollab.wiki import CLIWiki, WikiFailure

def importMetas(collab, metas, template, replace=True):
    for page, pmeta in metas.iteritems():
        try:
            collab.setMeta(page, pmeta, template=template, replace=replace)
        except WikiFailure, msg:
            error = page + " " + msg
            sys.exit(error)

