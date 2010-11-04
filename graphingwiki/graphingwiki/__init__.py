# -*- coding: utf-8 -*-

import MoinMoin.wikisync  
import MoinMoin.wikiutil as wikiutil
  
from MoinMoin.request import RequestBase
from MoinMoin.PageEditor import PageEditor
from MoinMoin.action import AttachFile
from MoinMoin.wikiutil import importPlugin, PluginMissingError
from MoinMoin.security import ACLStringIterator

import sys
import os
import re
import socket
import xmlrpclib

SEPARATOR = '-gwikiseparator-'

# Get action name
def actionname(request, pagename):
    return '%s/%s' % (request.getScriptname(), url_escape(pagename))

def url_escape(text):
    # Escape characters that break links in html values fields, 
    # macros and urls with parameters
    return re.sub('[\]"\?#&+]', lambda mo: '%%%02x' % ord(mo.group()), text)

def url_unescape(text):
    return re.sub(r"%([0-9a-f]{2})", lambda mo: chr(int(mo.group(1), 16)), text)

def id_escape(text):
    chr_re = re.compile('[^a-zA-Z0-9-_:.]')
    return chr_re.sub(lambda mo: '_%02x_' % ord(mo.group()), text)

def id_unescape(text):
    chr_re = re.compile('_([0-9a-f]{2})_')
    return chr_re.sub(lambda mo: chr(int(mo.group(1), 16)), text)

# Finding dependencies centrally

gv_found = True
gv = None

# 32bit and 64bit versions
try:
    sys.path.append('/usr/lib/graphviz/python')
    sys.path.append('/usr/local/lib/graphviz/python') # OSX
    sys.path.append('/usr/lib/pyshared/python2.6') # Ubuntu 9.10
    sys.path.append('/usr/lib/pyshared/python2.5') # Ubuntu 9.10
    import gv
except ImportError:
    sys.path[-1] = '/usr/lib64/graphviz/python'
    try:
        import gv
    except ImportError:
        gv_found = False
        pass

igraph_found = True
igraph = None

try:
    import igraph
except:
    igraph_found = False
    pass

if gv_found:
    # gv needs libag to be initialised before using any read methods,
    # making a graph here seems to ensure aginit() is called
    gv.graph(' ')

cairo_found = True
cairo = None

try:
    import cairo
except ImportError:
    cairo_found = False
    pass

geoip_found = True
GeoIP = None

try:
    import GeoIP
except ImportError:
    geoip_found = False
    pass

# HTTP Auth support to wikisync:
# http://moinmo.in/FeatureRequests/WikiSyncWithHttpAuth
class MoinRemoteWikiHttpAuth(MoinMoin.wikisync.MoinRemoteWiki):
    """ Used for MoinMoin wikis reachable via XMLRPC. """
    def __init__(self, request, interwikiname, prefix, pagelist, user, password, verbose=False):
        self.request = request
        self.prefix = prefix
        self.pagelist = pagelist
        self.verbose = verbose
        _ = self.request.getText

        wikitag, wikiurl, wikitail, wikitag_bad = wikiutil.resolve_interwiki(self.request, interwikiname, '')
        self.wiki_url = wikiutil.mapURL(self.request, wikiurl)
        self.valid = not wikitag_bad
        self.xmlrpc_url = self.wiki_url + "?action=xmlrpc2"
        if not self.valid:
            self.connection = None
            return

        httpauth = False
        notallowed = _("Invalid username or password.")

        self.connection = self.createConnection()

        try:
            iw_list = self.connection.interwikiName()
        except socket.error:
            raise MoinMoin.wikisync.UnsupportedWikiException(_("The wiki is currently not reachable."))
        except xmlrpclib.Fault, err:
            raise MoinMoin.wikisync.UnsupportedWikiException("xmlrpclib.Fault: %s" % str(err))
        except xmlrpclib.ProtocolError, err:
            if err.errmsg != "Authorization Required":
                raise

            if user and password:
                try:
                    import urlparse
                    import urllib

                    def urlQuote(string):
                        if isinstance(string, unicode):
                            string = string.encode("utf-8")
                        return urllib.quote(string, "/:")

                    scheme, netloc, path, a, b, c = \
                        urlparse.urlparse(self.wiki_url)
                    action = "action=xmlrpc2"

                    user, password = map(urlQuote, [user, password])
                    netloc = "%s:%s@%s" % (user, password, netloc)
                    self.xmlrpc_url = urlparse.urlunparse((scheme, netloc, 
                                                           path, "", 
                                                           action, ""))

                    self.connection = self.createConnection()
                    iw_list = self.connection.interwikiName()

                    httpauth = True
                except:
                    raise MoinMoin.wikisync.NotAllowedException(notallowed)
            elif user:
                return
            else:
                raise MoinMoin.wikisync.NotAllowedException(notallowed)

        if user and password:
            token = self.connection.getAuthToken(user, password)
            if token:
                self.token = token
            elif httpauth:
                self.token = None
            else:
                raise MoinMoin.wikisync.NotAllowedException(_("Invalid username or password."))
        else:
            self.token = None

        self.remote_interwikiname = remote_interwikiname = iw_list[0]
        self.remote_iwid = remote_iwid = iw_list[1]
        self.is_anonymous = remote_interwikiname is None
        if not self.is_anonymous and interwikiname != remote_interwikiname:
            raise MoinMoin.wikisync.UnsupportedWikiException(_("The remote wiki uses a different InterWiki name (%(remotename)s)"
                                             " internally than you specified (%(localname)s).") % {
                "remotename": wikiutil.escape(remote_interwikiname), "localname": wikiutil.escape(interwikiname)})

        if self.is_anonymous:
            self.iwid_full = MoinMoin.wikisync.packLine([remote_iwid])
        else:
            self.iwid_full = MoinMoin.wikisync.packLine([remote_iwid, 
                                                         interwikiname])

