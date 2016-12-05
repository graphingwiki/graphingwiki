import MoinMoin.web
from werkzeug.datastructures import CombinedMultiDict, MultiDict

from MoinMoin.action.fullsearch import execute as fs_execute

from MetaSearch import execute as ms_execute
from graphingwiki import values_to_form

def execute(pagename, request):
    if 'metasearch' in request.values: 
        form = values_to_form(request.values)
        form['action'] = [u'MetaSearch']
        val = form.get('value', [''])
        form['q'] = val
        request.values = CombinedMultiDict([MultiDict(form)])
        return ms_execute(pagename, request)

    return fs_execute(pagename, request)
