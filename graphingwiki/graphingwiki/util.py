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
import StringIO

import urllib
from codecs import getencoder
from xml.dom.minidom import getDOMImplementation
from xml.sax.saxutils import escape as cgi_escape
from xml.sax.saxutils import unescape as cgi_unescape

from MoinMoin.action import cache
from MoinMoin.formatter.text_html import Formatter as HtmlFormatter
from MoinMoin import version as MoinVersion
from MoinMoin import caching
from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.action import AttachFile
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.logfile import editlog

from graphingwiki import geoip_found, GeoIP, id_escape, SEPARATOR
from graphingwiki.graph import Graph

MOIN_VERSION = float('.'.join(MoinVersion.release.split('.')[:2]))


import logging
log = logging.getLogger("graphingwiki")

# configure default logger as advised in logger docs
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())

# Some XML output helpers
def xml_document(top):
    # First, make the header
    impl = getDOMImplementation()
    xml = impl.createDocument(None, top, None)
    top = xml.documentElement

    return xml, top

def xml_node_id_and_text(doc, parent, nodename, text='', **kw):
    node = doc.createElement(nodename)
    for key, value in kw.items():
        node.setAttribute(key, value)
    parent.appendChild(node)

    if text:
        text = doc.createTextNode(text)
        node.appendChild(text)

    return node

# Some GEOIP helpers
def geoip_init(request):
    _ = request.getText

    # Find GeoIP
    GEO_IP_PATH = getattr(request.cfg, 'gwiki_geoip_path', None)

    error = ''
    GEO_IP = None

    if not geoip_found:
        error = _("ERROR: GeoIP Python extensions not installed.")

    elif not GEO_IP_PATH:
        error = _("ERROR: GeoIP data file not found.")

    elif not os.path.isfile(GEO_IP_PATH):
        error = _("ERROR: GeoIP data file not found.")

    elif not os.access(GEO_IP_PATH, os.R_OK):
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
    request.write(request.page.formatter.endDocument())
    request.theme.send_closing_html()

# Encoder from unicode to charset selected in config
encoder = getencoder(config.charset)
def encode(str):
    return encoder(str, 'replace')[0]


# See also http://bugs.python.org/issue9061
QUOTEDATTRS = {'"': '&#x22;', "'": '&#x27;', '/': '&#x2F;'}
UNQUOTEDATTRS = dict()
UNQUOTEDATTRS.update([(y, x) for x, y in QUOTEDATTRS.items()])

def form_escape(text):
    # Escape characters that break value fields in html forms
    return cgi_escape(text, QUOTEDATTRS)

def form_unescape(text):
    # Unescape characters that break value fields in html forms
    return cgi_unescape(text, UNQUOTEDATTRS)

def form_writer(fmt, *args):
    args = tuple(map(form_escape, args))
    return fmt % args

def _as_str(string):
    if isinstance(string, unicode):
        return string.encode("utf-8")
    return string

def url_parameters(args):
    url_args = list()
    for key in args:
        for val in args[key]:
            key = urllib.quote_plus(_as_str(key))
            val = urllib.quote_plus(_as_str(val))
            url_args.append(key + '=' + val)

    return "?" + ('&'.join(url_args))

def url_construct(request, args, pagename=''):
    req_url = request.script_root + '/'
    if pagename:
        req_url += urllib.quote(_as_str(pagename))

    if args:
        req_url += url_parameters(args)

    return req_url

def render_error(text):
    return '<p><strong class="error">%s</strong></p>' % form_escape(text)

def render_warning(text):
    return '<p><strong class="warning">%s</strong></p>' % form_escape(text)

def make_tooltip(request, pagename, format=''):
    if not request.user.may.read(pagename):
        return str()

    _ = request.getText

    # Add tooltip, if applicable
    # Only add non-guaranteed attrs to tooltip
    pagemeta = dict()
    metas = request.graphdata.get_meta(pagename)
    for key in metas:
        pagemeta[key] = [x for x in metas[key]]
    for key in ['gwikicategory', '_notype']:
        pageout = request.graphdata.get_out(pagename)
        if key in pageout:
            pagemeta.setdefault(key, list()).extend(pageout[key])

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

