/*
  AttachTree
 - js collapsing for attachment tree
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Author: Lauri Pokka
 Depends: MooTools Element.Delegation
 Provides: gwiki.AttachTree
 */
define([
    'mootools'
], function(){
    "use strict";

    return new Class({
        initialize: function(element) {
            this.element = document.id(element);

            //pre-bind some methods
            ["toggle"].each(function(method){
                this[method] = this[method].bind(this);
            }, this);

            this.attach();
        },

        attach: function() {
            this.element.addEvent('click:relay(.attachtree_direntry)', this.toggle)
        },

        detach: function() {
            this.element.removeEvent('click:relay(.attachtree_direntry)', this.toggle);
        },

        toggle: function(event) {
            var li = event.target;
            li.toggleClass('collapsed');
            li.getNext('.attachtree_list').toggleClass('hidden');
        }
    });
});