var initChat = (function() {
    "use strict";

    var log = function() {
        if (window.console && console.log) {
            console.log.apply(console, arguments);
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

    var EventSource = (function() {
        var _has = Object.prototype.hasOwnProperty;
        var _slice = Array.prototype.slice;

        var EventSource = function() {};

        EventSource.prototype._callbacks = null;

        EventSource.prototype.trigger = function(type) {
            var callbacks = this._callbacks;
            if (!callbacks || !_has.call(callbacks, type)) return;

            var args = _slice.call(arguments, 1, arguments.length);
            var list = callbacks[type];
            list = _slice.call(list, 0, list.length);

            for (var i = 0, len = list.length; i < len; i++) {
                var obj = list[i];

                var callback = obj.callback;
                if (callback) {
                    callback.apply(obj.context, args);
                }
            }
        };

        EventSource.prototype.listen = function(type, callback, context) {
            var callbacks = this._callbacks;
            if (!callbacks) {
                this._callbacks = callbacks = {};
            }
            if (!_has.call(callbacks, type)) {
                callbacks[type] = [];
            }

            var list = callbacks[type];
            var obj = {
                callback: callback,
                context: context
            };
            list.push(obj);

            return {
                unlisten: function() {
                    obj.callback = null;
                    obj.context = null;

                    for (var i = list.length-1; i >= 0; i--) {
                        if (list[i] === obj) list.splice(i, 1);
                    }

                    if ((list.length === 0) && (callbacks[type] === list)) {
                        delete callbacks[type];
                    }
                }
            };
        };

        return EventSource;
    })();

    var Dict = (function() {
        var _has = Object.prototype.hasOwnProperty;

        var Dict = function(init) {
            var items = {};
            var count = 0;

            if (init) {
                for (var key in init) {
                    if (_has.call(init, key)) {
                        items[key] = init[key];
                        count += 1;
                    }
                }
            }

            this._items = items;
            this._count = count;
        };

        Dict.prototype.set = function(key, value) {
            var items = this._items;
            if (!_has.call(items, key)) {
                this._count += 1;
            }
            items[key] = value;
        };

        Dict.prototype.get = function(key, _default) {
            var items = this._items;
            if (_has.call(items, key)) {
                return items[key];
            }
            return arguments.length === 1 ? null : _default;
        };

        Dict.prototype.pop = function(key, _default) {
            var items = this._items;
            if (_has.call(items, key)) {
                this._count -= 1;

                var value = items[key];
                delete items[key];
                return value;
            }
            return arguments.length === 1 ? null : _default;
        };

        Dict.prototype.contains = function(key) {
            return _has.call(this._items, key);
        };

        Dict.prototype.forEach = function(func, ctx) {
            var items = this._items;
            for (var key in items) {
                if (_has.call(items, key)) {
                    func.call(ctx, items[key], key, this);
                }
            }
        };

        Dict.prototype.count = function() {
            return this._count;
        };

        return Dict;
    })();

    var UI = (function() {
        var pad = function(number, length) {
            number = "" + number;
            while (number.length < length) {
                number = "0" + number;
            }
            return number;
        };

        var formatTime = function(timestamp) {
            var dateObj = new Date(timestamp);
            return {
                time: (pad(dateObj.getHours(), 2) + ":" +
                       pad(dateObj.getMinutes(), 2)),
                date: (pad(dateObj.getFullYear(), 4) + "-" +
                       pad(dateObj.getMonth() + 1, 2) + "-" +
                       pad(dateObj.getDate(), 2))
            };
        };

        var linkRex = /https?:\/\/\S+/g;
        var linkify = function(text, linkAttributes) {
            var result = [];

            linkRex.lastIndex = 0;
            while (true) {
                var start = linkRex.lastIndex;
                var match = linkRex.exec(text);

                var end = match ? match.index : text.length;
                if (start < end) {
                    var bite = text.slice(start, end);
                    result.push(document.createTextNode(bite));
                }

                if (!match) {
                    break;
                }

                var a = document.createElement("a");
                a.href = match[0];
                a.rel = "noreferrer";
                a.target = "blank";
                a.appendChild(document.createTextNode(match[0]));
                result.push(a);
            }

            return result;
        };

        var lineRex = /\r\n|\r|\n/;
        var lineify = function(string) {
            var bites = string.split(lineRex);

            var result = [];
            result.push.apply(result, linkify(bites[0]));

            for (var i = 1, len = bites.length; i < len; i++) {
                result.push(document.createElement("br"));
                result.push.apply(result, linkify(bites[i]));
            }

            return result;
        };

        var hash = function(string) {
            // Return a value between 0.0 and 1.0 based on the input
            // string. This is an ad-hoc algorithm, implementing some
            // proper hash algorithm recommended.

            var result = 0x1337;

            for (var i = 0, len = string.length; i < len; i++) {
                var code = string.charCodeAt(i);
                result = (result ^ (code * code * 11 * 19)) & 0xffff;
            }

            return result / 0xffff;
        };

        var hsvFill = ["000000", "00000", "0000", "000", "00", "0", ""];
        var hsv = function(h, s, v) {
            // Hue (h), saturation (s) and value (v) should be values
            // between 0.0 and 1.0 (inclusive). Returns color in
            // format #RRGGBB.

            h = (h * 6) % 6;
            s = Math.max(Math.min(s, 1.0), 0.0);
            v = Math.max(Math.min(v, 1.0), 0.0);

            var max = v;
            var min = v * (1 - s);
            var mid = min + (max - min) * (1 - Math.abs(1 - h % 2));
            var maxMidMin = [max, mid, min, min, mid, max];

            var r = (255 * maxMidMin[((h + 0) % 6) | 0]) | 0;
            var g =  (255 * maxMidMin[((h + 4) % 6) | 0]) | 0;
            var b = (255 * maxMidMin[((h + 2) % 6) | 0]) | 0;

            var total = ((r << 16) + (g << 8) + b).toString(16);
            return "#" + hsvFill[total.length] + total;
        };

        var trim = function(string) {
            return string.match(/^\s*(.*?)\s*$/)[1];
        };

        var createElement = function(tag, className) {
            var element = document.createElement(tag);
            element.className = className;
            return element;
        };

        var appendText = function(element, text) {
            element.appendChild(document.createTextNode(text));
        };

        var UI = function(container) {

            var UserList = (function() {
                var UserList = function(){
                    this._container = createElement("div", "userlist");
                    this._list = createElement("ul", "users");
                    this._container.appendChild(this._list);
                };

                UserList.prototype.userJoin = function(key) {
                    var user = createElement("li", "user");
                    user.id = key;
                    user.textContent = key;
                    this._list.appendChild(user);
                };

                UserList.prototype.userLeave = function(key) {
                    var user = document.getElementById(key);
                    this._list.removeChild(user);
                };

                UserList.prototype.element = function() {
                    return this._container;
                };

                return UserList;
            })();

            this.container = container;

            this.tools = createElement("div", "toolbar");
            this.toolset = createElement("div", "toolset");
            this.channelLabel = createElement("span", "channel-label");
            this.connectionStatus = createElement("span", "connection-status");
            this.tools.appendChild(this.channelLabel);
            this.toolset.appendChild(this.connectionStatus);
            this.tools.appendChild(this.toolset);
            this.container.appendChild(this.tools);

            this.chatWrapper = createElement("div", "chat-wrapper");

            this.chat = createElement("div", "chat");
            this.chatWrapper.appendChild(this.chat);

            this.userlist = new UserList();
            this.chatWrapper.appendChild(this.userlist.element());
            this.container.appendChild(this.chatWrapper);

            this.area = createElement("div", "output");
            this.areaContainer = createElement("div", "output-container");
            this.areaContainer.appendChild(this.area);
            this.chat.appendChild(this.areaContainer);

            this.input = createElement("input", "input");
            this.input.placeholder = "<write your message here>";
            this.inputContainer = createElement("div", "input-container");
            this.inputContainer.appendChild(this.input);
            this.chat.appendChild(this.inputContainer);

            this.isAtBottom = true;
            this.previous = {};

            var _this = this;
            listenEvent(this.areaContainer, "scroll", function(event) {
                _this.isAtBottom = (this.scrollTop + this.clientHeight
                                    === this.scrollHeight);
            });
            listenEvent(window, "resize", function() {
                if (_this.isAtBottom) {
                    _this._scrollToBottom();
                }
            });
            listenEvent(this.input, "keypress", function(event) {
                if (event.keyCode !== 13) {
                    return true;
                }

                var text = trim(this.value);
                this.value = "";
                if (text) {
                    _this.trigger("output", text);
                }
                _this._scrollToBottom();
                return false;
            });
        };

        UI.prototype = new EventSource();

        UI.prototype.addMessage = function(timestamp, sender, body) {
            var formatted = formatTime(timestamp);
            var previous = this.previous;
            this.previous = formatted;

            var dateDiv = null;
            if (formatted.date !== previous.date) {
                var dateDiv = createElement("div", "message");
                var bodyDiv = createElement("div", "room-message");
                appendText(bodyDiv, "day changed to " + formatted.date);
                dateDiv.appendChild(bodyDiv);
            }

            var msgDiv = createElement("div", "message");

            if (sender !== null) {
                var hashed = hash(sender);
                var hue = hashed;
                var value = 0.97 + 0.03 * ((hashed * 1000) % 1.0);

                msgDiv.style.background = hsv(hue, 0.02, 0.98);

                var timeDiv = createElement("div", "time");
                appendText(timeDiv, formatted.time);
                msgDiv.appendChild(timeDiv);

                var senderDiv = createElement("div", "sender");
                senderDiv.style.color = hsv(hue, 0.35, 0.575);
                // Whitespaces around the sender make copy-pastes clearer.
                appendText(senderDiv, sender);
                msgDiv.appendChild(senderDiv);

                var bodyDiv = createElement("div", "body");
                bodyDiv.style.color = hsv(hue, 0.1, 0.3);

                var bites = lineify(body);
                for (var i = 0, len = bites.length; i < len; i++) {
                    bodyDiv.appendChild(bites[i]);
                }
                msgDiv.appendChild(bodyDiv);
            } else {
                var bodyDiv = createElement("div", "room-message");
                appendText(bodyDiv, body);
                msgDiv.appendChild(bodyDiv);
            }

            var wasAtBottom = this.isAtBottom;

            if (dateDiv) {
                this.area.appendChild(dateDiv);
            }
            this.area.appendChild(msgDiv);

            if (wasAtBottom) {
                this._scrollToBottom();
            }
        };

        UI.prototype._scrollToBottom = function() {
            this.areaContainer.scrollTop = this.areaContainer.scrollHeight;
        };

        UI.prototype.connectionStatusChanged = function(status) {
            this.connectionStatus.textContent = status.toLowerCase();
        };

        UI.prototype.userJoin = function(key, value) {
            this.userlist.userJoin(key);
        };

        UI.prototype.userLeave = function(key) {
            this.userlist.userLeave(key);
        };

        UI.prototype.setChannelLabel = function(label) {
            this.channelLabel.textContent = label;
        }

        return UI;
    })();

    var Connection = (function() {
        var getRoomJid = function(roomName, baseJid) {
            var node = Strophe.getNodeFromJid(roomName);
            if (node !== null) {
                return roomName;
            }
            var domain = Strophe.getDomainFromJid(baseJid);
            return roomName + "@conference." + domain;
        };

        var getText = function(element) {
            if (element.textContent != null) {
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

        var now = Date.now || function() {
        return (new Date()).getTime();
        };

        var rex = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.?(\d*)Z$/;

        var parseDelay = function(stanza) {
        var timestamp = null;

            iterChildren(stanza, function(child) {
            if (!child.tagName) return;;
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

        Connection.prototype = new EventSource();

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
            })
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

            if (type === "unavailable") {
                var msg = "has left the room";
                this.participants.pop(from);
                this.trigger("participantLeave", sender);
            } else {
                var msg = "has entered the room";
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
    })();

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
})();
