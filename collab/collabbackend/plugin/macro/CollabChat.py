import random

SCRIPT = """
<script>

requirejs([
        "collabcommon/js/CollabChat/Chat",
    ], function(Chat) {

    var request = new Request.JSON({
        "url": "%(creds)s",

        "onSuccess": function(creds) {
            new Chat("%(id)s", "%(bosh)s", "%(room)s", creds.jid, creds.password);
        },

        "onFailure": function() {
            alert("JSON request failed.");
        }
    });

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

    script = SCRIPT % {  "id": id, "bosh": bosh, "creds": creds, "room": ".".join(room) }

    html.append(script)

    return "".join(html)

