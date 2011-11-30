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

    //Prevent reload loops if cookies are disabled
    if (Cookie.read('js')) {
        window.location.reload();
    }
}

window.dateformat = '%Y-%m-%d';
window.GWIKISEPARATOR = '-gwikiseparator-';


window.addEvent('domready', function() {

    var src = $$('script[src$=gwiki-common.js]')[0].get('src').replace('js/gwiki-common.js', '');

    var loader = new GwikiImport(src);

    // MetaFormEdit improvements
    var fields = $$('.metaformedit');
    if (fields.length > 0) {
        loader.load('MetaFormEdit', function() {
            new MetaFormEdit(fields[0].getParent('form'));
        });
    }

    // Apply MooTools tooltips to elements with .mt-tooltip class
    var tooltips = new Tips('.mt-tooltip', {'className': 'mootip'});

    // Apply MetaTable improvements
    var tables = $$('div.metatable[data-options]');
    if (tables.length > 0) {
        loader.load('MetaTable', function() {
            tables.each(function(div, i) {

                new MetaTable(div.getElement('table'), {
                    tableArguments: JSON.decode(decodeURIComponent(div.getAttribute('data-options'))),
                    separator: GWIKISEPARATOR
                });
            });
        });
    }

    // InterMetaTable
    if ($$('div.InterMetaTable').length) {
        loader.load('MetaTable', function(){
            $$('div.InterMetaTable').each(function(table){
                var opts = JSON.decode(decodeURIComponent(table.getAttribute('data-options')));
                new InterMetaTable(table, opts);
            })
        })
    }

    // Inline Edit
    if ($$('dl:not(.collab_list) dt').length && $$('dl:not(.collab_list) dd').length) {
        loader.load('InlineEditor', function() {
            $$('.gwikiinclude').include(document.body).each(initInlineMetaEdit)
        });
    }

    // AttachTree
    if ($$('.attachtree_area')) {
        loader.load('AttachTree', function() {
            $$('.attachtree_area').each(function(el) {
                new AttachTree(el);
            })
        });
    }

    // DynamicTextareas for textareas with .dynamic
    if ($$('textarea.dynamic')) {
        loader.load('DynamicTextarea', function(){
            $$('textarea.dynamic').setStyles({
                'resize': 'none',
                'overflow': 'hidden'
            });
            
            document.body.addEvent('focus:relay(textarea.dynamic)', function(e){
                if (!$(e.target).retrieve('dynamic')) {
                    new DynamicTextarea(e.target);
                    $(e.target).store('dynamic', true).focus();
                }
            });
        });
    }

    //DnD file attachment upload
    initDnDUpload(document.body);
});

