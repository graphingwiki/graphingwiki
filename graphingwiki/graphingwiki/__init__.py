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
        # If we want to patch the result also
        patched_result = on_success(self, result)
        if patched_result:
            return patched_result
        return result
    return _patched

# FIXME: A ugly, ugly hack to fix ugly hacks suck as copy(request).
# Should be removed by removing request copying and such.

def request_copy(self):
    from copy import copy

    graphdata = self.graphdata
    self._graphdata = None

    del RequestBase.__copy__

    new_request = copy(self)
    new_request._graphdata = graphdata

    RequestBase.__copy__ = request_copy

    self._graphdata = graphdata
    return new_request
RequestBase.__copy__ = request_copy

# Functions for properly opening, closing, saving and deleting
# graphdata. NB: Do not return anything in functions used in
# monkey_patch unless you want to affect the return value of the
# patched function

def graphdata_getter(self):
    from graphingwiki.util import GraphData
    if "_graphdata" not in self.__dict__:
        self.__dict__["_graphdata"] = GraphData(self)
    return self.__dict__["_graphdata"]

def graphdata_close(self):
    graphdata = self.__dict__.pop("_graphdata", None)
    if graphdata is not None:
        graphdata.closedb()

def _get_save_plugin(self):
    # Save to graph file if plugin available.
    try:
        graphsaver = importPlugin(self.request.cfg, "action", "savegraphdata")
    except PluginMissingError:
        return

    return graphsaver

def graphdata_save(self, result):
    graphsaver = _get_save_plugin(self)

    if not graphsaver:
        return

    path = underlay_to_pages(self.request, self)
    text = self.get_raw_body()

    graphsaver(self.page_name, self.request, text, path, self)

def graphdata_rename(self, (success, _)):
    if not success:
        return

    graphsaver = _get_save_plugin(self)
    path = underlay_to_pages(self.request, self)

    graphsaver(self.page_name, self.request, '', path, self)

def variable_insert(self, result):
    """
    Replace variables specified in wikiconfig eg.

    gwikivariables = {'GWIKITEST': 'I am the bestest!'}
    """

    cfgvar = getattr(self.request.cfg, 'gwikivariables', dict())
    for name in cfgvar:
        result = result.replace('@%s@' % name, cfgvar[name])

    return result

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
    # Patch RequestBase.run too, just in case finally might not get
    # called in case of a crash.
    RequestBase.run = monkey_patch(RequestBase.run, 
                                   always=graphdata_close)

    # Monkey patch the different saving methods to update the metas in
    # the meta database.
    # Note: PageEditor.renamePage seems to use .saveText for the new
    # page (thus already updating the page's metas), so only the old page's
    # metas need to be deleted explicitly.
    PageEditor.saveText = monkey_patch(PageEditor.saveText, 
                                       graphdata_save)
    PageEditor.renamePage = monkey_patch(PageEditor.renamePage, 
                                         graphdata_rename)

    # FIXME: Remove this patch when MoinMoin makes variable names
    # configurable in some fashion.
    PageEditor._expand_variables = monkey_patch(PageEditor._expand_variables,
                                              variable_insert)

    _hooks_installed = True
