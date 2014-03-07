/*
 bootstrap.js
 A drop in replacement for bootstrap Dropdown
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2013 by Lauri Pokka
 */
require(['mootools'], function() {
    "use strict";

    var body = document.id(document.body);

    body.addEvent('click:relay(.searchmenu a)', function(e){
        e.preventDefault();
        var value = this.get('data-value');
        var parent = this.getParent('form');
        parent.getElements('.active').removeClass('active');
        this.getParent('li').addClass('active');

        var btn = parent.getElement('[type=submit]');
        btn.set('name', value + 'search');
        return false;
    });

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
                .addClass('collapsing');

            if (show) {
                parent.setStyle.delay(0, parent, ['height', parent.retrieve('height')]);
            } else {
                parent.setStyle('height', '0');
                parent.removeClass('in');
            }

            var done = function() {
                parent.removeClass('collapsing');
                if (!parent.retrieve('show')) {
                    parent.addClass('collapse');
                    parent.setStyle('height', '');
                }else{
                    parent.addClass('in');
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