ATTACHMENT_SCHEMAS = ["attachment", "drawing"]

def encode_page(page):
    return encode(page)

def decode_page(page):
    return unicode(page, config.charset)


_url_re = None
def get_url_re():
    global _url_re
    if not _url_re:
        from MoinMoin.parser.text_moin_wiki import Parser
        # Ripped off from Parser
        url_pattern = u'|'.join(config.url_schemas)
        url_rule = ur'%(url_guard)s(%(url)s)\:([^\s\<%(punct)s]|([%(punct)s][^\s\<%(punct)s]))+' % {
            'url_guard': u'(^|(?<!\w))',
            'url': url_pattern,
            'punct': Parser.punct_pattern,
        }
        _url_re = re.compile(url_rule)
    return _url_re

def node_type(request, nodename):
    if ':' in nodename:
        if get_url_re().search(nodename):
            return 'url'

        start = nodename.split(':')[0]
        if start in ATTACHMENT_SCHEMAS:
            return 'attachment'

        # Check if we know of the wiki an interwiki-style link is
        # trying to refer to. If not, assume that this should not be a
        # link.
        iw_list = wikiutil.load_wikimap(request)
        if iw_list.has_key(start):
            return 'interwiki'
        elif start:
            return 'none'

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
        return '../' * subrank + './%sProperty' % (link)

def format_wikitext(request, data, pagename=None):
    from MoinMoin.parser.text_moin_wiki import Parser

    if pagename:
        oldpage = request.page
        request.page = Page(request, pagename)

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

    if pagename:
        request.page = oldpage

    return data.getvalue().strip()

def wrap_span(request, key, data, id):
    if not key:
        return format_wikitext(request, data)

    return '<span id="' + \
        id_escape('%(page)s%(sepa)s%(key)s%(sepa)s%(id)s' % 
                  {'page': request.page.page_name, 'sepa': SEPARATOR, 
                   'id': id, 'key': key}) + '">' + \
                   format_wikitext(request, data) + '</span>'

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

# The load_ -functions try to minimise unnecessary reloading and overloading

def load_node(request, graph, node, urladd):
    load_origin = False

    nodeitem = graph.nodes.get(node)
    if not nodeitem:
        nodeitem = graph.nodes.add(node)
        load_origin = True

    # Get new data for current node
    adata = load_graph(request, node, urladd, load_origin)

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
            # Parent knows about links to pages even though they might
            # not see anything about the page being linked to
            if request.user.may.read(child):
                newnode.update(adata.nodes.get(child))
            else:
                newnode.gwikiURL = './\N'

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
            # Do not add link parents if they are not known
            if not request.user.may.read(parent):
                continue
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
    # XXX gone in moin 1.9
    # pageitem.clean_acl_cache()

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


