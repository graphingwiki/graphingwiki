# -*- coding: utf-8 -*-"
"""
    Invite macro plugin
    - wraps Invite action to easily configurable macro 
    @copyright: 2012 by Lauri Pokka <larpo@clarifiednetworks.com>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from graphingwiki.plugin.action.Invite import *
from MoinMoin import wikiutil
import re

def execute(macro, args):
    request = macro.request
    opts = re.findall("\s*([^,]+)\s*=\s*([^,]+)\s*", args)
    optargs = dict()
    for opt in opts:
        key = str(opt[0])
        if key not in optargs:
            optargs[key] = list()

        if ";" in opt[1]:
            optargs[key].append([x.strip() for x in opt[1].split(';')])
        else:
            optargs[key].append(opt[1].strip())


    inv = Invite(request.page.page_name, request, **optargs)
    out = u'<div class="invite">' + inv.make_form().render() + u'</div>'
    out = re.sub(r'<input [^>]*name="cancel"[^>]+>', '', out)
    ticket = wikiutil.createTicket(request, action="Invite")
    return re.sub('(name="ticket" value=")[^"]*"', r'\g<1>' +ticket+ '"',  out)
