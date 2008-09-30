# -*- coding: utf-8 -*-
from MoinMoin.security import Permissions
from graphingwiki.patterns import debug

from graphingwiki.editing import underlay_to_pages

def patched_run(self):
    try:
        self.orig_run(self)
    finally:
        if hasasttr(self, 'graphdata') and self.graphdata.opened:
            self.finish()

from MoinMoin.request import RequestBase
            
if not hasattr(RequestBase, 'orig_run'):
    RequestBase.orig_run = RequestBase.run
    RequestBase.run = patched_run

class SecurityPolicy(Permissions):
    def save(self, editor, newtext, rev, **kw):
        # No problem to save if my base class agree
        if Permissions.save(self, editor, newtext, rev, **kw):
            from MoinMoin.wikiutil import importPlugin, PluginMissingError

            try:
                # save to graph file, if plugin available
                graphsaver = importPlugin(self.request.cfg,
                                          'action',
                                          'savegraphdata')
            except PluginMissingError:
                return True

            if not graphsaver:
                return True
            else:
                path = underlay_to_pages(self.request, editor)

                graphsaver(editor.page_name, self.request,
                           newtext, path, editor)
                
                return True

        else:
            return False
