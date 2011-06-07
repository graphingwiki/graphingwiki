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

var GWIKISEPARATOR = '-gwikiseparator-';


window.addEvent('domready', function() {

    var src = $$('script[src$=gwiki-common.js]')[0].get('src').replace('gwiki-common.js', '');

    /* MetaFormEdit improvements */
    var fields = $$('.metaformedit-cloneable');
    if (fields.length > 0) new MetaFormEdit(fields[0].getParent('form'));

    /* Apply MooTools tooltips to elements with .mt-tooltip class */
    var tooltips = new Tips('.mt-tooltip', {'className': 'mootip'});

    /* Apply MetaTable improvements */
    var tables = $$('.metatable table');
    if (tables) {
        tables.each(function(tab, i) {

            new MetaTable(tab, {
                tableArguments: MetaTableArguments[i],
                separator: GWIKISEPARATOR
            });
        });
    }

    if ($$('dl dt') && $$('dl dd')) {
        $$('.gwikiinclude').include(document.body).each(initInlineMetaEdit)
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

    var metas, editor, page = "";

    if (base.hasClass('gwikiinclude')) page = unescapeId(base.id).split(GWIKISEPARATOR)[0];

    base.addEvent('mouseover:relay(div:not(.gwikiinclude) dl):once', function() {
        new Request.JSON({
            url: '?action=getMetaJSON&args=' + page,
            onSuccess: function(json) {
                page = Object.keys(json)[0];
                metas = json[page];
            }
        }).get();
    });

    var getMetaIndex = function(dt, values) {
        var key = dt.get('text');
        var dts = base.getElements('div:not(.gwikiinclude) dt').filter(
            function(dt) {
                return dt.get('text') == key;
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
            onSave: function (newValue) {
                var args = {};
                args[page] = {};

                var vals = metas[key];
                args[page][key] = vals;
                var oldData = Object.clone(args);
                vals[index] = newValue;

                new Request.SetMetas({
                    data: 'action=setMetaJSON&args=' + JSON.encode(args),
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

        if (editor) editor.cancel();

        dt.addClass('edit');

        editor = new InlineEditor(dt, {
            oldValue: key,
            onSave: function (newKey) {
                var args = {};
                args[page] = {};

                var oldData = Object.clone(args);
                oldData[page][key] = Array.clone(metas[key]);
                oldData[page][newKey] = Array.clone(metas[newKey] || []);

                var val = metas[key].splice(index, 1);
                args[page][key] = metas[key];
                args[page][newKey] = (metas[newKey] || []).combine(val);

                new Request.SetMetas({
                    data: 'action=setMetaJSON&args=' + JSON.encode(args),
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
        autoFormat: true
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
        this.input = new Element('input', {
            type: 'text',
            value: this.options.oldValue
        }).inject(this.element);

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

    exit: function() {
        if (this.options.autoFormat) {
            new Request.HTML({
                data: 'action=formatText&args=' + encodeURIComponent(this.value),
                update: this.element,
                onSuccess: function() {
                    this.element.removeClass('edit')
                }.bind(this)
            }).send();
        } else {
            this.element.removeClass('edit');
            this.element.empty();
            this.element.set('text', this.value);
        }
        this.fireEvent('exit');
    },

    cancel: function() {
        this.element.empty();
        this.element.set('html', this.element.retrieve('html'));
        this.element.removeClass('edit');
        this.fireEvent('exit');
    }
});


/*
 MetaTable
 - js improvements for MetaTable
 Depends: MooTools HtmlTable.sort
 */
(function() {
    var preformatTable = function(tab) {
        var head = tab.getElement('thead');
        if (!head) {
            head = new Element('thead').inject(tab, 'top');
            if (!head.getElement('tr')) {
                head.grab(tab.getElement('tr'));
            }
        }

        head.getElements('td')
            .addClass('head_cell')
            .setStyle('white-space', 'nowrap');

        return tab;
    };

    window.MetaTable = new Class({
        Extends: HtmlTable,
        options: {
            thSelector: 'td.head_cell:not(.edit)'
        },

        initialize: function(table) {
            preformatTable(table);
            this.parent.apply(this, arguments);

            this.metaRequest = new Request.JSON({
                url: '?action=getMetaJSON',
                data: 'args=' + encodeURIComponent(this.options.tableArguments),
                onSuccess: function(json) {
                    this.metas = json;
                }.bind(this)
            });

            this.hiddenCells = [];

            var selectors = [".meta_cell span:not(.edit)", ".meta_cell:not(.edit):empty"];
            this.body.addEvent('shiftclick:relay(' + selectors.join(", ") + ')', this.valueEdit.bind(this));

            this.head.addEvent('shiftclick:relay(span[id*=' + this.options.separator + '])', this.keyEdit.bind(this));

            table.addEvent('mouseover:once', function() {
                this.metaRequest.get()
            }.bind(this));

            this.enableSort();
            this.enableHiding();
        },

        enableHiding: function() {
            this.disableHiding();
            this.head.getElements('td').each(function(td) {
                var style = {
                    //'float': 'right',
                    'color': 'green',
                    'cursor': 'pointer',
                    'margin-left' : '4px',
                    'margin-right': 0
                };

                td.getElement('div').grab(new Element('a', {
                    'html': '&#171;',
                    'class' : 'hidelink',
                    'title': 'hide column',
                    'styles': style
                })).setStyle('white-space', 'nowrap');
                td.grab(new Element('a', {
                    'html': '&#187;',
                    'class' : 'showlink',
                    'title': 'show column',
                    'styles': style
                }).setStyle('display', 'none'));

                return this;
            });

            this.head.addEvents({
                'click:relay(a.hidelink)': function(event) {
                    this.hide.apply(this, [this.head.getElements('a.hidelink').indexOf(event.target)]);
                }.bind(this),
                'click:relay(a.showlink)': function(event) {
                    this.show.apply(this, [this.head.getElements('a.showlink').indexOf(event.target)]);
                }.bind(this)
            });

            return this;
        },

        disableHiding: function() {
            this.head.getElements('a.hidelink, a.showlink').destroy();
            this.head.removeEvents('click:relay(a.hidelink)');
            this.head.removeEvents('click:relay(a.showlink)');
            return this;
        },

        setTable: function(tab) {
            tab = preformatTable(tab);

            this.head.getElements(this.options.thSelector).destroy();
            this.head.adopt(tab.getElement('thead').getElements(this.options.thSelector));

            this.body.getElements('tr').destroy();
            this.body.adopt(tab.getElement('tbody').getElements('tr'));

            this.setParsers();
            this.enableHiding();

            return this;
        },

        valueEdit: function(event) {
            event.preventDefault();

            if (this.metaRequest.isRunning()) {
                this.valueEdit.delay(100, this, event);
                return;
            }

            var target = document.id(event.target),
                key, id, index, page, oldValue = "";

            if (target.get('tag') == 'td') {
                //edit empty cells without existing value
                var i = target.getParent('tr').getElements('td.meta_cell').indexOf(target);
                id = unescapeId(this.head.getElements('span[id*=' + this.options.separator + ']')[i].get('id'));
                key = id.split(this.options.separator)[1];
                index = 0;
                page = target.getParent('tr').getFirst('td').get('text');
            } else {
                //edit existing value
                if (target.get('tag') != 'span') target = target.getParent('span');

                id = unescapeId(target.get('id'));

                page = id.split(this.options.separator)[0];
                key = id.split(this.options.separator)[1];
                index = id.split(this.options.separator)[2];
                oldValue = this.metas[page][key][index];
            }

            if (this.inlineEditor) this.inlineEditor.cancel();

            var editor = this.inlineEditor = new InlineEditor(target, {
                autoFormat: false,
                oldValue: oldValue,
                onSave: function(value) {
                    if (!this.metas[page][key]) this.metas[page][key] = [""];

                    var oldData = {};
                    oldData[page] = {};
                    oldData[page][key] = Array.clone(this.metas[page][key]);

                    this.metas[page][key][index] = value;

                    var args = {};
                    args[page] = {};
                    args[page][key] = this.metas[page][key];

                    new Request.SetMetas({
                        data: 'action=setMetaJSON&args=' + JSON.encode(args),
                        checkUrl: '?action=getMetaJSON&args=' + page,
                        checkData: oldData,
                        onSuccess: function() {
                            this.inlineEditor = null;
                            this.refresh();
                        }.bind(this),
                        onConflict: function() {
                            this.inlineEditor.cancel();
                            this.refresh();
                        }.bind(this)
                    }).checkAndSend();

                    editor.exit();
                }.bind(this)
            });
        },

        keyEdit: function(event) {
            event.stopPropagation();
            event.preventDefault();

            if (this.metaRequest.isRunning()) {
                this.keyEdit.delay(100, this, event);
                return;
            }

            var target = document.id(event.target);
            if (target.get('tag') != 'span') target = target.getParent('span');

            var id = unescapeId(target.get('id'));
            var oldKey = id.split(this.options.separator)[1];

            if (this.inlineEditor) this.inlineEditor.cancel();

            var parent = target.getParent('td').addClass('edit');

            var editor = this.inlineEditor = new InlineEditor(target, {
                autoFormat: false,
                oldValue: oldKey,
                onSave: function(newKey) {
                    var oldData = Object.map(this.metas, function(metas, page) {
                        var m = Object.subset(metas, [oldKey, newKey]);
                        if (!m[newKey]) m[newKey] = [];
                        return m;
                    });

                    var args = Object.map(this.metas, function(metas, page) {
                        var renamed = {};
                        renamed[newKey] = (metas[newKey] || []).combine(metas[oldKey]);
                        renamed[oldKey] = [];
                        return renamed;
                    });

                    new Request.SetMetas({
                        data: 'action=setMetaJSON&args=' + JSON.encode(args),
                        checkUrl: '?action=getMetaJSON&args=' + page,
                        checkData: oldData,
                        onSuccess: function() {
                            this.inlineEditor = null;
                            this.refresh();
                        }.bind(this),
                        onConflict: function() {
                            this.inlineEditor.cancel();
                            this.refresh();
                        }.bind(this)
                    }).checkAndSend();

                    editor.exit();
                }.bind(this),
                onExit: function() {
                    parent.removeClass('edit');
                }
            });
        },

        editpopup: function(event) {
            event.preventDefault();

            if (this.metaRequest.isRunning()) {
                this.editpopup.delay(100, this, event);
                return;
            }
            var row = document.id(event.target).getParent('tr');
            var tds = row.getElements('td');
            var pagename = tds[0].get('text');

            var editor = new Editor(pagename, this.metas[pagename]);

            editor.addEvent('success', function(metas) {
                this.metas[pagename] = metas;
                this.refresh();
            }.bind(this))

        },

        refresh: function() {
            if (this.inlineEditor) return;

            this.metaRequest.get();

            new Request.HTML({
                url: '?action=showMetaTable',
                data: 'args=' + this.options.tableArguments,
                evalScripts: false,
                onSuccess: function(nodes) {
                    var tab = $$(nodes).getElement('table').filter(function(el) {
                        return el != null
                    });
                    if (tab.length != 1) return; //todo: show error message
                    this.setTable(tab[0]);
                    this.reSort();
                    this.hiddenCells.each(this.hide, this);
                }.bind(this)

            }).send();
        },

        hide: function(i) {
            this.hiddenCells.include(i);
            i++;
            this.head.getElements(this.options.thSelector + ':nth-child(' + i + ') div').setStyle('display', 'none');
            this.head.getElements(this.options.thSelector + ':nth-child(' + i + ') .showlink').setStyle('display', '');
            this.body.getElements('tr td:nth-child(' + i + ')').each(function(td) {
                td.store('hiddenHtml', td.get('html'));
                td.set('html', '');
            });
            return false;
        },

        show: function(i) {
            this.hiddenCells.erase(i);
            i++;
            this.head.getElements(this.options.thSelector + ':nth-child(' + i + ') div').setStyle('display', '');
            this.head.getElements(this.options.thSelector + ':nth-child(' + i + ') .showlink').setStyle('display', 'none');
            this.body.getElements('tr td:nth-child(' + i + ')').each(function(td) {
                td.set('html', td.retrieve('hiddenHtml'));
            });
            return false;
        },

        headClick: function(event) {
            //clear unintended selections
            if (window.getSelection) {
                var s = window.getSelection();
                if (s) s.collapse(document.body, 0);
            }

            if (!$(event.target).hasClass('hidelink') && !$(event.target).hasClass('showlink'))
                this.parent.apply(this, arguments);

        }
    });

    var Editor = new Class({
        Implements: [Events, Options],
        initialize: function(page, metas) {
            this.page = page;
            this.metas = metas || {};
            this.build()
        },

        build: function() {
            this.bg = new Element('div.alphabg').setStyles({
                'position': 'absolute',
                'left': '0',
                'top': '0',
                'width': '100%',
                'min-height': window.getScrollSize().y,
                'z-index': '99'
            }).inject(document.body);

            var container = new Element('div').setStyles({
                'position': 'relative',
                'margin': '100px auto auto',
                'padding': '8px',
                'width': '500px',
                'background': 'white',
                'border': '2px black solid',
                'border-radius': '5px'
            }).inject(this.bg);

            var close = new Element('div.close-button[text=x]')
                .addEvent('click', this.cancel.bind(this))
                .inject(container);

            this.editor = new Element('div').setStyles({
                'min-height': '200px'
            }).inject(container);

            if (this.page == null) {
                this.editor.grab(new Element('input', {
                    'name': 'pagename',
                    'id': 'pagename',
                    'placeholder': 'page name'
                }));
            } else {
                this.editor.grab(new Element('h3').set('text', this.page));
            }


            var form = new Element('form').inject(this.editor);
            var dl = new Element('dl').inject(form);

            Object.each(this.metas, function(values, key) {
                var generateInput = function(val) {

                    var input = new Element('input', {
                        name: key,
                        value: val
                    }).setStyle('width', '400px');

                    var dd = new Element('dd').grab(input);
                    if (dt.getNext('dt')) {
                        dd.inject(dt.getNext('dt'), 'before')
                    } else {
                        dl.grab(dd);
                    }

                    dd.grab(new Element('a', {
                        'class': 'jslink',
                        'title': 'Remove value',
                        'html': 'x',
                        'styles': {
                            'margin-left': '8px',
                            'color': 'red',
                            'font-weight': 'bold'
                        },
                        'events': {
                            'click': function() {
                                dd.destroy();
                                //if (dl.getElements('dd').length == 0) dl.destroy();
                            }
                        }}))
                };

                var dt = new Element('dt[text=' + key + ']');
                dl.grab(dt.grab(
                    new Element('a', {
                        'class': 'jslink',
                        'text': '+',
                        'title': 'Add value',
                        'styles': {
                            'margin-left': '8px',
                            'color': 'green',
                            'font-weight': 'bold'
                        },
                        'events': {
                            'click': generateInput.bind(this, "")
                        }
                    })
                ));


                if (values.length == 0) values = [""];
                values.each(generateInput);
            });
            var controls = new Element('div').adopt(
                new Element('button', {
                    text: 'Save',
                    styles: {
                        'float': 'left'
                    },
                    events: {
                        'click': this.send.bind(this)
                    }
                }),
                new Element('div').setStyle('clear', 'both')
            ).inject(container)
        },

        send: function() {
            var metas = {};
            this.editor.getElements('input').each(function(el) {
                if (!metas[el.name]) metas[el.name] = [];
                metas[el.name].push(el.value);
            });
            var args = {
                metas: metas,
                action: 'set'
            };

            new Request.JSON({
                url : this.page,
                method: 'post',
                data: 'action=setMetaJSON&args=' + JSON.encode(args),
                onSuccess: function(response) {
                    if (response && response.status == "ok") {
                        this.fireEvent('success', metas);
                        this.bg.destroy();
                    }
                }.bind(this)
            }).send()
        },

        cancel: function() {
            this.bg.destroy();
        }
    });
})();


/*
 MetaFormEdit
 - js improvements for meta edit form.
 Depends: MooTools Core
 */
var MetaFormEdit = new Class({
    initialize: function (form) {
        this.form = document.id(form);
        this.fields = this.getFields();

        this.SEPARATOR = this.form.getElement('input[name=' + GWIKISEPARATOR + ']').get('value');
        this.clean();
        this.build();
    },

    getFields: function() {
        return this.form.getElements('.metaformedit-cloneable, .metaformedit-notcloneable');
    },

    build: function() {
        var self = this;

        this.form.getElements('.metaformedit-cloneable').each(function(dd) {
            var dt = dd.getPrevious('dt');
            var siblings = dd.getParent().getChildren();
            if (siblings.indexOf(dd) - 1 != siblings.indexOf(dt)) return;
            dt.appendText(' ');
            dt.grab(new Element('a', {
                'class': 'jslink',
                'text': '+',
                'title': 'Add value',
                'events': {
                    'click': function() {
                        self.clone(dt.getNext('dd'));
                    }
                }
            }));
        });

        this.fields.each(function(el) {
            el.grab(new Element('a', {
                'class': 'jslink',
                'title': 'Remove value',
                'html': 'x',
                'styles': {
                    'margin-left': '8px',
                    'color': 'red',
                    'font-weight': 'bold'
                },
                'events': {
                    'click': function() {
                        self.remove(this.getParent('dd'))
                    }
                }
            }));
        });
    },

    /*
     Tries to group values with same key under one section.
     */
    clean: function() {
        var keys = [];
        var fields = this.getFields();
        fields.each(function(el) {
            if (!el || el.getElement('input, select, textarea') == null) return;
            var key = el.getElement('input, select, textarea').name;
            if (keys.contains(key)) {
                var values = [];
                el.getElements('input, select, textarea').each(function(input) {
                    if (input.get('tag') == "select") {
                        values.push(input.value);
                    } else if (["radio", "checkbox"].contains(input.type)) {
                        if (input.checked) values.push(input.value)
                    } else {
                        values.push(input.value)
                    }
                });

                this.remove(el);
                this.clone(this.getFields().filter(function(field) {
                    var els = field.getElements('[name^=' + key.split(" ")[0] + ']');
                    return els.length > 0 && els.some(function(el) {
                        return el.name == key;
                    });
                })[0], values, true);
            } else {
                keys.push(key)
            }
        }, this);
    },

    clone: function(source, values, minimalNew) {
        values = values || [];
        var first = source.getElement('input, select, textarea');
        var type = first.get('tag') == 'select' ? "select" : first.type;

        if (["checkbox"].contains(type)) {
            source.getElements('input[type=checkbox]').each(function(input) {
                if (values.contains(input.value)) {
                    input.checked = true;
                    values.erase(input.value);
                }
            });
            if (source.getElement('input[type=text]') == null || minimalNew) return;
        }

        var cloned = source.clone();
        if (cloned.getElement('a.jslink') != null) {
            cloned.getElement('a.jslink').cloneEvents(source.getElement('a.jslink'));
        }

        cloned.getElements('select, input, textarea').each(function(input) {
            input.value = "";
            input.checked = false;

            if (input.hasClass('file') && values.length == 0) {

                input.set('readonly', false);
                var name = input.name.split(this.SEPARATOR, 2).join(this.SEPARATOR);
                var i = 1;

                while (this.form.getElement('input[name=' + name + this.SEPARATOR + i + ']')) i++;

                new Element('input', {
                    'class': 'file',
                    'type': 'file',
                    'name': name + this.SEPARATOR + i
                }).inject(input, 'after');

                input.destroy();
            }

            if (input.get('tag') == "select") {
                input.getElements('option').set("selected", false);//[0].set("selected", true);
                input.getElements('option').each(function(opt) {
                    if (values.contains(opt.value)) {
                        opt.set("selected", true);
                        values.erase(opt.value);
                    }
                });
            }
            if (values.length > 0 && ["textarea", "text"]) {
                input.set('value', values.pop());
            }

        }, this);
        cloned.inject(source, 'before');
        this.fields.splice(this.fields.indexOf(source) + 1, 0, cloned);
    },

    remove: function(el) {
        var siblings = el.getParent().getChildren();
        var index = siblings.indexOf(el);
        if (siblings[index - 1].get('tag') == "dt"
            && (!siblings[index + 1] || siblings[index + 1].get('tag') == "dt")) {
            siblings[index - 1].destroy();
        }
        this.fields.erase(el);
        el.destroy();
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
