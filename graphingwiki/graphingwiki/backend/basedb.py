import UserDict
import re
import os

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page

from graphingwiki.util import encode, category_regex, template_regex, \
    SPECIAL_ATTRS, NO_TYPE, absolute_attach_name, attachment_file, node_type
from graphingwiki.graph import Graph
from graphingwiki import actionname

def strip_meta(key, val):
    key = key.strip()
    val = val.strip()

    # retain empty labels
    if key == 'gwikilabel' and not val:
        val = ' '        

    return key, val

class GraphDataBase(UserDict.DictMixin):
    def __init__(self, request):
        self.request = request

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
        raise NotImplemented()

    def __setitem__(self, item, value):
        raise NotImplemented()

    def __delitem__(self, item):
        raise NotImplemented()

    def keys(self):
        raise NotImplemented()

    def __iter__(self):
        raise NotImplemented()

    def __contains__(self, item):
        raise NotImplemented()

    def commit(self):
        raise NotImplemented()

    def getpage(self, pagename):
        # Always read data here regardless of user rights,
        # they should be handled elsewhere.
        return self.get(pagename, dict())

    def add_link(self, new_data, pagename, nodename, linktype):
        raise NotImplemented()

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
            page, fname = attachment_pagefile(pagefile, pagename)

            node.gwikilabel = encode(fname)
            node.gwikiURL = encode(actionname(self.request, page) + \
                '?action=AttachFile&do=get&target=' + fname)

        return graph

    def set_attribute(self, new_data, node, key, val):
        key, val = strip_meta(key, val)

        temp = new_data.get(node, {})

        if not temp.has_key(u'meta'):
            temp[u'meta'] = {key: [val]}
        elif not temp[u'meta'].has_key(key):
            temp[u'meta'][key] = [val]
        # a page can not have more than one label, shapefile etc
        elif key in SPECIAL_ATTRS:
            temp[u'meta'][key] = [val]
        else:
            temp[u'meta'][key].append(val)

        new_data[node] = temp

    def add_meta(self, new_data, pagename, (key, val)):
        
        # Do not handle empty metadata, except empty labels
        val = val.strip()
        if key == 'gwikilabel' and not val:
            val = ' '        

        if not val:
            return

        # Values to be handled in graphs
        if key in SPECIAL_ATTRS:
            self.set_attribute(new_data, pagename, key, val)
            # If color defined, set page as filled
            if key == 'fillcolor':
                self.set_attribute(new_data, pagename, 'style', 'filled')
            return

        # Save to shelve's metadata list
        self.set_attribute(new_data, pagename, key, val)

    def load_graph(self, pagename, urladd, load_origin=True):
        if not self.request.user.may.read(pagename):
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
        for linktype in links:
            for src in links[linktype]:
                # Filter Category, Template pages
                if cat_re.search(src) or temp_re.search(src):
                    continue
                # Add page and its metadata
                # Currently pages can have links in them only
                # from local pages, thus nodetype == page
                adata = self._add_node(src, adata, urladd, 'page')
                adata = add_adata_link(adata, (src, pagename), linktype)
        # Add links from page
        links = page.get('out', dict())
        for linktype in links:
            for i, dst in enumerate(links[linktype]):
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


