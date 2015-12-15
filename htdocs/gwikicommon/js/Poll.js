/*
 Poll.js
 - UI for Poll macro
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Author: Lauri Pokka
 */
define([
    './MetaRequest',
    'mootools'

], function(Request) {
    "use strict";

    var genIcon = function(checked, key) {
        return new Element('i', {
            'class': 'glyphicon ' + (checked ? "glyphicon-ok" : ""),
            'data-key': key,
            'data-checked': checked,
            'styles': {
                color: checked ? "green" : "red"
            }
        }).grab(new Element('span.fallback').set('text', checked ? 'x' : ''))
    };

    return new Class({
        Implements: [Options],
        options: {

        },

        initialize: function(element, opts) {
            this.setOptions(opts);
            this.element = document.id(element);
            this.metas = {};
            this.rows = {};

            ["addRow", "removeRow", "toggleEdit", "save", "checkEdit"].each(function(method) {
                this[method] = this[method].bind(this);
            }, this);

            this.build();
            this.update();
        },

        build: function() {
            var table = this.table = new Element('table').inject(this.element);
            var head = new Element('tr.header').inject(
                new Element('thead').inject(table)
            );
            this.body = new Element('tbody').inject(table);

            this.footer = new Element('tr').inject(
                new Element('tfoot').inject(table)
            );


            [""].concat(this.options.keys).forEach(function(key) {
                head.grab(new Element('th').set('text', key));
            });

        },

        addRow: function() {
            var row = new Element('tr').inject(this.body);
            var name = this.options.username;

            var names = this.rows;
            var check = function() {
                if (names[this.value]) {
                    this.addClass('invalid');
                } else {
                    this.removeClass('invalid');
                }
            };
            var inp = new Element('input[type=text]').set('value', name);
            inp.addEventListener('blur', check);
            inp.addEventListener('keyup', check);

            var els = [new Element('div').grab(new Element('span').grab(inp))];

            this.options.keys.forEach(function(key) {
                els.push(new Element('input', {
                    type: 'checkbox',
                    value: key
                }))
            });

            els.forEach(function(el) {
                row.grab(new Element('td').grab(el));
            });

            row.getElement('div').grab(
                new Element('a.jslink.glyphicon.glyphicon-trash')
                    .grab(new Element('span.fallback[text=del]'))
                    .addEvent('click', function() {
                        row.destroy();
                        this.checkEdit();
                    }.bind(this))
            );

            inp.select();

            this.checkEdit();

        },

        removeRow: function(e) {
            var parent = e.target.getParent('tr');
            parent.toggleClass('delete');

            this.checkEdit();

        },

        toggleEdit: function(e) {
            var tr = e.target.getParent('tr');
            var name = tr.getElement('td .name').get('text');
            var icons = tr.getElements('i');
            if (icons.length) {
                icons.forEach(function(i) {
                    var chk = i.get('data-checked');
                    var key = i.get('data-key');
                    new Element('input[type=checkbox]', {
                        value: key,
                        checked: chk
                    }).replaces(i);

                })
            } else {
                tr.getElements('input').forEach(function(inp) {
                    var key = inp.get('value');
                    genIcon(this.rows[name][key], key).replaces(inp)
                }, this);

            }
            this.checkEdit();
        },

        save: function() {
            var metas = this.metas;
            var ops = [];

            if (this.table.getElement('.invalid')) {
                alert("Cannot save duplicate vote for " +this.table.getElement('.invalid').get('value'));
                return
            }

            var add = function(value, key) {
                if (metas[key].indexOf(value) == -1) {
                    ops.push({op: 'add', key: key, value: value});
                    metas[key].push(value);
                }
            };
            var rm = function(value, key) {
                var i = (metas[key] || []).indexOf(value);
                if (i != -1) {
                    metas[key].splice(i, 1);
                    ops.push({op: 'del', key:key, value:value});
                }
            };

            this.body.getElements('input[type=checkbox]').forEach(function(el) {
                var parent = el.getParent('tr'), name;
                if (parent.getElement('input[type=text]')) {
                    name = parent.getElement('input[type=text]').get('value');
                } else {
                    name = parent.getElement('span').get('text');
                }

                var key = el.get('value');
                if (el.get('checked')) {
                    if (!metas[key])  metas[key] = [];
                    add(name, key);
                } else {
                    rm(name, key);
                }
            });

            this.body.getElements('.delete').forEach(function(tr) {
                var name = tr.getElement('.name').get('text');
                this.options.keys.forEach(function(key) {
                    rm(name, key);
                })
            }, this);

            new Request.SetMetas2({
                url: this.options.pageurl,
                onSuccess: function() {
                    this.update();
                }.bind(this)
            }).send(ops);

        },

        checkEdit: function() {
            if (this.body.getElements('.delete, input[type=checkbox]').length) {
                this.table.addClass('edit');
            } else {
                this.table.removeClass('edit');
            }
        },

        update: function() {

            new Request.JSON({
                url: this.options.pageurl + '?action=getMetaJSON',
                onSuccess: function(results) {
                    this.body.empty();
                    this.table.removeClass('edit');
                    this.footer.empty();
                    this.metas = Object.filter(results[Object.keys(results)[0]], function(meta, key) {
                        return this.options.keys.indexOf(key) != -1;
                    }, this);
                    var rows = this.rows = {};

                    var votes = this.options.keys.map(function() {
                        return 0
                    });

                    Object.each(this.metas, function(voters, key) {
                        voters.forEach(function(voter) {
                            if (!rows[voter]) rows[voter] = {};
                            rows[voter][key] = true;
                            votes[this.options.keys.indexOf(key)]++;
                        }, this);
                    }, this);

                    Object.each(rows, function(votes, voter) {
                        var tr = new Element('tr').inject(this.body);
                        tr.grab(new Element('td').grab(new Element('div').adopt(
                            new Element('span.name').set('text', voter),
                            new Element('a.jslink.glyphicon.glyphicon-pencil')
                                .grab(new Element('span.fallback[text=edit]'))
                                .addEvent('click', this.toggleEdit),
                            new Element('a.jslink.glyphicon.glyphicon-trash')
                                .grab(new Element('span.fallback[text=del]'))
                                .addEvent('click', this.removeRow)
                        )));
                        this.options.keys.forEach(function(key) {
                            tr.grab(new Element('td').grab(
                                genIcon(votes[key], key)
                            ));
                        });
                    }, this);

                    this.footer.adopt(
                        new Element('td').grab(new Element('div').adopt(
                            new Element('a.jslink.glyphicon.glyphicon-plus.add', {
                                events: {
                                    click: this.addRow
                                }
                            }).grab(new Element('span.fallback[text=+]')),
                            new Element('span'),
                            new Element('input.btn.btn-primary.save', {
                                type: 'button',
                                value: 'save',
                                events: {
                                    click: this.save
                                }
                            })
                        )
                        ));

                    votes.forEach(function(vote) {
                        this.footer.grab(new Element('td').set('text', vote));
                    }, this);

                }.bind(this)
            }).get();
        }
    });
});
