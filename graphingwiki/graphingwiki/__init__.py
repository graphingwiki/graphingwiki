# -*- coding: utf-8 -*-

from MoinMoin.request import RequestBase
from MoinMoin.PageEditor import PageEditor
from MoinMoin.wikiutil import importPlugin, PluginMissingError

from graphingwiki.editing import underlay_to_pages

import os

# Helper functions for monkey patching and dealing with underlays.

def ignore(*args, **keys):
    pass

def monkey_patch(original, on_success=ignore, always=ignore):
    def _patched(self, *args, **keys):
        try:
            result = original(self, *args, **keys)
        finally:
            always(self)
        on_success(self, result)
        return result
    return _patched

# Functions for properly opening, closing, saving and deleting graphdata.

def graphdata_getter(self):
    from graphingwiki.patterns import GraphData

    if "_graphdata" not in self.__dict__:
        self.__dict__["_graphdata"] = GraphData(self)
    return self.__dict__["_graphdata"]

def graphdata_close(self):
    graphdata = self.__dict__.pop("_graphdata", None)
    if graphdata is not None:
        graphdata.closedb()

def graphdata_save(self, result):
    # Save to graph file if plugin available.
    try:
        graphsaver = importPlugin(self.request.cfg, "action", "savegraphdata")
    except PluginMissingError:
        return

    if not graphsaver:
        return

    path = underlay_to_pages(self.request, self)
    text = self.get_raw_body()

    graphsaver(self.page_name, self.request, text, path, self)

def graphdata_delete(self, (success, _)):
    if not success:
        return
    self.request.graphdata.writelock()
    self.request.graphdata.pop(self.page_name, None)

# Main function for injecting graphingwiki extensions straight into
# Moin's beating heart.

_hooks_installed = False

def install_hooks():
    global _hooks_installed

    if _hooks_installed:
        return

    # Monkey patch the request class to have the property "graphdata"
    # which, if used, is then closed properly when the request
    # finishes.
    RequestBase.graphdata = property(graphdata_getter)
    RequestBase.finish = monkey_patch(RequestBase.finish, 
                                      always=graphdata_close)

    # Monkey patch the different saving methods to update the metas in
    # the meta database.
    # Note: PageEditor.renamePage seems to use .saveText for the new
    # page (thus already updating the page's metas), so only the old page's
    # metas need to be deleted explicitly.
    PageEditor.saveText = monkey_patch(PageEditor.saveText, 
                                       graphdata_save)
    PageEditor.deletePage = monkey_patch(PageEditor.deletePage, 
                                         graphdata_delete)
    PageEditor.renamePage = monkey_patch(PageEditor.renamePage, 
                                         graphdata_delete)

    _hooks_installed = True
