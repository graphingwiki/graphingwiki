define([
    "./EventSource",
], function(
    EventSource
) {
    "use strict";


    var Notification = function(timeout) {

        this._tabs = [];
        this._natives = [];
        this._tabTitle = null;
        this._defaultTitle = null;

        window.addEventListener("beforeunload", this.destroy.bind(this));
        window.addEventListener("unload", this.destroy.bind(this));
    };


    Notification.prototype = new EventSource(this);


    Notification.prototype.native = function(msg, options) {
        if (window.Notification.permission !== 'granted') {
            return;
        }

        if (!('Notification' in window)) {
            console.log("Native notifications are not supported by this browser.");
            return;
        }

        var opts = options || {};
        var notification = new window.Notification(msg, opts);
        this._natives.push(notification);
    };


    Notification.prototype.tab = function(msg, options, timeout) {

            if (this._tabs.length > 0 || typeof msg === 'undefined') {
                return;
            }

            if (this._defaultTitle === null) {
                this._defaultTitle = document.title;
            }

            var tabn = {
                "msg": msg,
                "interval": timeout || 1000,
                "tag": options.tag || null,
                "body": options.body || "",
            };

            tabn.intervalID = window.setInterval(this._tabUpdate.bind(this), tabn.interval);
            this._tabs.push(tabn);
    };


    Notification.prototype.checkPermission = function() {

        if (window.Notification.permission !== 'denied') {
            window.Notification.requestPermission(function(perm) {
                if (!('permission' in window.Notification)) {
                    window.Notification.permission = perm;
                }
                this.trigger("notificationPermission", window.Notification.permission);
                return;
            }.bind(this));
        }
        this.trigger("notificationPermission", window.Notification.permission);
    };


    Notification.prototype._tabUpdate = function() {

        if (this._tabs.length < 1) {
            return;
        }

        var tabn = this._tabs.shift();
        var title = tabn.msg + tabn.body;

        if (document.title !== title) {
            document.title = title;
            this._tabs.push(tabn);
            return;
        }

        document.title = this._defaultTitle;
        this._tabs.push(tabn);
    };


    Notification.prototype.clear = function(tag) {

        if (this._natives.length !== 0) {
            this._natives.forEach(function(notification) {
                if (notification.tag === tag) {
                    notification.close();
                }
            });
        }

        if (this._tabs.length !== 0) {
            for (var i in this._tabs) {
                if (this._tabs[i].tag === tag) {
                    window.clearInterval(this._tabs[i].intervalID);
                    this._tabs.splice(i, 1);
                    i--;
                }
            }

            if (this._tabs.length === 0) {
                document.title = this._defaultTitle;
            }
        }
    };


    Notification.prototype.clearAll = function() {

        if (this._natives.length === 0 && this._tabs.length === 0) {
            return;
        }

        if (this._natives.length !== 0) {
            this._natives.forEach(function(notification) {
                notification.close();
            });
        }

        if (this._tabs.length !== 0) {
            this._tabs = [];
            window.clearInterval(this._intervalID);
            document.title = this._defaultTitle;
        }
    };


    Notification.prototype.destroy = function() {

        this.clearAll();
        this._natives = null;
        this._tabs = null;
        this._tabTitle = null;

        window.removeEventListener("beforeunload", this.destroy, false);
        window.removeEventListener("unload", this.destroy, false);
    };


    return Notification;
});
