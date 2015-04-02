from graphingwiki.util import category_regex

def doctest_request(graphdata=dict(), mayRead=True, mayWrite=True):
    class Request(object):
        pass

    class Config(object):
        pass

    class Object(object):
        pass

    class Cache(object):
        pass

    class GraphData(dict):
        def getpage(self, page):
            return self.get(page, dict())
    
    request = Request()
    request.cfg = Config()
    request.cfg.cache = Cache()
    request.cfg.cache.page_category_regex = category_regex(request)
    request.cfg.cache.page_category_regexact = category_regex(request, act=True)
    request.graphdata = GraphData(graphdata)

    request.user = Object()
    request.user.may = Object()
    request.user.may.read = lambda x: mayRead
    request.user.may.write = lambda x: mayWrite

    return request
