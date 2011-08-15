# -*- coding: utf-8 -*-"
"""
    newpage action to MoinMoin/Graphingwiki
     - Extends the original MoinMoin action

    @copyright: 2008 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from copy import copy
from MoinMoin.action.newpage import NewPage
from MoinMoin import log

def execute(pagename, request):
    form = request.values.to_dict(flat=False)

    # Editaction allows for arbitrary action to be used for editing target page
    editaction = form.get('editfunc', [''])[0]
    # Edit actions assumed to be all in lower case
    editaction = editaction.lower()

    if editaction:
        # MoinMoin.action.newpage left no choice but to edit the URL
        # action on-the-fly in request.http_redirect
        request.http_redirect_real = request.http_redirect
        
        def redirect_editaction(url):
            url = url.replace('action=edit', 'action=%s' % editaction)
            request.http_redirect_real(url)

        request.http_redirect = redirect_editaction

    return NewPage(request, pagename).render()
