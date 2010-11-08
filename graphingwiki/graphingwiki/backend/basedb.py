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

class GraphDataBase(UserDict.DictMixin):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, item):
        raise NotImplementedError()

    def savepage(self, pagename, pagedict):
        raise NotImplementedError()

    __setitem__ = savepage

    def __delitem__(self, item):
        raise NotImplementedError()

    def keys(self):
        raise NotImplementedError()

    def __iter__(self):
        raise NotImplementedError()

    def __contains__(self, item):
        raise NotImplementedError()

    def commit(self):
        raise NotImplementedError()

    def abort(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()
 
    def getpage(self, pagename):
        # Always read data here regardless of user rights,
        # they should be handled elsewhere.
        return self.get(pagename, dict())

    def is_saved(self, pagename):
        raise NotImplementedError()

    def pagenames(self):
        raise NotImplementedError()

    def get_metakeys(self, name):
        """
        Return the complete set of page's (non-link) meta keys, plus gwiki category.
        """
        raise NotImplementedError()
 
    def get_out(self, pagename):
        raise NotImplementedError()

    def get_meta(self, pagename):
        raise NotImplementedError()

    def get_in(self, pagename):
        return self.getpage(pagename).get(u'in', {})
       
    def get_out(self, pagename):
        return self.getpage(pagename).get(u'out', {})

    def post_save(self, pagename):
        pass

    def get_vals_on_keys(self):
        self.reverse_meta()
        return self.vals_on_keys

    def clear_metas(self):
        pass

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



