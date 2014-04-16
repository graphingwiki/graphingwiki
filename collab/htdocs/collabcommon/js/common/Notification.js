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
        if (window.Notification.permission !== 'granted' ||
            this._natives.length > 0) {
            return;
        }

        var opts = options || {};

        if (!('Notification' in window)) {
            console.log("Native notifications are not supported by this browser.");
            return;
        }

        var notification = new window.Notification(msg, options);

        notification.onclose = function() {
            this._natives = [];
        }.bind(this);

        this._natives.push(notification);
    };


    Notification.prototype.clear = function() {

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


    Notification.prototype.tab = function(msg, timeout) {

            if (this._tabs.length > 0 || typeof msg === 'undefined') {
                return;
            }

            this._interval = timeout || 1000;

            if (this._defaultTitle === null) {
                this._defaultTitle = document.title;
            }

            this._tabTitle = msg;
            this._intervalID = window.setInterval(this._tabUpdate.bind(this), this._interval);
            this._tabs.push(this._intervalID);
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
        if (document.title !== this._tabTitle) {
            document.title = this._tabTitle;
            return;
        }

        document.title = this._defaultTitle;
    };


    Notification.prototype.destroy = function() {

        this.clear();
        this._natives = null;
        this._tabs = null;
        this._tabTitle = null;

        window.removeEventListener("beforeunload", this.destroy, false);
        window.removeEventListener("unload", this.destroy, false);
    };


    return Notification;
});