Element.Events.shiftclick = {
    base: 'click', // the base event type
    condition: function(event) {
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


var initDnDUpload = function(el){
    function noAction(e) {
        e.stopPropagation();
        e.preventDefault();
    }


    var overlay = null;

    el.addEventListener("dragenter", noAction, false);
    el.addEventListener("dragexit", noAction, false);
    el.addEventListener("dragover", noAction, false);
    el.addEventListener("drop", function(e) {
        e.stopPropagation();
        e.preventDefault();

        if (overlay) overlay.cancel();

        if (typeof(window.FileReader) == 'undefined' || typeof(window.FormData) == 'undefined') {
            // FailBack file uploader using normal form
            if (confirm("Ajax file uploading not supported by your browser, proceed to normal AttachFile action?")) {
                var url = window.location.href;
                var action = "?action=AttachFile";
                window.location.href = window.location.search ? url.replace(window.location.search, action) : url + action;
            }
        } else {
            // Upload using FileReader & xmlhttprequest + formdata
            var files = e.dataTransfer.files;

            if (files.length > 0) {
                overlay = new Overlay({
                    width: '650px',
                    onBuild: function() {
                        this.editor.grab(new Element('h3[text=Attach to page]'));
                        var div = new Element('div').inject(this.editor);
                        var ul = new Element('ul').inject(div);
                        var status = [];
                        var names = [];
                        for (var i = 0; i < files.length; i++) {
                            status.push(new Element('span'));
                            names.push(new Element('span').set('text', files[i].name));
                            ul.grab(new Element('li').adopt(names[i], status[i]));
                        }

                        var overwrite = false;
                        var failed = null;

                        var progress = new Element('div').inject(new Element('div.progress.hidden').inject(div));

                        div.grab(new Element('input[type=button][value=Send]').addEvent('click', function(e) {
                            var xhr = new XMLHttpRequest();
                            xhr.open('POST', '?action=ajaxUtils&util=uploadFile', true);

                            var text = new Element('span[text= ]').inject(progress.empty());
                            progress.getParent().removeClass('hidden');

                            var data = new FormData();
                            xhr.upload.addEventListener('progress', function(event) {
                                var percent = parseInt(event.loaded / event.total * 100);
                                progress.setStyle('width', percent + '%');
                                text.set('text', percent + '%');
                            }, false);
                            
                            xhr.onreadystatechange = function(event) {
                                if (event.target.readyState == 4) {
                                    if (event.target.status == 200) {
                                        text.set('text', ' complete!');
                                        var json = JSON.decode(xhr.responseText);
                                        failed = json.failed;

                                        for (var i = 0; i < files.length; i++) {
                                            new Request.HTML({
                                                data: 'action=ajaxUtils&util=format&text=' + encodeURIComponent("[[attachment:" + files[i].name + "]]"),
                                                update: names[i]
                                            }).send();

                                            if (json.success.contains(files[i].name)) {
                                                status[i].set('text', "success").setStyles({
                                                    'font-style': 'italic',
                                                    'color': 'green',
                                                    'margin-left': '15px'
                                                });
                                            }else if (failed.contains(files[i].name)) {
                                                status[i].set('text', "failed, file already in attachments!").setStyles({
                                                    'font-style': 'italic',
                                                    'color': 'red',
                                                    'margin-left': '15px'
                                                });

                                                $(e.target).removeClass('hidden').set('value', 'Overwrite');
                                                overwrite = true;
                                            }
                                            progress.getParent().addClass('hidden');
                                        }
                                    }
                                    else {
                                        text.set('text', ' Upload failed!');
                                    }
                                }
                            };

                            for (var i = 0; i < files.length; i++) {
                                if (failed && !failed.contains(files[i].name)) continue;
                                data.append("file" + i, files[i])
                            }

                            if (overwrite) data.append("overwrite", 1);
                            
                            xhr.send(data);

                            $(e.target).addClass('hidden');

                        }).setStyle('font-size', 'larger'));
                    }
                });
            }
        }
    }, false);



};

var initInlineMetaEdit = function (base) {

    //do not attach inline edit if MetaFormEdit is running
    if (!base.getElement('dl:not(.collab_list)') || base.getElement('dl').getParent('form')) return;

    var metas, editor, page = "";

    if (base.hasClass('gwikiinclude')) page = unescapeId(base.id).split(GWIKISEPARATOR)[0];

    base.addEvent('mouseover:relay(div:not(.gwikiinclude) dl):once', function() {
        new Request.JSON({
            url: '?action=getMetaJSON&args=' + page,
            onSuccess: function(json) {
                page = Object.keys(json)[0];
                metas = json[page];
                base.getElements('div:not(.gwikiinclude) dd').each(function(dd) {
                    if (dd.get('text').clean() == "" && dd.getElements('img').length == 0) {
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
        if (dd.get('text').clean() == "" && dd.getElements('img').length == 0) {

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

        editValue(dd);
    });

    var editValue = function(dd) {
        if (metas == null) {
            editValue.delay(100, this, dd);
            if (dd.getElements('.waiting').length == 0)
                dd.grab(new Element('span.waiting').set('html', '&nbsp;'), 'top');
            return;
        } else {
            dd.getElements('.waiting').destroy();
        }

        var key = dd.getPrevious('dt').get('text');
        var index = getMetaIndex(dd.getPrevious('dt'), metas[key]);

        var oldValue = metas[key][index];

        if (editor) editor.cancel();

        dd.addClass('edit');

        editor = new InlineEditor(dd, {
            oldValue: oldValue,
            key: key,
            inline: true,
            width: 40,
            size: 'large',
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

        editKey(dt);
    });

    var editKey = function(dt) {
        if (metas == null) {
            editValue.delay(100, this, dt);
            if (dt.getElements('.waiting').length == 0)
                dt.grab(new Element('span.waiting').set('html', '&nbsp;'), 'top');
            return;
        } else {
            dt.getElements('.waiting').destroy();
        }
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
        inline: false, //puts all controls on the same row if enabled
        key: null,
        autoFormat: true,
        field: null,
        width: 20,
        size: 'compact'
    },

    _keyProperties: {
        hint: 'text',
        constraint: null
    },

    initialize: function(element, options) {
        this.setOptions(options);


        this.element = document.id(element);

        if (this.options.key) {
            new Request.JSON({
                url: '?action=ajaxUtils&util=getProperties&key=' + this.options.key,
                onComplete: function(json) {
                    this._keyProperties = Object.merge(this._keyProperties, json);
                    this.build();
                }.bind(this)
            }).get();
        } else {
            this.build();
        }
    },

    build: function() {
        this.element.store('html', this.element.get('html'));
        this.element.addClass('edit');

        this.element.empty();

        var oldVal = this.options.oldValue;
        var type = this._keyProperties.hint;
        if (type == "date") {
            this.input = new Element('input',{
                value: oldVal,
                size: 11
            }).inject(this.element);
            new Picker.Date(this.input, {
                format: dateformat,
                pickerClass: 'datepicker_dashboard'
            });

            this.input.select();

        } else if (this._keyProperties.constraint == "existing") {
            var input = this.input = new Element('select.waiting').inject(this.element);
            new Request.JSON({
                url: '?action=getMetaJSON&getvalues=' + encodeURIComponent(this.options.key),
                onSuccess: function(json) {
                    input.removeClass('waiting');
                    var vals = [];
                    Object.each(json, function(values, page) {
                        vals.combine(values);
                    });
                    vals.each(function(value){
                       input.grab(new Element('option',{
                           value: value,
                           text: value,
                           selected: (value == oldVal)
                       }));
                    });
                }
            }).get();
        } else {
            this.input = new Element('textarea', {
                text: oldVal,
                cols: this.options.width
            }).inject(this.element);

            this.input.addEvent('keydown', function(e) {
                if (e && e.key == "esc") this.cancel();
            }.bind(this));

            if (this.options.inline) this.element.addClass('inline');

            var field = this.options.size == "compact" ? DynamicTextarea: GwikiDynamicTextarea;
            new field(this.input).addEvent('resize', function() {
                this.input.fireEvent('resize');
            }.bind(this));

            if (this.options.key) {
                this.suggestions = new MetaSuggestions(this.input, {
                    url: '?action=getMetaJSON&getvalues=' + encodeURIComponent(this.options.key)
                });
            }

            this.input.select();
        }
        

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

//Adds horizontal growing to dynamic text areas
var GwikiDynamicTextarea = function(textarea, options) {
    if (!window.GwikiDynamicTextarea_) {
        window.GwikiDynamicTextarea_ = new Class({
            Extends: DynamicTextarea,
            options: {
                horizontalGrow: true,
                maxWidth: 650,
                onResize: function() {
                    var x = this.textarea.getSize().x - 2 * this.textarea.getStyle('paddingLeft').toInt() - 2 * this.textarea.getStyle('borderWidth').toInt();
                    if (this.textarea.getStyle('width').toInt() != this.options.maxWidth && this.options.minRows * this.options.lineHeight < this.textarea.getScrollSize().y) {
                        if (!this.origWidth) this.origWidth = x;
                        this.textarea.setStyle('width', this.options.maxWidth);
                        this.checkSize(true);
                    }
                },
                onBlur: function() {
                    if (this.origWidth)  this.textarea.setStyle('width', this.origWidth);
                    this.checkSize(true);
                }
            }
        });
    }

    return new GwikiDynamicTextarea_(textarea, options);
};

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


Object.extend({
    sortedKeys: function(object) {
        return Object.keys(object).sort();
    },

    sortedValues: function(object) {
        var keys = Object.keys(object).sort();
        return keys.map(
            function(key) {
                return object[key];
            }).flatten();
    }
});

/**
 * Overlay
 * - Customizable overlay widget with nice opacity
 */
var Overlay = new Class({
    Implements: [Events, Options],
    options: {
        width: '80%',
        onBuild: function(){}
    },

    initialize: function(options) {
        this.setOptions(options);
        this.build();
    },

    build: function() {
        this.bg = new Element('div.alphabg').setStyles({
            'position': 'absolute',
            'left': 0,
            'top': 0,
            'width': document.id(window).getScrollSize().x,
            'min-height': document.id(window).getScrollSize().y,
            'z-index': '999'
        }).inject(document.body);

        this.positioner = new Element('div').setStyles({
            'position': 'absolute',
            'left': 0,
            'top': 0,
            'width': '100%',
            'z-index': '999'
        }).inject(document.body);
        this.container = new Element('div').setStyles({
            'position': 'relative',
            'margin': 'auto',
            'top': document.id(window).getScroll().y + 100,
            'padding': '15px',
            'width': this.options.width,
            'background': 'white',
            'border': '2px black solid',
            'border-radius': '5px'
        }).inject(this.positioner);

        var close = new Element('div.close-button[text=x]')
            .addEvent('click', this.cancel.bind(this))
            .inject(this.container);

        this.editor = new Element('div').setStyles({
            'min-height': '200px'
        }).inject(this.container);

        this.fireEvent('build');
    },

    cancel: function() {
        this.bg.destroy();
        this.positioner.destroy();
    }
});

/**
 * ActionSelector
 * - creates a select element with events bound to options
 *
 *  usage: elem.grab(new ActionSelector({"option1": func}, this))
 */
var ActionSelector = new Class({
    initialize: function(opts, context) {
        this.opts = opts;
        this.context = context;
        this.build();
        this.attach();
    },

    build: function() {
        this.element = new Element('select');
        Object.each(this.opts, this.add, this);
    },

    add: function(func, name) {
        this.element.grab(new Element('option', {
            text: name,
            value: name
        }));
    },

    attach: function() {
        this.element.addEvent('change', function(event) {
            var val = event.target.get('value');
            this.opts[val].apply(this.context);
        }.bind(this))
    },

    detach: function(){
        this.element.removeEvents('change');
    },

    toElement: function() {
        return this.element;
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
            styles: ['img/Expand.png']
        },
        InlineEditor: {
            files: ['js/gwiki-common.js'],
            depends: ['DynamicTextarea', 'MetaSuggestions', 'DatePicker']
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
