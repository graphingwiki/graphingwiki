import random

SCRIPT = """
<script>
(function() {
    var request = new Request.JSON({
        "url": "%(creds)s",

        "onSuccess": function(creds) {
            initChat("%(id)s", "%(bosh)s", "%(room)s", creds.jid, creds.password);
        },

        "onFailure": function() {
            alert("JSON request failed.");
        }
    });

    request.send();
})();
</script>
"""

def macro_CollabChat(self, args):
    room = [self.request.cfg.interwikiname]
    room_mask = [maskable.lower() for maskable in getattr(self.request.cfg, "collabchat_room_mask", [])]
    subroom_id = self.request.page.page_name.lower()

    if subroom_id:
        subroom_id = [".".join(subroom_id.replace(".", "").split("/"))]
        subrooms = set(subroom_id) - set(room_mask)
        room.extend(subrooms)

    bosh = self.request.cfg.collab_chat_bosh
    creds = self.request.cfg.collab_chat_creds

    id = "chat-%x" % random.randint(2 ** 63, 2 ** 64 - 1)

    result = list()
    result.append(self.formatter.div(1, **{ "id": id, "class": "collab_chat" }))
    result.append(self.formatter.div(0))

    script = SCRIPT % { "bosh": bosh, "room": ".".join(room), "creds": creds, "id": id }
    result.append(script)

    return "".join(result)

