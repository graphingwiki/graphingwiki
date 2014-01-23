define(function() {
    "use strict";

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
});