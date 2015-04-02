"""
    Incremental SetMeta for multi-page updates (prototype).

    @copyright: 2008 by Joachim Viide
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from graphingwiki.editing import set_metas

def execute(xmlrpcobj, cleared, discarded, added):
    request = xmlrpcobj.request
    return set_metas(request, cleared, discarded, added, lazypage=True)