MoinMoin.wikisync.MoinRemoteWiki = MoinRemoteWikiHttpAuth

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

def underlay_to_pages(req, p):
    underlaydir = req.cfg.data_underlay_dir

    pagepath = p.getPagePath()

    # If the page has not been created yet, create its directory and
    # save the stuff there
    if underlaydir in pagepath:
        pagepath = pagepath.replace(underlaydir, pagepath)
        if not os.path.exists(pagepath):
            os.makedirs(pagepath)

    return pagepath

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
#    from graphingwiki.backend.durusclient import GraphData
    from graphingwiki.backend.shelvedb import GraphData
    if "_graphdata" not in self.__dict__:
        self.__dict__["_graphdata"] = GraphData(self)
    return self.__dict__["_graphdata"]

def graphdata_close(self):
    graphdata = self.__dict__.pop("_graphdata", None)
    if graphdata is not None:
        graphdata.commit()
        graphdata.close()

def graphdata_commit(self, *args):
    graphdata = self.__dict__.pop("_graphdata", None)
    if graphdata is not None:
        graphdata.commit()

def _get_save_plugin(self):
    # Save to graph file if plugin available.
    try:
        graphsaver = importPlugin(self.request.cfg, "action", "savegraphdata")
    except PluginMissingError:
        return

    return graphsaver

## TODO: Hook PageEditor.sendEditor to add data on template to the
## text of the saved page?

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

    # Rename is really filesystem-level rename, no old data is really
    # left behind, so it should be cleared.  When saving with text
    # 'deleted\n', no graph data is actually saved.
    graphsaver(self.page_name, self.request, 'deleted\n', path, self)

    # Rename might litter empty directories data/pagename and
    # data/pagename/cache, let's remove them
    oldpath = self.getPagePath(check_create=0)
    for dirpath, dirs, files in os.walk(oldpath, topdown=False):
        # If there are files left, some backups etc information is
        # still there, so let's quit
        if files:
            break

        os.rmdir(dirpath)

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

def acl_user_expand(self, result, _):
    """
    Expand @ME@ user variable, which can result into problems when
    viewing template pages with acl:s
    """
    modifier, entries, rights = result

    entries = [x.replace('@ME@', 'All') for x in entries]

    return (modifier, entries, rights)


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

    # XXX "always" callback is called before the "on_success" one,
    # which pops _graphdata attr out in addition to closing the db
    # connection
    RequestBase.finish = monkey_patch(RequestBase.finish, 
                                      always=graphdata_close)#, on_success=graphdata_commit)
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

    # Monkey patch AttachFile to include diffing
    AttachFile._build_filelist = monkey_patch(AttachFile._build_filelist, 
                                              attachfile_filelist)

    # FIXME: Remove this patch when MoinMoin makes variable names
    # configurable in some fashion.
    PageEditor._expand_variables = monkey_patch(PageEditor._expand_variables,
                                                variable_insert)

    # Fix user variables in template acl strings
    ACLStringIterator.next = monkey_patch(ACLStringIterator.next,
                                          acl_user_expand)

    _hooks_installed = True
