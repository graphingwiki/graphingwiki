/*
 gwiki-common.js
 - Collection of js functions and classes used by graphingwiki.
 License:	MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2011 by Lauri Pokka
 */

/* Add "enable js" cookie */
if (!Cookie.read('js')) {
    Cookie.write('js', true, {
        duration: 100 * 365,
        domain: window.location.hostname
    });
    window.location.reload();
}

window.GWIKISEPARATOR = '-gwikiseparator-';


window.addEvent('domready', function() {

    var src = $$('script[src$=gwiki-common.js]')[0].get('src').replace('js/gwiki-common.js', '');

    var loader = new GwikiImport(src);

    /* MetaFormEdit improvements */
    var fields = $$('.metaformedit');
    if (fields.length > 0) {
        loader.load('MetaFormEdit', function() {
            new MetaFormEdit(fields[0].getParent('form'));
        });
    }

    /* Apply MooTools tooltips to elements with .mt-tooltip class */
    var tooltips = new Tips('.mt-tooltip', {'className': 'mootip'});

    /* Apply MetaTable improvements */
    var tables = $$('.metatable table');
    if (tables.length > 0) {
        loader.load('MetaTable', function() {
            tables.each(function(tab, i) {

                new MetaTable(tab, {
                    tableArguments: MetaTableArguments[i],
                    separator: GWIKISEPARATOR
                });
            });
        });
    }

    if ($$('dl dt').length && $$('dl dd').length) {
        loader.load('InlineEditor', function() {
            $$('.gwikiinclude').include(document.body).each(initInlineMetaEdit)
        });
    }

    if ($$('.attachtree_area')) {
        loader.load('AttachTree', function() {
            $$('.attachtree_area').each(function(el) {
                new AttachTree(el);
            })
        });
    }
});

Element.Events.shiftclick = {
    base: 'click', // the base event type
    condition: function(event) { //a function to perform additional checks
        if (event.shift) {
            event.preventDefault();
            return true;
        }
    }
};

Request.SetMetas = new Class({
    Extends : Request.JSON,
    options: {
        //onConflict: function(){}
        method: 'post',
        checkUrl: "",
        checkData: {}
    },
    checkAndSend: function() {
        var args = arguments;
        new Request.JSON({
            url: this.options.checkUrl,
            method: 'post',
            onSuccess: function(json) {
                if (Object.every(this.options.checkData, function(metas, page) {
                    return json[page] && Object.every(metas, function(values, key) {
                        values = values.filter(function(v) {
                            return v != '';
                        });
                        if (!json[page][key]) json[page][key] = [];
                        return json[page][key].length == values.length
                            && values.every(function(value) {
                            return json[page][key].contains(value);
                        })
                    });
                }) || confirm("Data has changed after you loaded this page, do you want to overwrite changes?")) {
                    this.send(args);
                } else {
                    this.fireEvent('conflict')
                }
            }.bind(this)
        }).send();
    },

    onSuccess: function (json) {
        if (json.status == "ok") {
            this.fireEvent('complete', arguments).fireEvent('success', arguments).callChain();
        } else {
            if (json.msg && json.msg[0]) alert(json.msg[0]);
            else alert("Save failed for unknown reason.");
        }
    }
});

var unescapeId = function(id) {
    return id.split(/_([0-9a-f]{2})_/).map(
        function(s) {
            if (s.test(/^[0-9a-f]{2}$/)) {
                return String.fromCharCode(s.toInt(16));
            } else {
                return s;
            }
        }).join("")
};


