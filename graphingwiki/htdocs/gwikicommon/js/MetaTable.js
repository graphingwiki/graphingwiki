/*
 MetaTable.js
 - js improvements for MetaTable
 License:	MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2011 by Lauri Pokka
 Depends: MooTools HtmlTable.sort InlineEditor Request.SetMetas Events.shiftclick More/Date
 */

(function($, exports) {
    "use strict";

    var preformatTable = function(tab) {
        var head = tab.getElement('thead');
        if (!head) {
            head = new Element('thead').inject(tab, 'top');
            if (!head.getElement('tr')) {
                head.grab(tab.getElement('tr'));
            }
        }

        head.getElements('td')
            .addClass('head_cell');

        return tab;
    };

    var diff = function(o1, o2) {
        var changed = [];
        Object.each(o2, function(metas, page) {
            if (!o1[page]) changed.include(page);
            else {
                Object.each(metas, function(values, key) {
                    var values2 = o1[page][key];
                    if (!values2 ||
                        !values.every(values2.contains.bind(values2)) ||
                        !values2.every(values.contains.bind(values)))
                        changed.include(page);
                });
            }
        });
        return changed;

    };

    var retrieveMetas = function(tbody) {
        var metas = {};
        tbody.getElements('tr').each(function(row){
            var page = row.getElement('.meta_page');
            if (page) page = page.get('text');
            if (page && !metas[page]) metas[page] = {};

            var vals = {};

            row.getElements('.meta_cell span').each(function(span){
                var val = span.get('data-value') || span.get('text');
                var page = span.get('data-page');
                var key = span.get('data-key');
                var index = span.get('data-index');
                if (page && !metas[page]) metas[page] = {};
                if (val) {
                    if (!vals[key]) vals[key] = {};
                    vals[key][index] = val;
                    metas[page][key] = Object.values(vals[key]);
                }
            });
        });
        return metas;
    };

    HtmlTable.Parsers['numberSpan'] = {
        match: /^<[^>]+>\d+[^\d.,]*<.+/,
        convert: function() {
            return this.getElement('span').get('text').toInt();
        },
        number: true
    };
    if (!HtmlTable.ParserPriority.contains("numberSpan")) {
        HtmlTable.ParserPriority.splice(0,0, "numberSpan")
    }

    var HideableTable = new Class({
        Extends: HtmlTable,

        initialize: function() {
            this.parent.apply(this, arguments);

            this.hiddenCells = [];
        },

        enableHiding: function() {
            this.disableHiding();
            this.head.getElements('td, th').each(function(td) {
                var style = {
                    //'float': 'right',
                    'color': 'green',
                    'cursor': 'pointer',
                    'margin-left': '4px',
                    'margin-right': 0
                };

                td.getElement('div').grab(new Element('a', {
                    'html': '&#171;',
                    'class': 'hidelink',
                    'title': 'hide column',
                    'styles': style
                }));
                td.grab(new Element('a', {
                    'html': '&#187;',
                    'class': 'showlink',
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


    var MetaTable = exports.MetaTable = new Class({
        Extends: HideableTable,
        options: {
            thSelector: 'td.head_cell:not(.edit)',
            tableArguments: {}
        },

        initialize: function(table) {
            table = $(table);
            preformatTable(table);
            this.parent.apply(this, arguments);

            this.tableArgs = Object.merge({
                'args': '',
                'template': null,
                'autorefresh': false,
                'nametemplate': ''
            }, this.options.tableArguments);

            this.metaRequest = new Request.HTML();
            this.metas = retrieveMetas(this.body);

            var selectors = [".meta_cell span:not(.edit)", ".meta_cell:not(.edit)"];
            this.body.addEvent('shiftclick:relay(' + selectors.join(", ") + ')', this.valueEdit.bind(this));

            this.head.addEvent('shiftclick:relay(span[data-key])', this.keyEdit.bind(this));

            if (this.tableArgs.autorefresh) {
                this.refresh.periodical(this.tableArgs.autorefresh * 1000, this, null);
            }

            var parent = table.getParent('div.metatable');
            if (parent && parent.getNext('a') && parent.getNext('a').get('text') == "[edit]") {
                new Element('a.jslink[text=[new row]]')
                    .setStyles({'font-size': 'inherit'})
                    .addEvent('click', this.newPage.bind(this))
                    .inject(parent, 'after');
            }

            this.enableSort();
            this.enableHiding();
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

            var target = $(event.target),
                key, index, page, oldValue = "";

            if (target.get('tag') == 'td') {
                //add new value, page and key can be retrieved from first span
                if (target.children.length > 0) {
                    var first = target.getElement('span');
                    page = first.get('data-page');
                    key = first.get('data-key');
                    //only one span without value => use that span
                    if (target.children.length == 1 && first.get('text') === "") {
                        index = 0;
                        target = first;
                    }else{
                        //append new value to existing ones if key had values
                        index = this.metas[page][key].length;
                        target = new Element('span').inject(target);
                    }
                } else {
                    return;
                }

            } else {
                //edit existing value
                if (target.get('tag') != 'span') target = target.getParent('span');

                page = target.get('data-page');
                key = target.get('data-key');
                index = target.get('data-index');
                oldValue = this.metas[page][key][index];
            }

            if (this.inlineEditor) this.inlineEditor.cancel();

            var editor = this.inlineEditor = new InlineEditor(target, {
                autoFormat: false,
                oldValue: oldValue,
                key: key,

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
                        metas: args,
                        checkArgs: page,
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

            var target = $(event.target);

            if (target.get('tag') != 'span') target = target.getParent('span');
            var oldKey = target.get('data-key');

            //check that the key is really meta-key and not indirection
            if (!Object.some(this.metas, function(metas, page){
                return metas[oldKey];
            })) return;

            if (this.inlineEditor) this.inlineEditor.cancel();

            var parent = target.getParent('td').addClass('edit');

            var editor = this.inlineEditor = new InlineEditor(target, {
                autoFormat: false,
                oldValue: oldKey,
                onSave: function(newKey) {
                    var oldData = Object.map(Object.clone(this.metas), function(metas, page) {
                        var m = Object.subset(metas, [oldKey, newKey]);
                        if (!m[newKey]) m[newKey] = [];
                        return m;
                    });

                    var args = Object.map(this.metas, function(metas, page) {
                        var renamed = {};
                        renamed[newKey] = (metas[newKey] || []).combine(metas[oldKey] || []);
                        renamed[oldKey] = [];
                        return renamed;
                    });

                    new Request.SetMetas({
                        metas: args,
                        checkArgs: this.tableArgs.args,
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

        newPage: function(event) {
            if (event) event.preventDefault();


            if (this.tableArgs.template && !this.template) {
                if (!this._templateRequest) {
                    this._templateRequest = new Request({
                        url: '?action=ajaxUtils&util=getTemplate&name=' + encodeURIComponent(this.tableArgs.template),
                        onSuccess: function(txt) {
                            this.template = txt;
                            delete this['_templateRequest'];
                        }.bind(this)
                    }).send();
                }
                this.newPage.delay(100, this);
                return;
            }
            var editor = new Editor({
                content: this.template,
                name: this.tableArgs.nametemplate,
                template: this.tableArgs.template
            });

            editor.addEvent('success', function() {
                this.refresh();
            }.bind(this));

        },

        refresh: function() {
            if (this.inlineEditor) return;

            var oldMetas = Object.clone(this.metas);

            this.metaRequest = new Request.HTML({
                url: '?action=showMetaTable',
                data: 'args=' + encodeURIComponent(this.tableArgs.args),
                evalScripts: false,
                onSuccess: function(nodes) {
                    var tab = $$(nodes).filter(function(n){
                        return typeOf(n.getElement) == "function";
                    }).getElement('table').clean();

                    if (tab.length != 1) return; //todo: show error message
                    this.setTable(tab[0]);
                    this.reSort();
                    this.hiddenCells.each(this.hide, this);

                    this.metas = retrieveMetas(this.body);

                    var highlightChanges = function() {
                        diff(oldMetas, this.metas).each(function(page) {
                            this.body.getElements('tr').each(function(row) {
                                if (row.cells[0].get('text') == page) {
                                    row.highlight("#bfb");
                                }
                            });
                        }, this);
                    }.bind(this);

                    highlightChanges.delay(500);
                }.bind(this)

            }).get();
        }
    });


    var Editor = new Class({
        Extends: Overlay,
        options: {
            content: "",
            name: "",
            template: ""
        },

        build: function() {
            this.parent();

            var form = new Element('form').inject(this.editor);

            var namefield = new Element('input[name=pagename][placeholder=Page Name]')
                .set('value', new Date().format(this.options.name))
                .setStyles({'width': '200px', 'margin-left': '20px'});

            form.adopt(
                new Element('span[text=Pagename: ]'),
                namefield,
                new Element('br'),
                new Element('br')
            );

            if (this.options.template) {
                var template = encodeURIComponent(this.options.template);
                new Element('a', {
                    'text': 'create in metaformedit',
                    'target': '_blank',
                    'href': namefield.get('value') + '?action=editmetaform&template=' + template,
                    'styles': {
                        'margin-left': '10px'
                    },
                    'events': {
                        'click': function() {
                            this.cancel();
                        }.bind(this)
                    }
                }).inject(namefield, 'after');
            }

            this.textarea = new Element('textarea', {
                'value': this.options.content,
                'styles': {
                    'width': '100%',
                    'margin': 'auto'
                }
            }).inject(form);

            new DynamicTextarea(this.textarea, {
                minRows: 20
            });

            var controls = new Element('div.clearfix').adopt(
                new Element('button', {
                    text: 'Save',
                    styles: {
                        'float': 'left'
                    },
                    events: {
                        'click': this.send.bind(this)
                    }
                })
            ).inject(this.container);
        },

        send: function() {
            var page = this.editor.getElement('input[name=pagename]').value;

            var data = {
                action: 'ajaxUtils',
                util: 'newPage',
                page: page,
                content: this.textarea.get('value')
            };

            new Request.JSON({
                url: page,
                method: 'post',
                data: Object.toQueryString(data),
                onSuccess: function(response) {
                    if (response && response.status == "ok") {
                        this.fireEvent('success');
                        this.cancel();
                    } else {
                        alert("Failed to create new page!\n" + '"' + response.msg + '"');
                    }
                }.bind(this)
            }).send();
        }
    });

    var InterMetaTable =  exports.InterMetaTable = new Class({
        Extends: HideableTable,

        options: {
            selector: "",
            baseurl: "",
            sortable: true,
            collabs: [""],
            keys: [],
            footer: false,
            inaccessibleCollabs: null
        },

        initialize: function(el, opts) {
            this.container = $(el);

            ["_format", "construct"].each(function(f) {
                this[f].bind(this);
            }, this);

            this.parent.apply(this, [null, opts]);

            if (typeOf(this.options.collabs) == "string") this.options.collabs = [this.options.collabs];
            if (typeOf(this.options.keys) == "string") this.options.keys = [this.options.keys];
            this.updateTable();
        },

        build: function() {
            this.parent();
            this.inject(this.container);

            this.container.addClass('waiting');

            var denied = this.options.inaccessibleCollabs;
            if (denied) {
                this.container.grab(new Element('em', {
                    text: 'You do not have premission to access following collab' +
                        (denied.length > 1 ? "s" : "") + ': ' + denied,
                    styles: {
                        color: 'red'
                    }
                }), 'top');
            }

            //this.container.grab(new Element('a.jslink[text=[settings]]'), 'bottom')
        },

        _format: function(vals, f) {
            if (typeOf(vals) != "array") vals = [vals];
            return vals.map(function(value) {
                return f[value] || value;
            }, this);
        },

        construct: function() {
            this.empty();

            var keys = {};
            Object.each(this.metas, function(pages, collab) {
                Object.each(pages, function(metas, page) {
                    Object.keys(metas).each(function(key) {
                        if (!keys[key]) keys[key] = this._format(key, this.formatted[collab]);
                    }, this);
                }, this);
            }, this);

            var foots = {};
            var sortedKeys;
            if (this.options.keys.length === 0) sortedKeys = Object.sortedKeys(keys);
            else sortedKeys = this.options.keys;

            sortedKeys.each(function(key) {
                foots[key] = 0;
            });

            //this.setHeaders(([new Element('a.jslink[text=edit]')].concat(Object.sortedValues(keys))));
            this.setHeaders([""].concat(sortedKeys.map(function(key){return keys[key];}).flatten()));
            this.thead.rows[0].addClass('meta_header');

            Object.each(this.metas, function(pages, collab) {
                Object.each(pages, function(metas, page) {
                    var vals = [new Element('a', {
                        text: (collab ? collab + ':' : "") + page,
                        href: this.options.baseurl + collab + '/' + page
                    })];

                    sortedKeys.each(function(key) {
                        if (!metas[key] || metas[key].length === 0) {
                            vals.push(" ");
                        } else {
                            vals.push(this._format(metas[key], this.formatted[collab]).join(", "));
                            if (Number.from(metas[key])) {
                                foots[key] += Number.from(metas[key]);
                            } else {
                                foots[key] = null;
                            }

                        }
                    }, this);

                    this.push(vals);
                }, this);
            }, this);

            $$(this.body.rows).getFirst('td').addClass('meta_page');
            $$($$(this.body.rows).getElements('td:not(.meta_page)')).addClass('meta_cell');

            this.sort(0, false);
            this.enableHiding();

            if (!this.isUpdating()) this.container.removeClass('waiting');
        },

        isUpdating: function() {
            if (!this.requests || this.requests.length === 0) return false;
            return this.requests.some(function(request) {
                return request.isRunning();
            });
        },

        updateTable: function() {
            if (this.isUpdating()) return;

            this.requests = [];
            this.options.collabs.each(function(collab) {
                this.requests.push(new Request.JSON({
                    url: this.options.baseurl + collab + '/?action=getMetaJSON',
                    data: 'args=' + encodeURIComponent(this.options.selector) + '&formatted=true',
                    onSuccess: function(json) {
                        if (!this.metas) this.metas = {};
                        if (!this.formatted) this.formatted = {};
                        this.metas[collab] = json.metas;
                        this.formatted[collab] = json.formatted;
                        this.construct();
                    }.bind(this)
                }).get());
            }, this);
        }
    });

//Use mootools document.id for $
})(document.id, window);
