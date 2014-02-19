define([
    "collabcommon/common/Dict",
    "collabcommon/common/EventSource",
    "collabcommon/common/Strophe",
], function(
    Dict, 
    EventSource
) {
    "use strict";

    var getRoomJid = function(roomName, baseJid) {
        var node = Strophe.getNodeFromJid(roomName);
        if (node !== null) {
            return roomName;
        }
        var domain = Strophe.getDomainFromJid(baseJid);
        return roomName + "@conference." + domain;
    };

    var getText = function(element) {
        if (element.textContent !== void 0) {
            return element.textContent;
        }
        return element.innerText;
    };

    var iterChildren = function(element, func, context) {
        var children = element.childNodes;

        for (var i = 0, child = null; child = children[i]; i++) {
            if (func.call(context, child, i) === false) break;
        }
    };

    var listenEvent = function(obj, type, callback) {
        if (obj.addEventListener && obj.removeEventListener) {
            obj.addEventListener(type, callback, false);
            return {
                unlisten: function() {
                    obj.removeEventListener(type, callback, false);
                }
            };
        }

        if (obj.attachEvent && obj.detachEvent) {
            var wrapped = function() {
                callback(window.event);
            };
            obj.attachEvent("on" + type, wrapped);
            return {
                unlisten: function() {
                    obj.detachEvent("on" + type, wrapped);
                }
            };
        }
    };

    var now = Date.now || function() {
    return (new Date()).getTime();
    };

    var rex = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.?(\d*)Z$/;

    var parseDelay = function(stanza) {
    var timestamp = null;

        iterChildren(stanza, function(child) {
        if (!child.tagName) return;
        if (child.tagName.toLowerCase() !== "delay") return;
        if (child.getAttribute("xmlns") !== "urn:xmpp:delay") return;

        var stamp = child.getAttribute("stamp");
        if (stamp === null) return;

        var newStamp = stamp.match(rex);
        if (newStamp === null) return;

            var fraction = newStamp.pop();

        newStamp.shift();
        newStamp[1] -= 1;
        timestamp = Date.UTC.apply(null, newStamp);

        if (fraction) {
            timestamp += 1000 * Number("0." + fraction);
        }
    });

    return timestamp === null ? now() : timestamp;
    };

    var bound = function(method, context) {
        return function() {
            return method.apply(context, arguments);
        };
    };

    var Connection = function(boshUri, roomJid, jid, password) {

        this.roomJid = getRoomJid(roomJid, jid);
        this.jid = jid;
        this.password = password;

        this.strophe = new Strophe.Connection(boshUri);
        this.strophe.connect(jid, password,
                             bound(this._statusChanged, this));

        this.participants = new Dict();

        this.queue = [];
        this.timeout = null;

        // Uncomment the following lines for debug logging
        //Strophe.log = function(level, msg) { log("debug", msg); };
        //this.strophe.xmlOutput = function(xml) { log(">", xml); };
        //this.strophe.xmlInput = function(xml) { log(">", xml); };

        var cleanup = bound(function() {
            this.strophe.disconnect();
            for (var i = 0, len = listeners.length; i < len; i++) {
                listeners[i].unlisten();
            }
        }, this);

        var listeners = [
            listenEvent(window, "beforeunload", cleanup),
            listenEvent(window, "unload", cleanup)
        ];
    };

    Connection.prototype = new EventSource(this);

    Connection.prototype._addToQueue = function(timestamp, sender, text) {
        if (this.timeout === null) {
            this.timeout = setTimeout(bound(this._flushQueue, this), 0);
        }
        this.queue.push({
            timestamp: timestamp,
            sender: sender,
            text: text
        });
    };

    Connection.prototype._flushQueue = function() {
        this.timeout = null;
        this.queue.sort(function(x, y) {
            return x.timestamp - y.timestamp;
        });

        for (var i = 0, len = this.queue.length; i < len; i++) {
            var obj = this.queue[i];
            this.trigger("message", obj.timestamp, obj.sender, obj.text);
        }
        this.queue = [];
    };

    Connection.prototype.send = function(message) {
        var msg = $msg({
                to: this.roomJid,
                type: "groupchat"
            });

        msg.c("body").t(message);
        this.strophe.send(msg.tree());
    };

    Connection.prototype._connected = function() {
        this.strophe.addHandler(bound(this._handleMessage, this),
                                null, "message", null, null,
                    this.roomJid, { matchBare: true });

        this.strophe.addHandler(bound(this._handlePresence, this),
                                null, "presence", null, null,
                    this.roomJid, { matchBare: true });

        var resource = Strophe.getNodeFromJid(this.jid);
        resource = resource + "-" + ((999 * Math.random()) | 0);

        var presence = $pres({
            to: this.roomJid + "/" + resource
        });
        presence.c("x", {
            xmlns: "http://jabber.org/protocol/muc"
        });
        this.strophe.send(presence);

        this.trigger("connected");
    };

    Connection.prototype._disconnected = function() {
        this.trigger("disconnected");
    };

    Connection.prototype._handleMessage = function(msg) {
        var from = msg.getAttribute("from");
        var sender = Strophe.getResourceFromJid(from);

        iterChildren(msg, function(child) {
            if (child.tagName && child.tagName.toLowerCase() === "body") {
                var timestamp = parseDelay(msg);
                this._addToQueue(timestamp, sender, getText(child));
                return false;
            }
        }, this);

        return true;
    };

    Connection.prototype._handlePresence = function(pres) {
        var type = pres.getAttribute("type");

        var from = pres.getAttribute("from");
        var sender = Strophe.getResourceFromJid(from);

        if (type !== "unavailable" && this.participants.contains(from)) {
            return;
        }

        var msg = "";
        if (type === "unavailable") {
            msg = "has left the room";
            this.participants.pop(from);
            this.trigger("participantLeave", sender);
        } else {
            msg = "has entered the room";
            this.participants.set(from, true);
            this.trigger("participantJoin", sender, true);
        }
        this.trigger("message", now(), null, sender + " " + msg);

        return true;
    };

    Connection.prototype._setStatus = function(isError, status) {
        this.status = status;
        this.trigger("statusChanged", isError, status);
    };

    Connection.prototype._statusChanged = function(status) {
        if (status == Strophe.Status.CONNECTING) {
            this._setStatus(false, "Connecting");
        } else if (status == Strophe.Status.CONNFAIL) {
            this._setStatus(true, "Connection failed");
            this.strophe.disconnect();
        } else if (status == Strophe.Status.AUTHENTICATING) {
            this._setStatus(false, "Authenticating");
        } else if (status == Strophe.Status.AUTHFAIL) {
            this._setStatus(true, "Authentication failed");
            this.strophe.disconnect();
        } else if (status == Strophe.Status.DISCONNECTING) {
            this._setStatus(false, "Disconnecting");
        } else if (status == Strophe.Status.DISCONNECTED) {
            this._setStatus(false, "Disconnected");
            this._disconnected();
        } else if (status == Strophe.Status.CONNECTED) {
            this._setStatus(false, "Connected");
            this._connected();
        }
    };

    return Connection;
});