define(function() {
    var keys = Object.keys;

    var createListener = function(target, listeners, useCapture) {
        keys(listeners).forEach(function(key) {
            target.addEventListener(key, listeners[key], useCapture);
        });

        return {
            "_target": target,
            "_listeners": listeners,
            "_useCapture": useCapture,

            "destroy": function() {
                var target = this._target;
                var listeners = this._listeners;
                if (target === null || listeners === null) {
                    return;
                }

                this._target = null;
                this._listeners = null;
                keys(listeners).forEach(function(key) {
                    target.removeEventListener(key, listeners[key], this._useCapture);
                });
            }
        };
    };

    return {
        "listen": function(target, type, _func, _useCapture) {
            var listeners = {};
            var useCapture = false;

            if (typeof type === "string") {
                listeners[type] = _func;
                useCapture = Boolean(_useCapture);
            } else {
                keys(type).forEach(function(key) {
                    listeners[key] = type[key];
                });
                useCapture = Boolean(_func);
            }
            return createListener(target, listeners, useCapture);
        },

        "eventOffset": function(event, _element) {
            var element = _element || event.currentTarget;

            var rect = element.getBoundingClientRect();
            var x = ((event.clientX - rect.left) / rect.width) * element.clientWidth;
            var y = ((event.clientY - rect.top) / rect.height) * element.clientHeight;
            return {
                "x": x,
                "y": y
            };
        },

        "preventWheelGestures": function(event, _element) {
            var element = _element || event.currentTarget;

            var deltaX = 0;
            var deltaY = 0;
            if (event.type === "mousewheel") {
                deltaX = -(event.wheelDeltaX || 0);
                deltaY = -(event.wheelDeltaY || (deltaX === 0 ? event.wheelDelta : 0)) || 0;
            } else if (event.type === "wheel") {
                deltaX = event.deltaX;
                deltaY = event.deltaY;
            }

            var left = element.scrollLeft;
            var ignoreX =
                (deltaX === 0) ||
                (deltaX > 0 && left >= element.scrollWidth - element.clientWidth) ||
                (deltaX < 0 && left <= 0);

            var top = element.scrollTop;
            var ignoreY =
                (deltaY === 0) ||
                (deltaY > 0 && top >= element.scrollHeight - element.clientHeight) ||
                (deltaY < 0 && top <= 0);

            // Workaround: In Chrome 31 scrollWidth - clientWidth may be 1 larger than
            // what scrollLeft can become. This can happen e.g. when the actual unrounded
            // clientWidth is fractional but gets rounded downward.
            // When we suspect such a thing might be happening we force vertical scrollbar to the
            // rightmost side (and hope that the user doesn't get bothered by it too much).
            if (!ignoreX && deltaX > 0 && left === element.scrollWidth - element.clientWidth - 1) {
                element.scrollLeft += 1;
                ignoreX = true;
            }
            // Same applies to scrollHeight - clientHeight and scrollTop.
            if (!ignoreY && deltaY > 0 && top === element.scrollHeight - element.clientHeight - 1) {
                element.scrollTop += 1;
                ignoreY = true;
            }

            if (ignoreX && ignoreY) {
                event.stopPropagation();
                event.preventDefault();
                return false;
            }
            return true;
        }
    };
});
