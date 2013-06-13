# -*- coding: utf-8 -*-"

import re

try:
    import simplejson as json
except ImportError:
    import json

def execute(pagename, request):
    request.content_type = "application/json"

    sid = request.session.sid
    user = request.user.name.replace("@", "%")
    if hasattr(request.cfg, "collab_chat_domain"):
        domain = request.cfg.collab_chat_domain
    else:
        domain = re.sub(r"^www\.", "", request.host)

    if sid and user and domain:
        data = {
            "jid": "%s@%s" % (user, domain),
            "password": sid,
        }
    else:
        data = {}

    json.dump(data, request)
