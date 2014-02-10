/**
 * Overlay
 * - Customizable overlay widget with nice opacity
 */
define([
    'mootools'
], function() {
    "use strict";
    return new Class({
        Implements: [Events, Options],
        options: {
            width: '80%',
            onBuild: function() {
            }
        },

        initialize: function(options) {
            this.setOptions(options);
            this.build();
        },

        build: function() {
            this.bg = new Element('div.alphabg').setStyles({
                'position': 'absolute',
                'left': 0,
                'top': 0,
                'width': document.id(window).getScrollSize().x,
                'min-height': document.id(window).getScrollSize().y,
                'z-index': '999'
            }).inject(document.body);

            this.positioner = new Element('div').setStyles({
                'position': 'absolute',
                'left': 0,
                'top': 0,
                'width': '100%',
                'z-index': '999'
            }).inject(document.body);
            this.container = new Element('div').setStyles({
                'position': 'relative',
                'margin': 'auto',
                'top': document.id(window).getScroll().y + 100,
                'padding': '15px',
                'width': this.options.width,
                'background': 'white',
                'border': '2px black solid',
                'border-radius': '5px'
            }).inject(this.positioner);

            var close = new Element('button.close-button', {html: '&times;'})
                .addEvent('click', this.cancel.bind(this))
                .inject(this.container);

            this.editor = new Element('div').setStyles({
                'min-height': '200px'
            }).inject(this.container);

            this.fireEvent('build');
        },

        cancel: function() {
            this.bg.destroy();
            this.positioner.destroy();
        }
    });

});