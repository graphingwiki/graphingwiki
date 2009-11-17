# -*- coding: utf-8 -*-
"""
    Utils for graph generation, compatibility between MoinMoin versions
    etc.

    @copyright: 2006-2009 by Joachim Viide and
                             Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""

import re
import os
import shelve
import itertools
import UserDict
import StringIO
import cgi

from codecs import getencoder
from xml.dom.minidom import getDOMImplementation

import MoinMoin.version

from MoinMoin.action import cache
from MoinMoin.formatter.text_html import Formatter as HtmlFormatter
from MoinMoin import caching
from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.util.lock import ReadLock, WriteLock
from MoinMoin.action import AttachFile
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.logfile import editlog

from graphingwiki import geoip_found, GeoIP
from graphingwiki.graph import Graph

MOIN_VERSION = float('.'.join(MoinMoin.version.release.split('.')[:2]))

SEPARATOR = '-gwikiseparator-'

# Some XML output helpers
def xml_document(top):
    # First, make the header
    impl = getDOMImplementation()
    xml = impl.createDocument(None, top, None)
    top = xml.documentElement

    return xml, top

def xml_node_id_and_text(doc, parent, nodename, text='', cdata='', **kw):
    node = doc.createElement(nodename)
    for key, value in kw.items():
        node.setAttribute(key, value)
    parent.appendChild(node)

    if text:
        text = doc.createTextNode(text)
        node.appendChild(text)
    # Does not work, I'm probably not using it correctly
    elif cdata:
        text = doc.createCDATASection(text)
        node.appendChild(text)

    return node

# Some GEOIP helpers
def geoip_init(request):
    # Find GeoIP
    GEO_IP_PATH = getattr(request.cfg, 'gwiki_geoip_path', None)

    error = ''
    GEO_IP = None

    if not geoip_found:
        error = _("ERROR: GeoIP Python extensions not installed.")

    elif not GEO_IP_PATH:
        error = _("ERROR: GeoIP data file not found.")

    else:
        GEO_IP = GeoIP.open(GEO_IP_PATH, GeoIP.GEOIP_STANDARD)

    return GEO_IP, error

def geoip_get_coords(GEO_IP, text):
    if text is None:
        return None

    # Do not accept anything impossible
    if not re.match('^[a-zA-Z0-9.]+$', text):
        return None

    try:
        gir = GEO_IP.record_by_name(text)
    except:
        return None

    if not gir:
        return None

    return u"%s,%s" % (gir['longitude'], gir['latitude'])

# Methods related to Moin cache feature
def latest_edit(request):
    log = editlog.EditLog(request)
    entry = ''

    for x in log.reverse():
        entry = x
        break
    
    return entry.ed_time_usecs

def cache_exists(request, key):
    if getattr(request.cfg, 'gwiki_cache_invalidate', False):
        return False

    return cache.exists(request, key)

def cache_key(request, parts):
    data = StringIO.StringIO()

    # Make sure that repr of the object is unique
    for part in parts:
        data.write(repr(part))

    data = data.getvalue()

    return cache.key(request, content=data)

# Functions for starting and ending page
def enter_page(request, pagename, title):
    _ = request.getText

    request.emit_http_headers()

    title = _(title)
    request.theme.send_title(title,
                             pagename=pagename)
    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter

    request.write(request.page.formatter.startContent("content"))

def exit_page(request, pagename):
    # End content
    request.write(request.page.formatter.endContent()) # end content div
    # Footer
    request.theme.send_footer(pagename)
    request.theme.send_closing_html()

# Encoder from unicode to charset selected in config
encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]

def form_escape(text):
    # Escape characters that break value fields in html forms
    #return re.sub('["]', lambda mo: '&#x%02x;' % ord(mo.group()), text)
    return cgi.escape(text, quote=True)

def form_writer(fmt, *args):
    args = tuple(map(form_escape, args))
    return fmt % args

def url_parameters(args):
    req_url = u'?'

    url_args = list()
    for key in args:
        for val in args[key]:
            url_args.append(u'='.join(map(url_escape, [key, val])))

    req_url += u'&'.join(url_args)

    return req_url

def url_construct(request, args, name=''):
    if not name:
        name = request.page.page_name 

    req_url = request.getScriptname() + u'/' + name

    if args:
        req_url += url_parameters(args)

    return request.getQualifiedURL(req_url)

def make_tooltip(request, pagedata, format=''):
    _ = request.getText

    # Add tooltip, if applicable
    # Only add non-guaranteed attrs to tooltip
    pagemeta = dict()
    for key in pagedata.get('meta', dict()):
        pagemeta[key] = [x for x in pagedata['meta'][key]]
    for key in ['gwikicategory', '_notype']:
        if key in pagedata.get('out', dict()):
            pagemeta.setdefault(key, list()).extend(pagedata['out'][key])

    tooldata = str()
    if pagemeta:
        pagekeys = nonguaranteeds_p(pagemeta)
        tooldata = '\n'.join("-%s: %s" % 
                             (x == '_notype' and _('Links') or x,
                              ', '.join(pagemeta[x]))
                             for x in pagekeys)

    # Graphviz bug: too long tooltips make svg output fail
    if format in ['svg', 'zgr']:
        return tooldata[:6746]

    return tooldata

# Expand include arguments to a list of pages
def expand_include(request, pagename, args):
    pagelist = list()

    for inc_name in args:
        inc_name = wikiutil.AbsPageName(pagename, inc_name)
        if inc_name.startswith("^"):
            try:
                inc_match = re.compile(inc_name)
            except re.error:
                pass # treat as plain page name
            else:
                # Get user filtered readable page list
                pagelist.extend(request.rootpage.getPageList(
                        filter=inc_match.match))
        else:
            pagelist.append(inc_name)
        
    return pagelist
   
# Default node attributes that should not be shown
SPECIAL_ATTRS = ["gwikilabel", "gwikisides", "gwikitooltip", "gwikiskew",
                 "gwikiorientation", "gwikifillcolor", 'gwikiperipheries',
                 'gwikishapefile', "gwikishape", "gwikistyle", 
                 'gwikicategory', 'gwikiURL', 'gwikiimage', 'gwikiinlinks',
                 'gwikicoordinates']
nonguaranteeds_p = lambda node: filter(lambda y: y not in
                                       SPECIAL_ATTRS, dict(node))

NONEDITABLE_ATTRS = ['gwikiinlinks', '-', 'gwikipagename']
editable_p = lambda node: filter(lambda y: y not in 
                                 NONEDITABLE_ATTRS and not '->' in y, node)

NO_TYPE = u'_notype'

# FIXME: Is this needed?
def resolve_iw_url(request, wiki, page): 
    res = wikiutil.resolve_interwiki(request, wiki, page) 
    if res[3] == False: 
        iw_url = res[1] + res[2] 
    else: 
        iw_url = './InterWiki' 
        
    return iw_url 

ATTACHMENT_SCHEMAS = ["attachment", "drawing"]

def encode_page(page):
    return encode(page)

def decode_page(page):
    return unicode(page, config.charset)

def node_type(request, nodename):
    if ':' in nodename:
        if request.graphdata.url_re.search(nodename):
            return 'url'

        start = nodename.split(':')[0]
        if start in ATTACHMENT_SCHEMAS:
            return 'attachment'

        iw_list = wikiutil.load_wikimap(request)
        if iw_list.has_key(start):
            return 'interwiki'

    return 'page'

def filter_categories(request, candidates):
    # Let through only the candidates that are both valid category
    # names and WikiWords

    # Nah, the word rules in 1.6 were not for the feint for heart,
    # just use the wikiutil function until further notice

    return wikiutil.filterCategoryPages(request, candidates)

def get_url_ns(request, pagename, link):
    # Find out subpage level to adjust URL:s accordingly
    subrank = pagename.count('/')
    # Namespaced names
    if ':' in link:
        iw_list = wikiutil.load_wikimap(request)
        iwname = link.split(':')
        if iw_list.has_key(iwname[0]):
            return iw_list[iwname[0]] + iwname[1]
        else:
            return '../' * subrank + './InterWiki'
    # handle categories as ordernodes different
    # so that they would point to the corresponding categories
    if filter_categories(request, [link]):
        return '../' * subrank + './' + link
    else:
        return '../' * subrank + './Property' + link

def format_wikitext(request, data):
    from MoinMoin.parser.text_moin_wiki import Parser

    request.page.formatter = request.formatter
    request.formatter.page = request.page
    parser = Parser(data, request)
    parser.request = request
    # No line anchors of any type to table cells
    request.page.formatter.in_p = 1
    parser._line_anchordef = lambda: ''

    # Do not parse macros from revision pages. For some reason,
    # it spawns multiple requests, which are not finished properly,
    # thus littering a number of readlocks. Besides, the macros do not
    # return anything useful anyway for pages they don't recognize
    if '?action=recall' in request.page.page_name:
        parser._macro_repl = lambda x: x

    # Using StringIO in order to strip the output
    data = StringIO.StringIO()
    request.redirect(data)
    # Produces output on a single table cell
    request.page.format(parser)
    request.redirect()

    return data.getvalue().strip()

def absolute_attach_name(name, target):
    abs_method = target.split(':')[0]

    # Pages from MetaRevisions may have ?action=recall, breaking attach links
    if '?' in name:
        name = name.split('?', 1)[0]

    if abs_method in ATTACHMENT_SCHEMAS and not '/' in target:
        target = target.replace(':', ':%s/' % (name.replace(' ', '_')), 1)

    return target 

def get_selfname(request):
    if request.cfg.interwikiname:
        return request.cfg.interwikiname
    else:
        return 'Self'

def get_wikiurl(request):
    return request.getBaseURL() + '/'

def attachment_file(request, page, file):
    att_file = AttachFile.getFilename(request, page, file)
                                                   
    return att_file, os.path.isfile(att_file)

def attachment_url(request, page, file):
    att_url = AttachFile.getAttachUrl(page, file, request)
                                                   
    return att_url

class GraphData(UserDict.DictMixin):
    def __init__(self, request):
        self.request = request

        gddir = os.path.join(request.cfg.data_dir, 'graphdata')
        if not os.path.isdir(gddir):
            os.mkdir(gddir)
        self.graphshelve = os.path.join(gddir, 'graphdata.shelve')

        self.use_sq_dict = getattr(request.cfg, 'use_sq_dict', False)
        if self.use_sq_dict:
            import sq_dict
            self.shelveopen = sq_dict.shelve
        else:
            self.shelveopen = shelve.open

        # XXX (falsely) assumes shelve.open creates file with same name;
        # it happens to work with the bsddb backend.
        if not os.path.exists(self.graphshelve):
            db = self.shelveopen(self.graphshelve, 'c')
            db.close()

        self.db = None
        self.lock = None

        self.cache = dict()
        self.writing = False
        
        self.readlock()

        from MoinMoin.parser.text_moin_wiki import Parser

        # Ripped off from Parser
        url_pattern = u'|'.join(config.url_schemas)

        url_rule = ur'%(url_guard)s(%(url)s)\:([^\s\<%(punct)s]|([%(punct)s][^\s\<%(punct)s]))+' % {
            'url_guard': u'(^|(?<!\w))',
            'url': url_pattern,
            'punct': Parser.punct_pattern,
        }

        self.url_re = re.compile(url_rule)

    def __getitem__(self, item):
        page = encode_page(item)

        if page not in self.cache:
            self.cache[page] = self.db[page]

        return self.cache[page]

    def __setitem__(self, item, value):
        page = encode_page(item)

        self.db[page] = value
        self.cache[page] = value

    def cacheset(self, item, value):
        page = encode_page(item)

        self.cache[page] = value

    def __delitem__(self, item):
        page = encode_page(item)

        del self.db[page]
        self.cache.pop(page, None)

    def keys(self):
        return map(decode_page, self.db.keys())

    def __iter__(self):
        return itertools.imap(decode_page, self.db)

    def __contains__(self, item):
        page = encode_page(item)
        return page in self.cache or page in self.db

    def readlock(self):
        if self.lock is None or not self.lock.isLocked():
            self.lock = ReadLock(self.request.cfg.data_dir, timeout=60.0)
            self.lock.acquire()

        if self.db is None:
            self.db = self.shelveopen(self.graphshelve, "r")
            self.writing = False

    def writelock(self):
        if self.db is not None and not self.writing:
            self.db.close()
            self.db = None
        
        if (self.lock is not None and self.lock.isLocked() and 
            isinstance(self.lock, ReadLock)):
            self.lock.release()
            self.lock = None

        if self.lock is None or not self.lock.isLocked():
            self.lock = WriteLock(self.request.cfg.data_dir, 
                                  readlocktimeout=60.0)
            self.lock.acquire()

        if self.db is None:
            self.db = self.shelveopen(self.graphshelve, "c")
            self.writing = True

    def closedb(self):
        if self.lock is not None and self.lock.isLocked():
            self.lock.release()
            self.lock = None

        if self.db is not None:
            self.db.close()
            self.db = None

        self.cache.clear()
        self.writing = False

    def getpage(self, pagename):
        # Always read data here regardless of user rights,
        # they should be handled elsewhere.
        return self.get(pagename, dict())

    def reverse_meta(self):
        self.keys_on_pages = dict()
        self.vals_on_pages = dict()
        self.vals_on_keys = dict()

        for page in self:
            if page.endswith('Template'):
                continue

            value = self[page]

            for key in value.get('meta', dict()):
                self.keys_on_pages.setdefault(key, set()).add(page)
                for val in value['meta'][key]:
                    self.vals_on_pages.setdefault(val, set()).add(page)
                    self.vals_on_keys.setdefault(key, set()).add(val)

    def _add_node(self, pagename, graph, urladd="", nodetype=""):
        # Don't bother if the node has already been added
        if graph.nodes.get(pagename):
            return graph

        page = self.getpage(pagename)

        node = graph.nodes.add(pagename)
        # Add metadata
        for key, val in page.get('meta', dict()).iteritems():
            if key in SPECIAL_ATTRS:
                node.__setattr__(key, ''.join(val))
            else:
                node.__setattr__(key, val)

        # Add links as metadata
        for key, val in page.get('out', dict()).iteritems():
            if key == NO_TYPE:
                continue
            if key in SPECIAL_ATTRS:
                node.__setattr__(key, ''.join(val))
            else:
                node.__setattr__(key, val)

        # Shapefile is an extra special case
        for shape in page.get('meta', dict()).get('gwikishapefile', list()):
            node.gwikishapefile = shape
        # so is category
        node.gwikicategory = \
            page.get('out', dict()).get('gwikicategory', list())

        # Configuration for local pages next, 
        # return known to be something else
        if not nodetype == 'page':
            return graph

        # Local nonexistent pages must get URL-attribute
        if not hasattr(node, 'gwikiURL'):
            node.gwikiURL = './' + pagename

        if page.has_key('saved'):
            node.gwikiURL += urladd
            # FIXME: Is this needed?
            # node.gwikiURL = './' + node.gwikiURL
        elif Page(self.request, pagename).isStandardPage():
            # try to be helpful and add editlinks to non-underlay pages
            node.gwikiURL += u"?action=edit"
            node.gwikitooltip = self.request.getText('Add page')

        if node.gwikiURL.startswith('attachment:'):
            pagefile = node.gwikiURL.split(':')[1]
            page, file = attachment_pagefile(pagefile, pagename)

            node.gwikilabel = encode(file)
            node.gwikiURL = encode(actionname(self.request, page) + \
                '?action=AttachFile&do=get&target=' + file)

        return graph

    def _add_link(self, adata, edge, type):
        # Add edge if it does not already exist
        e = adata.edges.get(*edge)
        if not e:
            e = adata.edges.add(*edge)
            e.linktype = set([type])
        else:
            e.linktype.add(type)
        return adata

    def load_graph(self, pagename, urladd, load_origin=True):
        if not self.request.user.may.read(pagename):
            return None

        cat_re = category_regex(self.request)
        temp_re = template_regex(self.request)

        page = self.getpage(pagename)
        if not page:
            return None

        # Make graph, initialise head node
        adata = Graph()
        if load_origin:
            adata = self._add_node(pagename, adata, urladd, 'page')
        else:
            adata.nodes.add(pagename)

        # Add links to page
        links = page.get('in', dict())
        for type in links:
            for src in links[type]:
                # Filter Category, Template pages
                if cat_re.search(src) or temp_re.search(src):
                    continue
                # Add page and its metadata
                # Currently pages can have links in them only
                # from local pages, thus nodetype == page
                adata = self._add_node(src, adata, urladd, 'page')
                adata = self._add_link(adata, (src, pagename), type)

        # Add links from page
        links = page.get('out', dict())
        for type in links:
            for i, dst in enumerate(links[type]):
                # Filter Category, Template pages
                if cat_re.search(dst) or temp_re.search(dst):
                    continue

                # Fix links to everything but pages
                label = ''
                gwikiurl = ''
                tooltip = ''
                nodetype = node_type(self.request, dst)

                if nodetype == 'attachment':
                    # get the absolute name ie both page and filename
                    gwikiurl = absolute_attach_name(pagename, dst)
                    att_parts = gwikiurl.split(':')[1].split('/')
                    att_page = '/'.join(att_parts[:-1])
                    att_file = att_parts[-1]

                    if pagename == att_page:
                        label = "Attachment: %s" % (att_file)
                    else:
                        label = "Attachment: %s/%s" % (att_page, att_file)

                    _, exists = attachment_file(self.request, 
                                                att_page, att_file)

                    # For existing attachments, have link to view it
                    if exists:
                        gwikiurl = "./%s?action=AttachFile&do=get&target=%s" % \
                            (att_page, att_file)
                        tooltip = self.request.getText('View attachment')
                    # For non-existing, have a link to upload it
                    else:
                        gwikiurl = "./%s?action=AttachFile&rename=%s" % \
                            (att_page, att_file)
                        tooltip = self.request.getText('Add attachment')

                elif nodetype == 'interwiki':
                    # Get effective URL:s to interwiki URL:s
                    iwname = dst.split(':')
                    iw_list = wikiutil.load_wikimap(self.request)

                    gwikiurl = iw_list[iwname[0]] + iwname[1]
                    tooltip = iwname[1] + ' ' + \
                        self.request.getText('page on') + \
                        ' ' + iwname[0] + ' ' + \
                        self.request.getText('wiki')

                elif nodetype == 'url':
                    # URL:s have the url already, keep it
                    gwikiurl = dst
                    tooltip = dst

                # Add page and its metadata
                adata = self._add_node(dst, adata, urladd, nodetype)
                adata = self._add_link(adata, (pagename, dst), type)

                if label or gwikiurl or tooltip:
                    node = adata.nodes.get(dst)

                # Add labels, gwikiurls and tooltips
                if label:
                    node.gwikilabel = label
                if gwikiurl:
                    node.gwikiURL = gwikiurl
                if tooltip:
                    node.gwikitooltip = tooltip

        return adata

# The load_ -functions try to minimise unnecessary reloading and overloading

def load_node(request, graph, node, urladd):
    load_origin = False

    nodeitem = graph.nodes.get(node)
    if not nodeitem:
        nodeitem = graph.nodes.add(node)
        load_origin = True

    # Get new data for current node
    adata = request.graphdata.load_graph(node, urladd, load_origin)

    if adata:
        nodeitem.update(adata.nodes.get(node))

    return adata

def load_children(request, graph, parent, urladd):
    adata = load_node(request, graph, parent, urladd)

    # If no data
    if not adata:
        return list()
    if not adata.nodes.get(parent):
        return list()

    children = set()

    # Add new nodes, edges that link to/from the current node
    for child in adata.edges.children(parent):
        if not graph.nodes.get(child):
            newnode = graph.nodes.add(child)
            newnode.update(adata.nodes.get(child))

        newedge = graph.edges.add(parent, child)
        edgedata = adata.edges.get(parent, child)
        newedge.update(edgedata)

        children.add(child)

    return children

def load_parents(request, graph, child, urladd):
    adata = load_node(request, graph, child, urladd)

    # If no data
    if not adata:
        return list()
    if not adata.nodes.get(child):
        return list()

    parents = set()

    # Add new nodes, edges that are the parents of the current node
    for parent in adata.edges.parents(child):
        if not graph.nodes.get(parent):
            newnode = graph.nodes.add(parent)
            newnode.update(adata.nodes.get(parent))

        newedge = graph.edges.add(parent, child)
        edgedata = adata.edges.get(parent, child)
        newedge.update(edgedata)

        parents.add(parent)

    return parents

def delete_moin_caches(request, pageitem):
    # Clear cache
    arena = PageEditor(request, pageitem.page_name)

    # delete pagelinks
    key = 'pagelinks'
    cache = caching.CacheEntry(request, arena, key, scope='item')
    cache.remove()

    # forget in-memory page text
    pageitem.set_raw_body(None)

    # clean the in memory acl cache
    pageitem.clean_acl_cache()

    request.graphdata.cache = dict()

    # clean the cache
    for formatter_name in request.cfg.caching_formats:
        key = formatter_name
        cache = caching.CacheEntry(request, arena, key, scope='item')
        cache.remove()

def template_regex(request, act=False):
    if act and hasattr(request.cfg.cache, 'page_template_regexact'):
        return request.cfg.cache.page_template_regexact

    if hasattr(request.cfg.cache, 'page_template_regex'):
        return request.cfg.cache.page_template_regex

    if MOIN_VERSION > 1.6:
        if not hasattr(request.cfg, 'page_template_regex'):
            request.cfg.page_template_regex = ur'(?P<all>(?P<key>\S+)Template)'
        if act:
            request.cfg.page_template_regexact = \
                re.compile(u'^%s$' % request.cfg.page_template_regex, 
                           re.UNICODE)
            return re.compile(request.cfg.page_template_regexact, re.UNICODE)
    else:
        # For editing.py unittests
        if not hasattr(request.cfg, 'page_template_regex'):
            request.cfg.page_template_regex = u'[a-z]Template$'

    return re.compile(request.cfg.page_template_regex, re.UNICODE)

def category_regex(request, act=False):
    if act and hasattr(request.cfg.cache, 'page_category_regexact'):
        return request.cfg.cache.page_category_regexact

    if hasattr(request.cfg.cache, 'page_category_regex'):
        return request.cfg.cache.page_category_regex

    if MOIN_VERSION > 1.6:
        if not hasattr(request.cfg, 'page_category_regex'):
            request.cfg.page_category_regex = \
                ur'(?P<all>Category(?P<key>(?!Template)\S+))'
        if act:
            request.cfg.page_category_regexact = \
                re.compile(u'^%s$' % request.cfg.page_category_regex, 
                           re.UNICODE)
            return re.compile(request.cfg.page_category_regexact, re.UNICODE)
    else:
        # For editing.py unittests
        if not hasattr(request.cfg, 'page_category_regex'):
            request.cfg.page_category_regex = u'^Category[A-Z]'

    return re.compile(request.cfg.page_category_regex, re.UNICODE)
