# -*- coding: utf-8 -*-
from MoinMoin.security import Permissions
from MoinMoin.request import RequestBase
from MoinMoin.util.antispam import SecurityPolicy as AntiSpam

from graphingwiki.editing import underlay_to_pages
from graphingwiki.patterns import GraphData

# Monkey patching is bad, so let's do it

orig_finish = RequestBase.finish

def graphdata_getter(self):
    if "_graphdata" not in self.__dict__:
        self.__dict__["_graphdata"] = GraphData(self)
    return self.__dict__["_graphdata"]

def patched_finish(self, *args, **keys):
    try:
        return orig_finish(self, *args, **keys)
    finally:
        graphdata = self.__dict__.get("_graphdata", None)
        if graphdata is not None and graphdata.opened:
            request.graphdata.closedb()

RequestBase.graphdata = property(graphdata_getter)
RequestBase.finish = patched_finish

class SecurityPolicy(AntiSpam):
    def save(self, editor, newtext, rev, **kw):
        if getattr(self.request.cfg, 'antispam', False) and not AntiSpam.save(self, editor, newtext, rev, **kw):
          return False
        # No problem to save if my base class agree
        if Permissions.save(self, editor, newtext, rev, **kw):
            from MoinMoin.wikiutil import importPlugin,  PluginMissingError

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

                if not hasattr(self.request, 'graphdata'):
                    getgraphdata(self.request)
                    self.request.lock.release()

                graphsaver(editor.page_name, self.request,
                           newtext, path, editor)
                
                return True

        else:
            return False
