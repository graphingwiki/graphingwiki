define([
    "collabcommon/CollabChat/Connection",
    "collabcommon/CollabChat/UI"
], function(
    Connection,
    UI)
{
    "use strict";

    return function(container, boshUri, roomJid, jid, password) {
        var main = function(container) {
            var ui = new UI(container);

            var conn = new Connection(boshUri, roomJid, jid, password);

            ui.setChannelLabel(roomJid);

            conn.listen("statusChanged", function(isError, status) {
                ui.connectionStatusChanged(status);
            });

            conn.listen("connected", function() {
                var listener = ui.listen("output", conn.send, conn);
                conn.listen("disconnected", listener.unlisten);
                conn.listen("disconnected", ui.onDisconnect, ui);
            });
            conn.listen("message", ui.addMessage, ui);

            conn.listen("participantJoin", ui.userJoin, ui);
            conn.listen("participantLeave", ui.userLeave, ui);
        };

        var check = function() {
            if ((typeof container) === "string") {
                if (document.readyState === "complete") {
                    main(document.getElementById(container));
                } else {
                    setTimeout(check, 25);
                }
            } else {
                main(container);
            }
        };
        check();
    };
});
