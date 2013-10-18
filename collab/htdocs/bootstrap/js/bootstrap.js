/*
     bootstrap.js
     A drop in replacement for bootstrap Dropdown
     License: MIT <http://www.opensource.org/licenses/mit-license.php>
     Copyright: 2013 by Lauri Pokka
 */
document.id(window).addEvent('domready', function() {
    var toggle = "[data-toggle=dropdown]";
    var body = document.id(document.body);
    body.addEvent('click:relay(' + toggle + ')', function(e) {
        e.preventDefault();
        var parent = this.getParent();

        if (!parent.hasClass('open')) {
            parent.addClass('open');
            body.addEvent('click:once', function(){
                parent.removeClass('open');
            })
        }
    });
});