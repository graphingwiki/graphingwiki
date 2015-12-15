import UserDict

class GraphDataBase(UserDict.DictMixin):
    # Does this backend promise that operations provided by
    # this API are ACID and commit/abort work?

    is_acid = False

    def __init__(self, request, **kw):
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

    def get_vals_on_pages(self):
        self.reverse_meta()
        return self.vals_on_pages

    def clear_page(self, pagename):
        raise NotImplementedError()

    def clear_metas(self):
        pass

    def __repr__(self):
        return "<%s instance %x>" % (str(self.__class__), id(self))

    def reverse_meta(self):
        if hasattr(self, 'keys_on_pages'):
            return
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
