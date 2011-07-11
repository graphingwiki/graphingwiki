/*
  AttachTree
 - js collapsing for attachment tree
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2011 by Lauri Pokka
 Depends: MooTools Element.Delegation
 */

(function(exports) {
    exports.AttachTree = new Class({
        initialize: function(element) {
            this.element = document.id(element);

            //pre-bind some methods
            ["toggle"].each(function(method){
                this[method] = this[method].bind(this);
            }, this);

            //this.build();
            this.attach();
        },

        build: function() {
            this.element.getElements('.attachtree_direntry').each(function(li){
                var txt = li.get('text');
                li.empty().adopt(
                    new Element('span').set('text', txt),
                    li.getNext('ul')
                );
            });
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
})(this);