/*
  Banner
 - Add dismissing support for Gwiki Banners
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Author: Lauri Pokka
 */
define([
    'mootools'
], function(){
    "use strict";

    return new Class({
        initialize: function(element) {
            this.element = document.id(element);
            this.name = 'dismissed.' + this.element.get('data-bannername');
            this.dismiss = this.dismiss.bind(this);
            if (!localStorage.getItem(this.name)){
                this.build();
                this.attach();
            }
        },

        build: function(){
            this.element.addClass('show');
            if (!this.element.getElements('.dismiss').length){
                this.element.grab(new Element('a.dismiss.glyphicon.glyphicon-remove[title=Dismiss]')
                    .grab(new Element('span.fallback[text=x]')))
            }
        },

        attach: function() {
            this.element.addEvent('click:relay(.dismiss)', this.dismiss)
        },

        detach: function() {
            this.element.removeEvent('click:relay(.dismiss)', this.dismiss);
        },

        destroy: function(){
            this.detach();
            this.element.destroy();
        },

        dismiss: function() {
            localStorage.setItem(this.name, true);
            this.destroy();
        }
    });
});