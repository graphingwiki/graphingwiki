try:
    import json
except ImportError:
    import simplejson as json
import random

SCRIPT = """
<script>

requirejs([
        "collabcommon/CollabChat/Chat",
    ], function(Chat) {

    var request = new XMLHttpRequest();

    request.open("post", %(creds)s, true);

    request.onload = function(event) {
        if (request.status !== 200) {
            alert("CollabChat: Connecting to XMPP server failed: " + request.statusText);
            return;
        }

        if (request.response === null) {
            alert("CollabChat: Request failed: Empty response from server. Request status: " + request.statusText);
            return;
        }

        try {
            creds = JSON.parse(request.responseText);
        } catch(err) {
            alert("CollabChat: Parsing JSON response failed: " + err.message);
            return;
        }

        new Chat(%(id)s, %(bosh)s, %(room)s, creds.jid, creds.password);
    }

    request.onerror = function(event) {
        alert("CollabChat: Request failed: " + request.statusText);
        return;
    }

    request.ontimeout = function(event) {
        alert("CollabChat: Connection timed out: " + request.statusText);
        request.abort();
    }

    request.onabort = function(event) {
        console.log("CollabChat: Connection cancelled: " + request.statusText);
        return;
    }

    request.timeout = 30000;

    request.send();
});

</script>
"""

def macro_CollabChat(self, args):
    room = [self.request.cfg.interwikiname]
    room_mask = [maskable.lower() for maskable in getattr(self.request.cfg, "collab_chat_room_mask", [])]
    subroom_id = self.request.page.page_name.lower()

    if subroom_id:
        subroom_id = [".".join(subroom_id.replace(".", "").split("/"))]
        subrooms = set(subroom_id) - set(room_mask)
        room.extend(subrooms)

    bosh = self.request.cfg.collab_chat_bosh
    creds = self.request.cfg.collab_chat_creds

    id = "chat-%x" % random.randint(2 ** 63, 2 ** 64 - 1)

    html = list()
    html.append(self.formatter.div(1, **{"id": id, "class": "collab_chat"}))
    html.append(self.formatter.div(0))

    script = SCRIPT % { 
        "id": json.dumps(id), 
        "bosh": json.dumps(bosh), 
        "creds": json.dumps(creds), 
        "room": json.dumps(".".join(room))
    }

    html.append(script)

    return "".join(html)