var initInlineMetaEdit = function (base) {

    //do not attach inline edit if MetaFormEdit is running
    if (!base.getElement('dl') || base.getElement('dl').getParent('form')) return;

    var metas, editor, page = "";

    if (base.hasClass('gwikiinclude')) page = unescapeId(base.id).split(GWIKISEPARATOR)[0];

    base.addEvent('mouseover:relay(div:not(.gwikiinclude) dl):once', function() {
        new Request.JSON({
            url: '?action=getMetaJSON&args=' + page,
            onSuccess: function(json) {
                page = Object.keys(json)[0];
                metas = json[page];
                base.getElements('div:not(.gwikiinclude) dd').each(function(dd) {
                    if (dd.get('text').clean() == "") {
                        var dt = dd.getPrevious('dt');
                        if (!metas[getKey(dt)]) metas[getKey(dt)] = [];
                        metas[getKey(dt)].splice(getMetaIndex(dt), 0, "");
                    }
                });

            }
        }).get();
    });

    //add a '+' button for adding values to empty metas (foo::)
    base.getElements('div:not(.gwikiinclude) dd').each(function(dd) {
        if (dd.get('text').clean() == "") {

            var dt = dd.getPrevious('dt');

            dt.grab(new Element('a', {
                'class': 'jslink',
                'text': '+',
                'styles': {
                    'font-weight': 'bold',
                    'font-size': '1.1em',
                    'margin-left': '10px'
                },
                'events': {
                    'click': function() {
                        this.destroy();
                        dd.set('html', '&nbsp;');
                        editValue(dd);
                    }
                }
            }));

        }
    });

    var getKey = function(dt) {
        var tmp = dt.clone();
        tmp.getElements('a.jslink').destroy();
        return tmp.get('text');
    };

    var getMetaIndex = function(dt, values) {
        var key = getKey(dt);
        var dts = base.getElements('div:not(.gwikiinclude) dt').filter(
            function(dt) {
                return getKey(dt) == key;
            });

        return dts.indexOf(dt);
    };

    base.addEvent('shiftclick:relay(div:not(.gwikiinclude) dd:not(.edit))', function(event) {
        event.preventDefault();

        var dd = event.target;
        if (dd.get('tag') != "dd") dd = dd.getParent('dd');

        if (metas == null) editValue.delay(100, this, dd);
        else editValue(dd);
    });

    var editValue = function(dd) {
        var key = dd.getPrevious('dt').get('text');
        var index = getMetaIndex(dd.getPrevious('dt'), metas[key]);

        var oldValue = metas[key][index];

        if (editor) editor.cancel();

        dd.addClass('edit');

        editor = new InlineEditor(dd, {
            oldValue: oldValue,
            suggestionKey: key,
            inline: true,
            width: 40,
            onSave: function (newValue) {
                var args = {};
                args[page] = {};

                var vals = metas[key];
                args[page][key] = vals;
                var oldData = Object.clone(args);
                vals[index] = newValue;

                new Request.SetMetas({
                    data: 'action=setMetaJSON&args=' + encodeURIComponent(JSON.encode(args)),
                    checkUrl: '?action=getMetaJSON&args=' + page,
                    checkData: oldData,
                    onSuccess: function() {
                        editor.exit();
                        editor = null;
                    }.bind(this)
                }).checkAndSend();
            },
            onExit: function() {
                dd.removeClass('edit');
            }
        });
    };

    base.addEvent('shiftclick:relay(div:not(.gwikiinclude) dt:not(.edit))', function(event) {
        event.preventDefault();

        var dt = event.target;
        if (dt.get('tag') != "dt") dt = dt.getParent('dt');

        if (metas == null) editKey.delay(100, this, dt);
        else editKey(dt);
    });

    var editKey = function(dt) {
        var key = dt.get('text');
        var index = getMetaIndex(dt, metas[key]);

        if (!metas[key] || metas[key][index] == "") return;

        if (editor) editor.cancel();

        dt.addClass('edit');

        editor = new InlineEditor(dt, {
            oldValue: key,
            inline: true,
            onSave: function (newKey) {
                var args = {};
                args[page] = {};

                var oldData = Object.clone(args);
                oldData[page][key] = Array.clone(metas[key]);
                oldData[page][newKey] = Array.clone(metas[newKey] || []);

                var val = metas[key].splice(index, 1);
                args[page][key] = metas[key];
                args[page][newKey] = (metas[newKey] || []).combine(val);
                metas[newKey] = args[page][newKey];

                new Request.SetMetas({
                    data: 'action=setMetaJSON&args=' + encodeURIComponent(JSON.encode(args)),
                    checkUrl: '?action=getMetaJSON&args=' + page,
                    checkData: oldData,
                    onSuccess: function() {
                        editor.exit();
                        editor = null;
                    }.bind(this)
                }).checkAndSend();
            },
            onExit: function() {
                dt.removeClass('edit');
            }
        });
    };

};

