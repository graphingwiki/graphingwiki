"""
    Incremental SetMeta for multi-page updates (prototype).

    @copyright: 2008 by Joachim Viide
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import xmlrpclib

from MoinMoin.formatter.text_plain import Formatter as TextFormatter
from graphingwiki.editing import set_metas
from graphingwiki.patterns import filter_categories

def execute(xmlrpcobj, cleared, discarded, added, query="", handle=None):
    request = xmlrpcobj.request
    request.formatter = TextFormatter(request)

    # Using the same access controls as in MoinMoin's xmlrpc_putPage
    # as defined in MoinMoin/wikirpc.py
    if request.cfg.xmlrpc_putpage_trusted_only and not request.user.trusted:
        message = "You are not allowed to edit pages by XML-RPC"
        return xmlrpclib.Fault(1, request.getText(message))

    return set_metas(request, cleared, discarded, added)
