# -*- coding: utf-8 -*-

from MoinMoin.request import RequestBase
from MoinMoin.PageEditor import PageEditor
from MoinMoin.action import AttachFile
from MoinMoin.wikiutil import importPlugin, PluginMissingError

from graphingwiki.editing import underlay_to_pages
from graphingwiki.util import actionname

import os
import re

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
        patched_result = on_success(self, result, (args, keys))
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

def graphdata_save(self, result, _):
    graphsaver = _get_save_plugin(self)

    if not graphsaver:
        return

    path = underlay_to_pages(self.request, self)
    text = self.get_raw_body()

    graphsaver(self.page_name, self.request, text, path, self)

def graphdata_copy(self, result, (args, _)):
    newpagename = args[0]
    graphsaver = _get_save_plugin(self)

    if not graphsaver:
        return

    text = self.get_raw_body()
    path = underlay_to_pages(self.request, self)

    graphsaver(newpagename, self.request, text, path, self)

def graphdata_rename(self, (success, msg), _):
    if not success:
        return

    graphsaver = _get_save_plugin(self)
    path = underlay_to_pages(self.request, self)

    graphsaver(self.page_name, self.request, '', path, self)

def variable_insert(self, result, _):
    """
    Replace variables specified in wikiconfig eg.

    gwikivariables = {'GWIKITEST': 'I am the bestest!'}
    """

    cfgvar = getattr(self.request.cfg, 'gwikivariables', dict())
    for name in cfgvar:
        result = result.replace('@%s@' % name, cfgvar[name])

    # Add the page's creator as a dynamic variable
    backto = self.request.form.get('backto', [''])[0]
    result = result.replace('@CREATORPAGE@', backto)

    return result

def attachfile_filelist(self, result, (args, _)):
    _ = self.getText
    attachments = re.findall('do=view&amp;target=([^"]+)', result)
    if len(attachments) < 2:
        return result

    form = u'<form method="GET" action="%s">\n' % \
        actionname(self, self.page.page_name) + \
        u'<input type=hidden name=action value="AttachFile">'

    result = form + result

    att1 = self.form.get('att1', [''])[0]
    att2 = self.form.get('att2', [''])[0]
    sort = self.form.get('sort', ['normal'])[0]

    for target in attachments:
        buttontext = '\\1 | ' + \
            '<input type="radio" value="%s" name="att1"/%s>' % \
            (target, att1 == target and ' checked' or '')+ \
            '<input type="radio" value="%s" name="att2"/%s>' % \
            (target, att2 == target and ' checked' or '')+ \
            _('diff')

        viewtext = '(<a href.+&amp;do=view&amp;target=%s">%s</a>)' % \
            (re.escape(target), _("view"))
        
        result, count = re.subn(viewtext, buttontext, result, 1)

    result = result + \
        '<input type="radio" value="normal" name="sort"/%s>%s\n' % \
        (sort == 'normal' and ' checked' or '', _("Normal")) + \
        '<input type="radio" value="sort" name="sort"/%s>%s\n' % \
        (sort == 'sort' and ' checked' or '', _("Sort")) + \
        '<input type="radio" value="uniq" name="sort"/%s>%s\n' % \
        (sort == 'uniq' and ' checked' or '', _("Sort + uniq")) + \
        '<input type="radio" value="cnt" name="sort"/%s>%s\n' % \
        (sort == 'cnt' and ' checked' or '', _("Sort + uniq + count")) + \
        '<br><input type=submit name=do value="diff"></form>'

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
    PageEditor.copyPage = monkey_patch(PageEditor.copyPage, 
                                       graphdata_copy)

    AttachFile._build_filelist = monkey_patch(AttachFile._build_filelist, 
                                              attachfile_filelist)

    # FIXME: Remove this patch when MoinMoin makes variable names
    # configurable in some fashion.
    PageEditor._expand_variables = monkey_patch(PageEditor._expand_variables,
                                                variable_insert)

    _hooks_installed = True
