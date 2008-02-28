# -*- coding: utf-8 -*-"
"""
    newpage action to MoinMoin/Graphingwiki
     - Extends the original MoinMoin action

    @copyright: 2008 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from copy import copy
from MoinMoin.action.newpage import NewPage

def execute(pagename, request):
    # Editaction allows for arbitrary action to be used for editing target page
    editaction = request.form.get('editfunc', [''])[0]
    # Edit actions assumed to be all in lower case
    editaction = editaction.lower()
    # Making a throwaway request by copying to avoid littering modifications
    newreq = copy(request)

    if editaction:
        # MoinMoin.action.newpage left no choice but to edit the URL
        # action on-the-fly in request.http_redirect
        newreq.http_redirect_real = newreq.http_redirect
        
        def redirect_editaction(url):
            url = url.replace('action=edit', 'action=%s' % editaction)
            newreq.http_redirect_real(url)

        newreq.http_redirect = redirect_editaction

    return NewPage(newreq, pagename).render()
