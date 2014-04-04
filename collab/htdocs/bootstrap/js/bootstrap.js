/*
 bootstrap.js
 A drop in replacement for bootstrap Dropdown
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Copyright: 2013 by Lauri Pokka
 */
require([
    'collabcommon/common/dom',
    'mootools'
], function(dom) {
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
            });
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

    $$('.collab-list').addEvent('click', function(e) {
        if ($$('div.collab-list-container').length) {
            return;
        }

        e.preventDefault();

        var cont = new Element('div.collab-list-container.list-group.loading').inject(document.body);
        var spinner = new Element('i.glyphicon.glyphicon-refresh.icon-spin');
        cont.grab(new Element('div.spinner-container').grab(spinner));
        dom.listen(cont, "mousewheel", dom.preventWheelGestures);
        dom.listen(cont, "wheel", dom.preventWheelGestures);

        new Request.JSON({
            url: '?action=collabListJSON',
            onSuccess: function(collabs) {
                cont.empty();
                var filter = new Element('input[placeholder=Filter]');
                cont.grab(new Element('span.list-group-item').grab(filter));
                filter.focus();

                filter.addEventListener('keyup', function(e){
                    var val = this.value;
                    var filtered = collabs.filter(function(collab){
                        return (collab.title + collab.motd + collab.shortName).indexOf(val) != -1;
                    });

                    list(filtered);
                });

                var list = function(items) {
                    cont.getElements('a').destroy();
                    items.forEach(function(collab) {
                        var active = collab.active ? " active" : "";
                        cont.grab(new Element('a', {
                            'class': 'list-group-item' + active,
                            'href': collab.url
                        }).adopt(
                                new Element('h4.list-group-item-heading', {text: collab.title}),
                                new Element('p.list-group-item-text', {
                                        text: collab.motd}
                                )
                            ));
                    });
                };

                list(collabs);

            }
        }).get();

        var close = function(e) {
            if (!e.target.getParent('.collab-list-container')) {
                $$('div.collab-list-container').destroy();
                body.removeEvent('click', close);
            }
        };
        body.addEventListener('click', close);

        return false;
    });

});