def _add_node(request, pagename, graph, urladd="", nodetype=""):
    # Don't bother if the node has already been added
    if graph.nodes.get(pagename):
        return graph

    node = graph.nodes.add(pagename)
    # Add metadata
    for key, val in request.graphdata.get_meta(pagename).iteritems():
        if key in SPECIAL_ATTRS:
            node.__setattr__(key, ''.join(val))
        else:
            node.__setattr__(key, val)

    # Add links as metadata
    for key, val in request.graphdata.get_out(pagename).iteritems():
        if key == NO_TYPE:
            continue
        if key in SPECIAL_ATTRS:
            node.__setattr__(key, ''.join(val))
        else:
            node.__setattr__(key, val)

    # Shapefile is an extra special case
    for shape in request.graphdata.get_meta(pagename).get('gwikishapefile', list()):
        node.gwikishapefile = shape
    # so is category
    node.gwikicategory = \
         request.graphdata.get_out(pagename).get('gwikicategory', list())

    # Configuration for local pages next, 
    # return known to be something else
    if not nodetype == 'page':
        return graph

    # Local nonexistent pages must get URL-attribute
    if not hasattr(node, 'gwikiURL'):
        node.gwikiURL = './' + pagename

    if request.graphdata.is_saved(pagename):
        node.gwikiURL += urladd
        # FIXME: Is this needed?
        # node.gwikiURL = './' + node.gwikiURL
    elif Page(request, pagename).isStandardPage():
        # try to be helpful and add editlinks to non-underlay pages
        node.gwikiURL += u"?action=edit"
        node.gwikitooltip = request.getText('Add page')

    if node.gwikiURL.startswith('attachment:'):
        pagefile = node.gwikiURL.split(':')[1]
        page, fname = attachment_pagefile(pagefile, pagename)

        node.gwikilabel = encode(fname)
        node.gwikiURL = encode(actionname(request, page) + \
            '?action=AttachFile&do=get&target=' + fname)

    return graph

def load_graph(request, pagename, urladd, load_origin=True):
    if not request.user.may.read(pagename):
        return None

    def add_adata_link(adata, edge, type):
        # Add edge if it does not already exist
        e = adata.edges.get(*edge)
        if not e:
            e = adata.edges.add(*edge)
            e.linktype = set([type])
        else:
            e.linktype.add(type)
        return adata

    cat_re = category_regex(request)
    temp_re = template_regex(request)

    page = request.graphdata.getpage(pagename)
    if not page:
        return None

    # Make graph, initialise head node
    adata = Graph()
    if load_origin:
        adata = _add_node(request, pagename, adata, urladd, 'page')
    else:
        adata.nodes.add(pagename)

    # Add links to page
    links = request.graphdata.get_in(pagename)
    for linktype in links:
        for src in links[linktype]:
            # Filter Category, Template pages
            if cat_re.search(src) or temp_re.search(src):
                continue
            # Add page and its metadata
            # Currently pages can have links in them only
            # from local pages, thus nodetype == page
            adata = _add_node(request, src, adata, urladd, 'page')
            adata = add_adata_link(adata, (src, pagename), linktype)
    # Add links from page
    links = request.graphdata.get_out(pagename)
    for linktype in links:
        #print "add_node", pagename, dst
        for i, dst in enumerate(links[linktype]):
            # Filter Category, Template pages
            if cat_re.search(dst) or temp_re.search(dst):
                continue

            # Fix links to everything but pages
            label = ''
            gwikiurl = ''
            tooltip = ''
            nodetype = node_type(request, dst)

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

                _, exists = attachment_file(request, 
                                            att_page, att_file)

                # For existing attachments, have link to view it
                if exists:
                    gwikiurl = "./%s?action=AttachFile&do=get&target=%s" % \
                        (att_page, att_file)
                    tooltip = request.getText('View attachment')
                # For non-existing, have a link to upload it
                else:
                    gwikiurl = "./%s?action=AttachFile&rename=%s" % \
                        (att_page, att_file)
                    tooltip = request.getText('Add attachment')

            elif nodetype == 'interwiki':
                # Get effective URL:s to interwiki URL:s
                iwname = dst.split(':')
                iw_list = wikiutil.load_wikimap(request)
                
                gwikiurl = iw_list[iwname[0]] + iwname[1]
                tooltip = iwname[1] + ' ' + \
                    request.getText('page on') + \
                    ' ' + iwname[0] + ' ' + \
                    request.getText('wiki')

            elif nodetype == 'url':
                # URL:s have the url already, keep it
                gwikiurl = dst
                tooltip = dst

            elif nodetype == 'none':
                # Was not a valid link after all, eg. an
                # interwiki-style link, but the wiki name was not in
                # intermap.
                continue

            # Add page and its metadata
            adata = _add_node(request, dst, adata, urladd, nodetype)
            adata = add_adata_link(adata, (pagename, dst), linktype)
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
