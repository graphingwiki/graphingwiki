import string
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

def execute(self, args):
    room = self.request.cfg.interwikiname
    bosh = self.request.cfg.collab_chat_bosh
    creds = self.request.cfg.collab_chat_creds

    id = "".join([random.choice(string.letters) for _ in range(32)])

    result = list()
    result.append(self.formatter.div(1, **{ "id": id, "class": "collab_chat" }))
    result.append(self.formatter.div(0))

    script = SCRIPT % { "bosh": bosh, "room": room, "creds": creds, "id": id }
    result.append(script)

    return "".join(result)
