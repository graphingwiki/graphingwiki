/*
 MetaTable.js
 - js improvements for MetaTable
  License:	MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2011 by Lauri Pokka
 Depends: MooTools HtmlTable.sort InlineEditor Request.SetMetas Events.shiftclick
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
