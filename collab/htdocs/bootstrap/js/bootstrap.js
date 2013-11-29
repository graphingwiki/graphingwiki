/*
 bootstrap.js
 A drop in replacement for bootstrap Dropdown
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2013 by Lauri Pokka
 */
document.id(window).addEvent('domready', function() {
    "use strict";

    var body = document.id(document.body);
    body.addEvent('click:relay([data-toggle=dropdown])', function(e) {
        e.preventDefault();
        var parent = this.getParent();

        if (!parent.hasClass('open')) {
            parent.addClass('open');
            body.addEvent('click:once', function() {
                parent.removeClass('open');
            })
        }
    });

    body.addEvent('click:relay([data-toggle=collapse])', function(e) {
        $$(this.get('data-target')).forEach(function(parent) {
            var show = !parent.retrieve('show');

            if (!parent.retrieve('height')) {
                parent.store('height', parent.getDimensions()['height']);
            }

            parent.store('show', show)
                .removeClass('collapse')
                .addClass('collapsing')
                .addClass('in');

            if (show) {
                parent.setStyle.delay(0, parent, ['height', parent.retrieve('height')]);
            } else {
                parent.setStyle('height', 'auto');
            }

            var done = function() {
                parent.removeClass('collapsing');
                if (!parent.retrieve('show')) {
                    parent.removeClass('in');
                    parent.addClass('collapse');
                }
            };

            if ("ontransitionend" in window) {
                parent.addEventListener('transitionend', done);
            } else {
                done();
            }
        });
    });
});