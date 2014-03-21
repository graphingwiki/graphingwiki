Dependencies = ['myfilesystem']

try:
    import simplejson as json
except ImportError:
    import json

from collabbackend import listCollabs


def execute(pagename, request):
    request.content_type = "application/json"
    user = request.user.name
    active = request.cfg.interwikiname
    path = request.cfg.collab_basedir
    baseurl = request.cfg.collab_baseurl

    collabs = listCollabs(baseurl, user, path, active)
    results = []
    for collab in collabs:
        results.append({
            "shortName": collab[0],
            "title": collab[1],
            "motd": collab[2],
            "url": collab[3],
            "active": collab[4]
        })

    json.dump(results, request, indent=2)
    return