var InlineEditor = new Class({
    Implements: [Events, Options],

    options: {
        //onSave: function(value){},
        //onExit: function(){}
        oldValue: "",
        inline: false,
        suggestionKey: null,
        autoFormat: true,
        width: 20
    },

    initialize: function(element, options) {
        this.setOptions(options);

        this.element = document.id(element);
        this.build();
    },

    build: function() {
        this.element.store('html', this.element.get('html'));
        this.element.addClass('edit');

        this.element.empty();
        this.input = new Element('textarea', {
            text: this.options.oldValue,
            cols: this.options.width
        }).inject(this.element);


        if (this.options.inline) this.element.addClass('inline');

        new DynamicTextarea(this.input).addEvent('resize', function() {
            this.input.fireEvent('resize');
        }.bind(this));

        if (this.options.suggestionKey) {
            this.suggestions = new MetaSuggestions(this.input, {
                url: '?action=getMetaJSON&getvalues=' + encodeURIComponent(this.options.suggestionKey)
            });
        }

        this.input.select();

        this.element.adopt(
            new Element('input', {
                type: 'button',
                value: 'save',
                events: {
                    click: this.save.bind(this)
                }
            }),
            new Element('input', {
                type: 'button',
                value: 'cancel',
                events: {
                    click: this.cancel.bind(this)
                }
            }))
    },

    save: function() {
        this.value = this.input.get('value');
        if (this.value !== this.options.oldValue) {
            this.fireEvent('save', this.value);
        } else {
            this.cancel();
        }
    },

    _clean: function() {
        this.element.removeClass('edit');
        this.element.removeClass('inline');
    },

    exit: function() {
        if (this.suggestions) this.suggestions.detach();

        if (this.options.autoFormat) {
            new Request.HTML({
                data: 'action=ajaxUtils&util=format&text=' + encodeURIComponent(this.value),
                update: this.element,
                onSuccess: function() {
                    this._clean();
                }.bind(this)
            }).send();
        } else {

            this.element.empty();
            this.element.set('text', this.value);
            this._clean();
        }
        this.fireEvent('exit');
    },

    cancel: function() {
        if (this.suggestions) this.suggestions.detach();

        this.element.empty();
        this.element.set('html', this.element.retrieve('html'));
        this._clean();
        this.fireEvent('exit');
    }
});


//Fixing Date to output week numbers in correct (finnish) way
Date.implement({
    getFinWeek : function() {
        //if first day of year is before friday (<4) => first week number is 1
        var firstDay = this.clone().set('month', 0).set('date', 1);
        var weeknum = ((this.get('dayOfYear') + firstDay.getFinDay()) / 7).ceil();
        weeknum = (firstDay.getFinDay() < 4) ? weeknum : weeknum - 1;
        return weeknum;
    },
    getFinDay : function() {
        return (this.getDay() + 6) % 7
    }
});

/**
 * GwikiImport
 * - dynamic js importer for gwiki's javacript modules
 * License: MIT <http://www.opensource.org/licenses/mit-license.php>
 * Copyright: 2011 by Lauri Pokka
 * Depends: MooTools
 */

(function() {
    var DEPS = {
        AttachTree: {
            files: ['js/AttachTree.js'],
            depends: [],
            styles: ['css/Expand.png']
        },
        InlineEditor: {
            files: ['js/gwiki-common.js'],
            depends: ['DynamicTextarea', 'MetaSuggestions']
        },
        DynamicTextarea: {
            files: ['js/DynamicTextarea.js'],
            depends: []
        },
        MetaTable: {
            files: ['js/MetaTable.js'],
            depends: ['InlineEditor']
        },
        MetaFormEdit: {
            files: ['js/MetaFormEdit.js'],
            depends: ['DynamicTextarea', 'DatePicker']
        },
        MetaSuggestions: {
            files: ['js/MetaSuggestions.js'],
            depends: []
        },
        DatePicker: {
            files: ['js/DatePicker.js'],
            styles: [
                'css/DatePicker/datepicker_dashboard.css'
            ],
            depends: []
        }
    };

    this.GwikiImport = new Class({
        initialize: function(baseUrl) {
            this.baseUrl = baseUrl;
            this.requests = [];
            this.queue = [];
            this.loaded = [];
            Object.each(DEPS, function(module, name) {
                if (module.files.every(function(file) {
                    return $$('script[src=' + this.baseUrl + file + ']').length != 0;
                }, this)) {
                    this.loaded.push(name);
                }
            }, this);

            this.bound = {
                load: this._load.bind(this)
            }
        },

        load: function(modules, callback) {
            var missing = this.missingDeps(modules);
            if (missing.length == 0) {
                callback.apply();
            } else {
                this.requests.push({modules: missing, callback: callback});
                missing.each(this.bound.load)
            }
        },

        _load: function(mod) {
            if (this.queue.contains(mod)) return;

            var module = DEPS[mod];
            this.queue.include(mod);

            module.files.each(function(file) {
                new Asset.javascript(this.baseUrl + file, {
                    onLoad: function() {
                        this.loaded.include(mod);
                        this.queue.erase(mod);
                        this.requests = this.requests.filter(function(req) {
                            req.modules.erase(mod);
                            if (req.modules.length > 0) {
                                return true
                            } else {
                                req.callback.apply();
                                return false;
                            }
                        });
                    }.bind(this)
                });
            }, this);

            if (module.styles) module.styles.each(function(file) {
                if (file.test("css$")) new Asset.css(this.baseUrl + file);
                else new Asset.image(this.baseUrl + file);
            }, this)
        },
        missingDeps: function() {
            var deps = Array.prototype.slice.call(arguments).flatten(), missing = [];
            while (deps.length > 0) {
                mod = deps.shift();
                deps.append(DEPS[mod].depends);
                if (!this.loaded.contains(mod)) missing.include(mod);
            }

            return missing;
        }
    });
})();
