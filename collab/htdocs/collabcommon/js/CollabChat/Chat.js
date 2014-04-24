define([
    "collabcommon/CollabChat/Connection",
    "collabcommon/CollabChat/UI",
    "collabcommon/common/Notification"
], function(
    Connection,
    UI,
    Notification
) {
    "use strict";

    return function(container, boshUri, roomJid, jid, password) {

        var main = function(container) {
            var ui = new UI(container);
            var conn = new Connection(boshUri, roomJid, jid, password);
            var notification = new Notification();
            var visible = false;
            var showNotifications = true;
            var newMessageNotification = null;

            if (window.Notification.permission !== 'granted') {
                showNotifications = false;
            }

            ui.setNotificationStatus(showNotifications);
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

            ui.listen("notificationPermissionChange", function() {

                if (showNotifications === false) {
                    notification.checkPermission();
                }

                showNotifications = showNotifications ? false : true;
                ui.setNotificationStatus(showNotifications);
            });

            ui.listen("chatvisibilitychange", function(isVisible) {
                if (visible === isVisible) {
                    return;
                }

                visible = isVisible;

                if (visible) {
                    newMessageNotification = null;
                    notification.clear("CollabChatNotification");
                }
            });

            conn.listen("message", function() {
                if (visible) {
                    newMessageNotification = null;
                    notification.clear("CollabChatNotification");
                    return;
                }

                if (showNotifications !== true) {
                    return;
                }

                var opts = {
                    "tag": "CollabChatNotification",
                    "body": "New message"
                };

                notification.tab("CollabChat: " + roomJid, opts, 1000);

                if (newMessageNotification === null) {
                    notification.native("CollabChat: " + roomJid, opts);
                }
            }.bind(this));
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
