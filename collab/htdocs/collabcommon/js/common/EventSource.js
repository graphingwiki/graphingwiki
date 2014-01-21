define(function() {
    var _has = Object.prototype.hasOwnProperty;
    var _slice = Array.prototype.slice;

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
});
