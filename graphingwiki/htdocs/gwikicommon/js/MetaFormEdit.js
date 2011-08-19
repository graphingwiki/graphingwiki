/*
 MetaFormEdit
 - js improvements for meta editor.
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2011 by Lauri Pokka
 Depends: MooTools DynamicTextArea
 */

(function() {
    if (this.MetaFormEdit) return;

    var dateformat = '%Y-%m-%d';

    var MetaformEdit = this.MetaFormEdit = new Class({
        initialize: function (form) {
            this.form = document.id(form);

            this.form.addEvent('submit', function() {
                this.getElements('.hidden').destroy();
                this.getElements('input[type=file][value=""]').filter(
                    function(inp) {
                        return inp.value == "";
                    }).destroy();
            });

            this.SEPARATOR = window.GWIKISEPARATOR;
            this.clean();
            this.build();
        },

        getFields: function() {
            return this.form.getElements('.metaformedit');
        },

        // Add dynamic scaling and automatic select hiding
        _setupTextArea: function(textarea) {
            var dd = textarea.getParent('dd');
            var dynText = new DynamicTextarea(textarea);
            var siblings = dd.getElements('select');
            siblings.removeClass('hidden');
            if (siblings.length > 0) {
                dynText.addEvent('keyPress', function() {
                    if (textarea.get('value') != "") {
                        siblings.addClass('hidden');
                    } else {
                        siblings.removeClass('hidden');
                    }
                })
            }

        },

        _bindLabel: function(label) {
            var input = label.getPrevious('input');
            var id = String.uniqueID();
            input.set('id', id);
            label.set('for', id);
        },

        build: function() {
            var self = this;

            //remove annoying title text on help icon
            this.form.getElements('dt img').each(function(img) {
                img.set('title', '');
            });

            //add '+'-button for each dt that has cloneable dd elements
            this.getFields().each(function(dd) {
                if (dd.get('data-cloneable') == "false") return;
                var dt = dd.getPrevious('dt');
                var siblings = dd.getParent().getChildren();
                if (siblings.indexOf(dd) - 1 != siblings.indexOf(dt)) return;
                dt.appendText(' ');
                dt.grab(new Element('a', {
                    'class': 'jslink',
                    'text': '+',
                    'title': 'Add value',
                    'styles': {
                        'font-weight': 'bold',
                        'font-size': '1.1em'
                    },
                    'events': {
                        'click': function() {
                            self.clone(dt.getNext('dd'));
                        }
                    }
                }));
            });

            //add 'x'-buttons for each row
            this.getFields().each(function(el) {
                el.grab(new Element('a', {
                    'class': 'jslink',
                    'title': 'Remove value',
                    'html': 'x',
                    'styles': {
                        'margin-left': '5px',
                        'color': 'red',
                        'font-weight': 'bold',
                        'font-size': '0.95em'
                    },
                    'events': {
                        'click': function() {
                            self.remove(this.getParent('dd'))
                        }
                    }
                }));
            });

            this.getFields().getElements('textarea').flatten().each(this._setupTextArea);
            this.getFields().getElements('label').flatten().each(this._bindLabel);

            new Picker.Date(this.getFields().getElements('input.date').flatten(), {
                format: dateformat,
                pickerClass: 'datepicker_dashboard'
            });

        },

        /*
         Tries to group values with same key under one section.
         */
        clean: function() {
            var keys = [];

            //value grouping
            this.getFields().each(function(el) {
                if (!el || el.getElement('input, select, textarea') == null) return;
                var key = el.getElement('input, select, textarea').name;

                //not the first appearance of this key -> group with previous one
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

            /* Set default values */
            this.getFields().each(function(dd) {
                var def = dd.get('data-default');
                if (!def) return;

                var chks = dd.getElements('input[type=checkbox],input[type=radio');
                var sel = dd.getElement('select');
                var inputs = dd.getElements('input, textarea');

                //handle checkbox/radio
                if (dd.getElement('input[checked]')) return;

                if (chks.length > 0) {
                    chks.each(function(el) {
                        if (el.get('value') == def) el.set('checked', true);
                    });

                    //handle selects
                } else if (sel) {
                    if (sel.get('value') == '') sel.set('value', def);
                    //handle rest text based fields
                } else if (inputs.length > 0) {
                    if (inputs.every(function(el) {
                        return el.get('value') == "";
                    })) {
                        inputs[0].set('value', def);
                    }
                }
            });
        },

        clone: function(source, values, minimalNew) {
            values = values || [];
            var first = source.getElement('input, select, textarea');
            var type = first.get('tag') == 'select' ? "select" : first.type;

            if (["checkbox", "radio"].contains(type)) {
                source.getElements('input[type=checkbox] ,input[type=radio]').each(function(input) {
                    if (values.contains(input.value)) {
                        input.checked = true;
                        values.erase(input.value);
                    }
                });
                if (source.getElement('textarea') == null || minimalNew) return;
            }

            if (["radio"])
                var cloned = source.clone();
            cloned.inject(source, 'before');

            if (cloned.getElement('a.jslink') != null) {
                cloned.getElement('a.jslink').cloneEvents(source.getElement('a.jslink'));
            }

            cloned.getElements('input[type=checkbox], input[type=radio], label').destroy();

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
                if (values.length > 0) {
                    input.set('value', values.pop());
                }

                if (!minimalNew) {
                    if (input.get('tag') == "textarea") {
                        var div = input.getParent('div');
                        var txt = new Element('textarea').set('name', input.get('name'))
                            .replaces(div);
                        this._setupTextArea(txt);
                    }

                    if (input.hasClass('date')) {
                        new Picker.Date(input, {
                            format: dateformat,
                            pickerClass: 'datepicker_dashboard'
                        })
                    }
                }


            }, this);

            cloned.getElements('label').each(this._bindLabel);
        },

        remove: function(el) {
            var siblings = el.getParent().getChildren();
            var index = siblings.indexOf(el);

            // remove key title and create an empty hidden input for key if we are deleting the last value
            if (siblings[index - 1].get('tag') == "dt"
                && (!siblings[index + 1] || siblings[index + 1].get('tag') == "dt")) {
                siblings[index - 1].destroy();
                var name = el.getElement('input, textarea').get('name');
                el.grab(new Element('input[type=hidden]').set('name', name), 'after');
            }
            el.destroy();
        }
    });

})();
