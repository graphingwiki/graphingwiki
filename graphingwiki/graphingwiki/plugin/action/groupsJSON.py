# -*- coding: utf-8 -*-"
"""
    groupsJSON action plugin for MoinMoin/Graphingwiki
     - group editing and listing backend for GroupEditor.js

    @copyright: 2014 by Lauri Pokka larpo@clarifiednetworks.com
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

try:
    import simplejson as json
except ImportError:
    import json

from graphingwiki.groups import GroupException, group_add, group_rename, group_del
from MoinMoin.datastruct.backends.wiki_groups import WikiGroup


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, WikiGroup):
            return obj.name

        return json.JSONEncoder.default(self, obj)


def execute(pagename, request):
    _ = request.getText

    request.content_type = "application/json"

    if request.environ['REQUEST_METHOD'] == "GET":
        groups = {}
        for group in request.groups:
            members = request.groups[group].members
            grps = request.groups[group].member_groups
            groups[group] = dict(members=members, groups=grps)

        json.dump(groups, request, cls=SetEncoder)
        return

    elif request.environ['REQUEST_METHOD'] == 'POST':
        try:
            indata = request.read()
            if not indata:
                raise ValueError("No data")

            indata = json.loads(indata)

            for row in indata:
                op = row.get('op', None)
                group = row.get('group', None)
                name = row.get('name', None)

                if op == "rename":
                    group_rename(request, group, [name, row.get('to')])
                elif op == "del":
                    group_del(request, group, [name])
                elif op == "add":
                    group_add(request, group, [name], row.get('create', False))
                else:
                    raise ValueError("Bad operation")

        except (GroupException, ValueError) as e:
            request.status_code = 400
            request.write(e.message)

        except NotImplementedError as e:
            request.status_code = 501
            request.write(e.message)

        except Exception as e:
            request.status_code = 500
            request.write(e.message)


    else:
        #405 Method Not Allowed
        request.status_code = 405

    return