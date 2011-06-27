/*
   MetaFormEdit
   - js improvements for meta editor.
   License: MIT <http://www.opensource.org/licenses/mit-license.php>
   Copyright: 2011 by Lauri Pokka
   Depends: MooTools DynamicTextArea
 */

(function() {
    if (this.MetaFormEdit) return;

    var MetaformEdit = this.MetaFormEdit = new Class({
        initialize: function (form) {
            this.form = document.id(form);
            this.fields = this.getFields();

            this.form.addEvent('submit', function(){
               this.getElements('.hidden').destroy();
            });
            
            this.SEPARATOR = window.GWIKISEPARATOR;
            this.clean();
            this.build();
        },

        getFields: function() {
            return this.form.getElements('.metaformedit-cloneable, .metaformedit-notcloneable');
        },

        _setupTextArea: function(textarea){
            var dd = textarea.getParent('dd');
            var dynText = new DynamicTextarea(textarea);
            var siblings = dd.getElements('select, input, label');
            siblings.removeClass('hidden');
            if (siblings.length > 0){
                dynText.addEvent('keyPress', function(){
                    if (textarea.get('value') != "") {
                        siblings.addClass('hidden');
                    }else{
                        siblings.removeClass('hidden');
                    }
                })
            }

        },

        _bindLabel: function(label){
            var input = label.getPrevious('input');
            var id = String.uniqueID();
            input.set('id', id);
            label.set('for', id);
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

            this.fields.getElements('textarea').flatten().each(this._setupTextArea);
            this.fields.getElements('label').flatten().each(this._bindLabel);

            new Picker.Date(this.fields.getElements('input.date').flatten(), {
                format: '%d-%m-%Y',
                pickerClass: 'datepicker_dashboard'
            });

            this.fields = this.getFields();
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
                if (values.length > 0) {
                    input.set('value', values.pop());
                }

                if (!minimalNew) {
                    source.getElements('textarea').each(function(textarea) {
                        var div = textarea.getParent('div');
                        textarea.dispose();
                        textarea.replaces(div);
                        this._setupTextArea(textarea);
                    }, this);

                    if (input.hasClass('date')) {
                        new Picker.Date(input, {
                            format: '%d-%m-%Y',
                            pickerClass: 'datepicker_dashboard'
                        })
                    }
                }


            }, this);

            cloned.getElements('label').each(this._bindLabel);
            
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

})();
