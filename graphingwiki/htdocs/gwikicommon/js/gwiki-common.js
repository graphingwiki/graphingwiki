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

window.addEvent('domready', function() {

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
                sortable: true,
                tableArguments: MetaTableArguments[i],
                separator: '-gwikiseparator-'
            });
        });
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
        head.getElements('td').addClass('head_cell').setStyle('white-space', 'nowrap');
        return tab;
    };

    window.MetaTable = new Class({
        Extends: HtmlTable,
        options: {
            thSelector: 'td.head_cell'
        },

        initialize: function(table) {
            preformatTable(table);
            this.parent.apply(this, arguments);

            this.bound.edit = this.edit.bind(this);

            this.request = new Request.JSON({
                url: '?action=getMetaJSON',
                data: 'args=' + encodeURIComponent(this.options.tableArguments),
                onSuccess: function(json) {
                    var separator = new Element('a').set('html', '&#171;').get('text');
                    var visibleKeys = this.head.getElements('td').get('text').map(function(val) {
                        return val.split(separator)[0].trim();
                    });

                    if (visibleKeys[0] == "") visibleKeys.shift();

                    this.metas = Object.map(json, function(metas) {
                        return Object.filter(metas, function(value, key) {
                            return visibleKeys.some(function(k) {
                                return key.contains(k);
                            });
                        });
                    }, this);
                }.bind(this)
            }).get();

            this.hiddenCells = [];

            //add column hiding functionality
            this.head.getElements(this.options.thSelector).each(function(th) {
                var style = {
                    //'float': 'right',
                    'color': 'green',
                    'cursor': 'pointer',
                    'margin-left' : '4px',
                    'margin-right': 0
                };

                th.getElement('div').grab(new Element('a', {
                    'html': '&#171;',
                    'class' : 'hidelink',
                    'title': 'hide column',
                    'styles': style
                })).setStyle('white-space', 'nowrap');
                th.grab(new Element('a', {
                    'html': '&#187;',
                    'class' : 'showlink',
                    'title': 'show column',
                    'styles': style
                }).setStyle('display', 'none'));
            }, this);

            this.body.addEvent('click:relay(.meta_editicon a)', this.bound.edit);
            this.head.addEvents({
                'click:relay(a.hidelink)': function(event) {
                    this.hide.apply(this, [this.head.getElements('a.hidelink').indexOf(event.target)]);
                }.bind(this),
                'click:relay(a.showlink)': function(event) {
                    this.show.apply(this, [this.head.getElements('a.showlink').indexOf(event.target)]);
                }.bind(this)
            })
        },

        edit: function(event) {
            event.preventDefault();

            if (this.request.isRunning()) {
                this.edit.delay(100, this, event);
                return;
            }
            var row = document.id(event.target).getParent('tr');
            var tds = row.getElements('td');
            var pagename = tds[0].get('text');

            var editor = new Editor(pagename, this.metas[pagename]);

            editor.addEvent('success', function(metas) {
                this.metas[pagename] = metas;
                new Request.HTML({
                    url: '?action=showMetaTable',
                    data: 'args=' + this.options.tableArguments,
                    evalScripts: false,
                    onSuccess: function(nodes) {
                        var tab = $$(nodes).getElement('table').filter(function(el) {
                            return el != null
                        });
                        if (tab.length != 1) return; //todo: show error message
                        tab = preformatTable(tab[0]);
                        this.body.getElements('tr').destroy();
                        this.body.adopt(tab.getElement('tbody').getElements('tr'));
                        this.hiddenCells.each(this.hide, this);

                    }.bind(this)

                }).send();

            }.bind(this))

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

            if (!$(event.target).hasClass('hidelink') && !$(event.target).hasClass('showlink')) this.parent.apply(this, arguments);

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

        this.SEPARATOR = this.form.getElement('input[name=gwikiseparator]').get('value');
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
