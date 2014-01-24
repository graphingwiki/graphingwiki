/*
 InlineEditor
 */
define([
    './MetaSuggestions',
    './DynamicTextarea',
    './MetaRequest',
    'config',
    'mootools'
],
    function(
        MetaSuggestions,
        DynamicTextarea,
        Request,
        config
        ) {
        "use strict";

        var GwikiDynamicTextarea = DynamicTextarea.GwikiDynamicTextarea,
            DynamicTextarea = DynamicTextarea.DynamicTextarea,
            dateformat = config.dateformat;

        return new Class({
            Implements: [Events, Options],

            options: {
                //onSave: function(value){},
                //onExit: function(){}
                //onCancel: function(){}
                oldValue: "",
                inline: true, //puts all controls on the same row if enabled
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
                        url: '?action=ajaxUtils&util=getProperties&key=' + encodeURIComponent(this.options.key),
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

                if (this.options.inline) this.element.addClass('inline nowrap');

                var oldVal = this.options.oldValue;
                var type = this._keyProperties.hint;
                if (type == "date") {
                    this.input = new Element('input', {
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
                    new Request.GetMetas({
                        onSuccess: function(json) {
                            input.removeClass('waiting');
                            var vals = [];
                            Object.each(json, function(metas, page) {
                                Object.each(metas, function(values, key) {
                                    vals.combine(values);
                                });
                            });

                            vals.each(function(value) {
                                input.grab(new Element('option', {
                                    value: value,
                                    text: value,
                                    selected: (value == oldVal)
                                }));
                            });
                        }
                    }).get(this.options.key, true);
                } else {
                    this.input = new Element('textarea', {
                        text: oldVal,
                        cols: this.options.width
                    }).inject(this.element);

                    this.input.addEvent('keydown', function(e) {
                        if (e && e.key == "esc") this.cancel();
                    }.bind(this));

                    var field = this.options.size == "compact" ? DynamicTextarea : GwikiDynamicTextarea;
                    new field(this.input).addEvent('resize', function() {
                        this.input.fireEvent('resize');
                    }.bind(this));

                    if (this.options.key) {
                        this.suggestions = new MetaSuggestions(this.input, {
                            key: this.options.key
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
                    }));
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
                this.element.removeClass('nowrap');
            },

            exit: function() {
                if (this.suggestions) this.suggestions.exit();

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
                if (this.suggestions) this.suggestions.exit();

                this.element.empty();
                this.element.set('html', this.element.retrieve('html'));
                this._clean();
                this.fireEvent('cancel');
                this.fireEvent('exit');
            }
        });
    });