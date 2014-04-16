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

            if (window.Notification.permission !== 'granted') {
                showNotifications = false;
            }

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

                if (!showNotifications) {
                    notification.checkPermission();
                }

                showNotifications = showNotifications ? false : true;
                ui.setNotificationStatus(showNotifications);
            });

            notification.listen("notificationPermission", function(perm) {
                showNotifications = (perm === 'granted') ? true : false;
                ui.setNotificationStatus(showNotifications);
            });

            ui.listen("chatvisibilitychange", function(isVisible) {
                visible = isVisible;
                if (visible) {
                    notification.clear();
                }
            });

            conn.listen("message", function() {
                if (visible) {
                    notification.clear();
                    return;
                }

                if (showNotifications !== true) {
                    return;
                }

                notification.tab("Chat: New message", 1000);

                notification.native("CollabChat: " + roomJid, {
                    "tag": "CollabChatNotification",
                    "body": "New message"
                });

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
