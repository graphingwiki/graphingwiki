define([
    "./EventSource"
], function(
    EventSource
) {
    "use strict";

    var Notification = function(timeout) {

        this._tabs = [];
        this._natives = [];
        this._defaultTitle = null;

        this._boundDestroy = this.destroy.bind(this);
        window.addEventListener("unload", this._boundDestroy);
        window.addEventListener("beforeunload", this._boundDestroy);
    };

    Notification.prototype = new EventSource(this);

    Notification.prototype.native = function(msg, options) {

        if (!('Notification' in window) || window.Notification.permission !== 'granted') {
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
                "body": options.body || ""
            };

            tabn.intervalID = window.setInterval(this._tabUpdate.bind(this), tabn.interval);
            this._tabs.push(tabn);
    };


    Notification.prototype.checkPermission = function() {
        if (!("Notification" in window)) {
            return;
        }

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
        }else{
            document.title = this._defaultTitle;
        }

        this._tabs.push(tabn);
    };


    Notification.prototype.clear = function(tag) {

        this._natives.forEach(function(notification) {
            if (notification.tag === tag) {
                notification.close();
            }
        });

        this._tabs = this._tabs.filter(function(tab){
            if (tab.tag === tag) {
                clearInterval(tab.intervalID);
                return false;
            }else{
                return true;
            }
        });

        if (this._tabs.length === 0) {
            document.title = this._defaultTitle;
        }
    };


    Notification.prototype.clearAll = function() {

        this._natives.forEach(function(notification) {
            notification.close();
        });

        this._natives = [];

        if (this._tabs.length !== 0) {
            this._tabs.forEach(function(tab){
                clearInterval(tab.intervalID);
            });

            this._tabs = [];
            document.title = this._defaultTitle;
        }
    };


    Notification.prototype.destroy = function() {
        this.clearAll();
        window.removeEventListener("unload", this._boundDestroy);
        window.removeEventListener("beforeunload", this._boundDestroy);
    };


    return Notification;
});
