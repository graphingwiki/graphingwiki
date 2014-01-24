/*
 MetaSuggestions
 - Folcsonomic meta suggestion widget.
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Author: Lauri Pokka
 Depends: MooTools
 Provides: MetaSuggestions
 */
define([
    './MetaRequest',
    'mootools'
], function(Request) {
    "use strict";

    var SuggestionList = new Class({

        Implements: Events,

        rows: [],

        initialize: function(parent) {
            this.parent = parent;

            this.bound = {
                control: this._control.bind(this),
                select: this._select.bind(this),
                show: this.show.bind(this)
            };
            this.build();
            this.attach();
        },

        build: function() {
            this.element = new Element('div.hidden.ac-results');
            this.table = new Element('table').inject(this.element);
            this.element.inject(document.body);
        },

        position: function(pos) {
            this.element.setPosition(pos);
            this.table.setStyle('width', pos.w);
            return this;
        },

        _control: function(e) {
            if (["up", "down"].contains(e.key)) {
                var selected = this.element.getElement('.selected'), i;
                if (!selected) i = 0;
                else {
                    i = this.rows.indexOf(selected);
                    i += e.key == "down" ? 1 : -1;
                }
                this.element.getElements('.selected').removeClass('selected');

                if (i >= 0 && i < this.rows.length) {
                    this.rows[i].addClass('selected');
                }
                return false;
            }
        },

        _select: function () {
            this.fireEvent('select', this.getSelected());
        },

        attach: function () {
            document.id(window).addEvent('keydown', this.bound.control);
            this.element.addEvent('click', this.bound.select);
            return this;
        },

        detach: function () {
            document.id(window).removeEvent('keydown', this.bound.control);
            this.element.removeEvent('click', this.bound.select);

            return this;

        },

        getSelected: function() {
            var selected = this.element.getElement('.selected');
            if (!selected) return null;
            else return selected.retrieve('item');
        },

        show: function(data) {
            this.element.removeClass('waiting');
            
            if (data.length == 0) {
                this.hide();
                return;
            }

            if (this.element.hasClass('hidden')) this.attach();

            this.table.empty();
            this.element.removeClass('hidden');

            this.rows = [];
            var tbody = new Element('tbody').inject(this.table);

            data.each(function(item) {
                var tr = new Element('tr').inject(tbody);
                var pages = item.page.join(", ");
                pages = pages.length > 15 ? pages.slice(0, 15) + "..." : pages;
                tr.adopt(new Element('td.value').set('text', item.value),
                    new Element('td.page').set('text', pages));
                tr.store('item', item);
                tr.addEvent('mouseenter', function() {
                    tbody.getElements('.selected').removeClass('selected');
                    tr.addClass('selected');
                });
                this.rows.push(tr);
            }, this);

            if (this.rows.length == 1) this.rows[0].addClass('selected');

            if (this.element.getSize().y < this.table.getSize().y) this.element.setStyle('overflow-y', 'scroll');
        },

        waiter: function(){
            this.table.empty();
            this.element.removeClass('hidden');
            var tbody = new Element('tbody').inject(this.table);
            tbody.grab(new Element('tr').grab(new Element('td').set('html', '&nbsp;')));
            this.element.addClass('waiting');
        },

        hide: function(delay) {
            var fn = function() {
                this.rows = [];
                this.table.empty();
                this.detach();
                this.element.addClass('hidden');
                this.element.removeClass('waiting');
            }.bind(this);
            if (delay) fn.delay(delay);
            else fn.call();
        }

    });

    var SuggestionText = new Class({
        initialize: function(parent) {
            this.parent = document.id(parent);
            this.parent.setStyles({
                'z-index': 1,
                'background': 'transparent'
            });
            this.element = new Element('textarea.hidden')
                .set('rows', 1)
                .setStyles({
                'position': 'absolute',
                'border': 'none',
                'color': 'gray',
                'padding': '3px',
                'resize': 'none',
                '-moz-resize': 'none',
                '-webkit-resize': 'none',
                'background': 'transparent',
                'overflow': 'hidden'
            });

            this.element.inject(document.body);

            this.position();
        },

        position: function() {
            this.element.setStyle('width', this.parent.getSize().x);
            this.element.setPosition(this.parent.getPosition());
        },

        show: function(text) {
            this.element.removeClass('hidden');
            this.element.set('text', text);
            return this;
        },

        hide: function() {
            this.element.addClass('hidden');
            return this;
        }

    });


    var MetaSuggestions = new Class({
        Implements: [Options, Events],

        options: {
            count: 10,
            url: '',
            limitToExisting: false,
            suggestions: null, // ["value1", "value2"]
            showOnEmpty: true,
            key: '',
            onSelect: function() {
            }
        },

        initialize: function(el, options) {
            this.field = document.id(el);
            this.setOptions(options);

            this.list = new SuggestionList(this);
            this.overlayText = new SuggestionText(el);
            this._resize();

            this.bound = {
                resize: this._resize.bind(this),
                change: this._change.bind(this),
                focus: this._focus.bind(this),
                select: this.select.bind(this),
                hide: this._blur.bind(this)
            };

            if (this.options.suggestions) {
                this.suggestions = this.options.suggestions.map(function(val){
                    return {"value": val, "page": []};
                });
            } else {
                this.request = new Request.GetMetas({
                    onSuccess: function(json) {
                        var suggestions = this.suggestions = [];
                        Object.each(json, function(metas, page) {
                            Object.each(metas, function(values, key){
                                values.each(function(value) {
                                    if (suggestions.every(function(sug) {
                                        if (sug.value == value) {
                                            sug.page.push(page);
                                        } else {
                                            return true;
                                        }
                                    })) {
                                        suggestions.push({"value": value, "page": [page]})
                                    }
                                });
                            });
                        });
                    }.bind(this)
                }).get(this.options.key, true);
            }

            this.attach();
        },
        _resize: function() {
            var pos = this.field.getPosition();
            var size = document.id(this.field).getSize();
            this.list.position({x:pos.x, y: pos.y + size.y + 1 , w: size.x});
            this.overlayText.position();
        },

        _focus: function() {
            if (this.value != null) this.query(this.value);
        },

        _blur: function() {
            this.list.hide(200);
            this.overlayText.hide();
        },
        _change: function (e) {
            if (e && ["enter", "tab", "right"].contains(e.key)) {
                var value = this.list.getSelected();
                if (value && value.value) {
                    this.select(value.value);
                    e.stopPropagation();
                    e.preventDefault();
                    this.field.fireEvent('keypress');
                    return false;
                }
            } else {
                if (this.value == null) this.value = this.field.value;
                this._delayedChange.delay(1, this);
            }
        },

        _delayedChange: function() {
            var s = this.field.value;

            var sel = this.list.getSelected();

            if (sel) this.overlayText.show(sel.value);
            else this.overlayText.hide();

            if (s == this.value) return;

            if (this.options.limitToExisting &&
                !this.request.isRunning() &&
                this.suggestions.filter(
                    function(value) {
                        return value.value.test('^' + s.escapeRegExp(), "i");
                    }).length < 1) {
                this.field.set('value', this.value);
                return;
            }

            this.value = s;
            if (s || this.options.showOnEmpty) {
                this.query(s);
                this.bound.resize.delay(10);
            } else {
                this.list.hide();
            }
        },

        select: function(value) {
            value = value.value || value;
            this.field.value = value;
            this.field.fireEvent('keypress');
            this.field.blur();
            this.overlayText.hide();
            this.fireEvent('select', value)
        },


        attach: function() {
            this.field.addEvent('keydown', this.bound.change);
            this.field.addEvent('keypress', this.bound.change);
            this.field.addEvent('blur', this.bound.hide);
            this.field.addEvent('focus', this.bound.focus);
            this.list.addEvent('select', this.bound.select);
            this.field.addEvent('resize', this.bound.resize);
        },

        detach: function() {
            this.bound.hide();
            this.field.removeEvent('keydown', this.bound.change);
            this.field.removeEvent('keypress', this.bound.change);
            this.field.removeEvent('blur', this.bound.hide);
            this.field.removeEvent('focus', this.bound.focus);
            this.list.removeEvent('select', this.bound.select);
            this.field.removeEvent('resize', this.bound.resize);

        },

        query: function(needle) {
            if (this.request && this.request.isRunning()) {
                if (this._delayed) clearTimeout(this._delayed);
                this._delayed = this.query.delay(100, this, needle);
                this.list.waiter();
                return;
            }

            var suggestions = this.suggestions.filter(function(value) {
                return value.value.test('^' + needle.escapeRegExp());
            });
            //if (suggestions.length > this.options.count) suggestions = suggestions.slice(0, this.options.count);
            this.list.show(suggestions)
        },

        exit: function() {
            if (this.request.isRunning()) this.request.cancel();
            this.detach();
        }
    });

    return MetaSuggestions;

});