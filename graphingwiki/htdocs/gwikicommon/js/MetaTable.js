/*
 MetaTable.js
 - js improvements for MetaTable
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Author: Lauri Pokka
 Depends: MooTools HtmlTable.sort InlineEditor Request.SetMetas Events.shiftclick More/Date
 provides: [gwiki.MetaTable, gwiki.InterMetaTable]
 */
define([
    './InlineEditor',
    './DynamicTextarea',
    './Overlay',
    'mootools-more'

], function(InlineEditor, dt, Overlay) {
    "use strict";

    var DynamicTextarea = dt.DynamicTextarea,
        $ = document.id;

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
                    if (!values2 || !values.every(values2.contains.bind(values2)) || !values2.every(values.contains.bind(values)))
                        changed.include(page);
                });
            }
        });
        return changed;

    };

    var retrieveMetas = function(tbody) {
        var metas = {};
        tbody.getElements('tr').each(function(row) {
            var page = row.getElement('.meta_page');
            if (page) page = page.get('text');
            if (page && !metas[page]) metas[page] = {};

            var vals = {};

            row.getElements('.meta_cell span[data-key]').each(function(span) {
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
        HtmlTable.ParserPriority.splice(0, 0, "numberSpan")
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

    var EditableTable = new Class({
        enableValueEdit: function() {
            var selectors = [".meta_cell span[data-key]:not(.edit)", ".meta_cell:not(.edit)"];
            this.body.addEvent('shiftclick:relay(' + selectors.join(", ") + ')', this.valueEdit.bind(this));
        },
        enableKeyEdit: function() {
            this.head.addEvent('shiftclick:relay(span[data-key])', this.keyEdit.bind(this));
        },

        isUpdating: function() {
            return false;
        },

        valueEdit: function(event) {
            event.preventDefault();

            if (this.isUpdating()) {
                this.valueEdit.delay(100, this, event);
                return;
            }

            var target = $(event.target),
                baseUrl = this.options.baseurl,
                key, index, page, collab, oldValue = "", metas;

            if (target.get('tag') == 'td') {
                //add new value, page and key can be retrieved from first span
                if (target.children.length > 0) {
                    var first = target.getElement('span');
                    page = first.get('data-page');
                    key = first.get('data-key');
                    collab = first.get('data-collab');
                    metas = collab ? this.metas[collab] : this.metas;

                    //only one span without value => use that span
                    if (target.children.length == 1 && first.get('text') === "") {
                        index = 0;
                        target = first;
                    } else {
                        //append new value to existing ones if key had values
                        index = metas[page][key].length;
                        target = new Element('span').inject(target);
                    }
                } else {
                    return;
                }

            } else {
                //edit existing value
                if (!target.get('data-key')) target = target.getParent('span[data-key]');

                page = target.get('data-page');
                key = target.get('data-key');
                index = target.get('data-index');
                collab = target.get('data-collab');
                metas = collab ? this.metas[collab] : this.metas;
                oldValue = metas[page][key][index];
            }

            if (this.inlineEditor) this.inlineEditor.cancel();

            var editor = this.inlineEditor = new InlineEditor(target, {
                autoFormat: false,
                oldValue: oldValue,
                key: key,
                compact: true,

                onSave: function(value) {
                    new Request.SetMetas2({
                        url: (collab && baseUrl) ? baseUrl + collab + "/" : "",
                        onComplete: function() {
                            this.refresh([collab]);
                        }.bind(this)
                    }).send([
                            {op: 'del', key: key, value: oldValue, page: page},
                            {op: 'add', key: key, value: value, page: page}
                        ]);

                    this.inlineEditor = null;
                    editor.exit();
                }.bind(this)
            });
        },

        keyEdit: function(event) {
            event.stopPropagation();
            event.preventDefault();

            if (this.isUpdating()) {
                this.keyEdit.delay(100, this, event);
                return;
            }

            var target = $(event.target);

            if (!target.get('data-key')) target = target.getParent('span[data-key]');
            var oldKey = target.get('data-key');

            //check that the key is really meta-key and not indirection
            if (!Object.some(this.metas, function(metas, page) {
                return metas[oldKey];
            })) return;

            if (this.inlineEditor) this.inlineEditor.cancel();

            var parent = target.getParent('td').addClass('edit');

            var editor = this.inlineEditor = new InlineEditor(target, {
                autoFormat: false,
                oldValue: oldKey,
                compact: true,
                onSave: function(newKey) {
                    var changes = [];
                    Object.each(this.metas, function(metas, page) {
                        if (metas[oldKey]) {
                            changes.push({op: 'set', page: page, key: oldKey});
                            changes.push({op: 'add', page: page, key: newKey, value: metas[oldKey]});
                        }
                    });

                    new Request.SetMetas2({
                        onComplete: function() {
                            this.refresh();
                        }.bind(this),
                        onFailure: function() {
                            alert("Could not edit the key!");
                        }.bind(this)
                    }).send(changes);

                    this.inlineEditor = null;
                    editor.exit();
                }.bind(this),
                onExit: function() {
                    parent.removeClass('edit');
                }
            });
        }
    });

    var MetaTable = new Class({
        Extends: HideableTable,
        Implements: [EditableTable],

        options: {
            thSelector: 'td.head_cell:not(.edit)',
            tableArguments: {}
        },

        initialize: function(container, options) {
            container = $(container);
            var table = container.getElement('table');
            preformatTable(table);
            this.parent.call(this, table, options);

            this.tableArgs = Object.merge({
                'args': '',
                'template': null,
                'autorefresh': false,
                'nametemplate': ''
            }, this.options.tableArguments);

            this.metaRequest = new Request.HTML();
            this.metas = retrieveMetas(this.body);

            this.enableValueEdit();
            this.enableKeyEdit();


            if (this.tableArgs.autorefresh) {
                this.refresh.periodical(this.tableArgs.autorefresh * 1000, this, null);
            }

            if (container.getElement('.meta_footer_link')) {
                new Element('a.jslink[text=[new row]]')
                    .setStyles({'font-size': 'inherit'})
                    .addEvent('click', this.newPage.bind(this))
                    .inject(container.getElement('.meta_footer_link'), 'before');
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

        isUpdating: function() {
            return this.metaRequest.isRunning();
        },

        refresh: function() {
            if (this.inlineEditor) return;

            var oldMetas = Object.clone(this.metas);

            this.metaRequest = new Request.HTML({
                url: '?action=showMetaTable',
                data: 'args=' + encodeURIComponent(this.tableArgs.args),
                evalScripts: false,
                onSuccess: function(nodes) {
                    var tab = $$(nodes).filter(function(n) {
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
                new Element('button.btn.btn-primary', {
                    text: 'Save',
                    styles: {
                        'float': 'left',
                        'margin-top': '10px'
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
                url: "",
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

    var InterMetaTable = new Class({
        Extends: HideableTable,
        Implements: [EditableTable],

        options: {
            selector: "",
            baseurl: "",
            sortBy: "",
            sortDir: 'asc',
            collabs: [""],
            keys: [],
            footer: false,
            inaccessibleCollabs: null,
            action: "getMetaJSON"
        },

        initialize: function(el, opts) {
            this.container = $(el);

            ["_format", "construct"].each(function(f) {
                this[f].bind(this);
            }, this);

            this.parent.apply(this, [null, opts]);

            this.enableSort();
            this.enableValueEdit();

            ["sortBy", "sortDir"].forEach(function(key) {
                if (typeOf(this.options[key]) == "array") this.options[key] = this.options[key][0];
            }, this);

            this.refresh();
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
            if (this.options.keys.length === 0) {
                sortedKeys = Object.sortedKeys(keys);
            } else {
                sortedKeys = this.options.keys;
                sortedKeys.forEach(function(key) {
                    if (!keys[key]) keys[key] = key
                });
            }

            sortedKeys.each(function(key) {
                foots[key] = 0;
            });

            //this.setHeaders(([new Element('a.jslink[text=edit]')].concat(Object.sortedValues(keys))));
            keys = [""].concat(sortedKeys.map(function(key) {
                return keys[key];
            }).flatten());

            this.setHeaders(keys);
            this.thead.rows[0].addClass('meta_header');

            var genEl = function(collab, page, key, index, html) {
                return new Element('span', {
                    'html': html,
                    'data-collab': collab,
                    'data-page': page,
                    'data-key': key,
                    'data-index': index
                });
            };

            Object.each(this.metas, function(pages, collab) {
                var pagePrefix = this.options.collabs.length == 1
                    && this.options.collabs[0] == this.options.active ?
                     "": collab + ':';

                Object.each(pages, function(metas, page) {

                    var vals = [new Element('a', {
                        text: pagePrefix + page,
                        href: this.options.baseurl + collab + '/' + page
                    })];

                    sortedKeys.each(function(key) {
                        if (!metas[key] || metas[key].length === 0) {
                            vals.push(genEl(collab, page, key, 0, ""));
                        } else {
                            var formatted = this._format(metas[key], this.formatted[collab]);
                            vals.push(formatted.map(function(html, index) {
                                return genEl(collab, page, key, index, html).outerHTML;
                            }).join(", "));

                            if (Number.from(metas[key])) {
                                foots[key] += Number.from(metas[key]);
                            } else {
                                foots[key] = null;
                            }


                        }
                    }, this);

                    this.push(new Element('tr').adopt(
                        vals.map(function(el) {
                            return new Element('td', {
                                html: el.outerHTML ? el.outerHTML : el
                            })
                        })
                    ));
                }, this);
            }, this);

            $$(this.body.rows).getFirst('td').addClass('meta_page');
            $$($$(this.body.rows).getElements('td:not(.meta_page)')).addClass('meta_cell');

            this.sort(keys.indexOf(this.options.sortBy), this.options.sortDir == "desc");
            this.enableHiding();

            if (!this.isUpdating()) this.container.removeClass('waiting');
        },

        isUpdating: function() {
            if (!this.requests || this.requests.length === 0) return false;
            return this.requests.every(function(request) {
                return request.isRunning();
            });
        },

        refresh: function(collabs) {
            collabs = collabs || this.options.collabs;
            this.requests = [];
            collabs.each(function(collab) {
                this.requests.push(new Request.JSON({
                    url: this.options.baseurl + collab + '/?action=' + this.options.action,
                    data: 'args=' + encodeURIComponent(this.options.selector) + '&formatted=true',
                    onSuccess: function(json) {
                        if (!this.metas) this.metas = {};
                        if (!this.formatted) this.formatted = {};
                        this.metas[collab] = json.metas;
                        this.formatted[collab] = json.formatted;
                        this.construct();
                    }.bind(this),
                    onFailure: function(xhr) {
                        this.empty();
                        this.container.removeClass('waiting');
                        this.push(new Element('tr').grab(
                            new Element('td').set('text', xhr.responseText)
                        ));
                    }.bind(this)
                }).get());
            }, this);
        }
    });

    return {
        MetaTable: MetaTable,
        InterMetaTable: InterMetaTable
    };
});
