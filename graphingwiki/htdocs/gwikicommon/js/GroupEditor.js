/*
 GroupEditor.js
 - GUI for moinmoin group editor
 License: MIT <http://www.opensource.org/licenses/mit-license.php>
 Author: Lauri Pokka
 */
define([
    'mootools'
], function() {
    "use strict";

    return new Class({
        Implements: [Options],

        options: {},
        initialize: function(element, opts) {
            this.setOptions(opts);
            this.element = document.id(element);

            this.attach();
            this.update();
        },

        attach: function() {
            this.element.addEvent('click:relay(a.add)', function(e) {
                var li = new Element('li');
                li.adopt(
                    new Element('input'),
                    new Element('a.glyphicon.glyphicon-trash.jslink')
                        .addEvent('click', function() {
                            li.destroy()
                        })
                );
                e.target.getSiblings('ul').grab(li);
            });

            this.element.addEvent('click:relay(a.edit)', function(e) {
                var el = e.target.getSiblings('.name')[0];
                var name = el.parentElement.get('data-value');

                if (el.get('tag') == "input") {
                    new Element('span.name').set('text', name).replaces(el);
                } else {
                    new Element('input.name').set('value', name).replaces(el);
                }
            });

            this.element.addEvent('click:relay(a.rm)', function(e) {
                e.target.getParent('li, ul').toggleClass('delete');
            });

            this.element.addEvent('click:relay(.save)', this.save.bind(this));

            this.element.addEvent('click:relay(.jslink)', function() {
                if (this.element.getElements('input, .delete').length) {
                    this.element.addClass('edited');
                } else {
                    this.element.removeClass('edited');
                }
            }.bind(this));
        },

        save: function(){
            var ops = [];

            this.element.getElements('.delete').each(function(el) {
                var group = el.getParent('ul').getElement('h4').get('data-value');
                var name = el.get('data-value');
                ops.push({op: 'del', group: group, name: name});
            }).destroy();

            this.element.getElements('input').each(function(el){
                var group = el.getParent('ul').getElement('h4').get('data-value');
                var value = el.get('value');
                if (el.hasClass('name')){
                    var old = el.getParent('[data-value]').get('data-value');
                    ops.push({op: 'rename', group: group, name: old, to: value});
                }else{
                    ops.push({op: 'add', group: group, name: value});
                }
            });

            new Request({
                headers: {
                    'Content-Type': "application/json;charset=UTF-8"
                },
                url: '?action=groupsJSON',
                onSuccess: function(){
                    this.update();
                }.bind(this),
                onFailure:  function(xhr) {
                    alert(xhr.response);
                    this.update();
                }.bind(this)
            }).post(JSON.stringify(ops));
        },

        update: function() {
            var el = this.element;
            var spinner = new Element('i.glyphicon.glyphicon-refresh.icon-spin');
            el.grab(new Element('div.spinner-container').grab(spinner));
            var baseurl = this.options.baseurl;
            new Request.JSON({
                url: '?action=groupsJSON',
                onSuccess: function(results) {
                    this.groups = results;
                    el.empty();

                    Object.each(results, function(group, name) {
                        var cont  = new Element('div.groupcontainer').inject(el);
                        var ul = new Element('ul').grab(new Element('h4').adopt(
                            new Element('a.name').set({
                                'text': name,
                                'href': baseurl + "/" + name
                            })
//                            new Element('a.glyphicon.jslink').set('html', '&nbsp;'),
//                            new Element('a.glyphicon.glyphicon-pencil.jslink.edit')
                        ).set('data-value', name));
                        cont.grab(ul);
                        (group.members.concat(group.groups)).forEach(function(name) {
                            var isgroup = group.members.indexOf(name) == -1,
                                cls,
                                access = "";
                            if (isgroup) {
                                cls = 'glyphicon glyphicon-folder-open';
                                access = results[name]? "": "(no access)";
                            }

                            ul.grab(new Element('li').adopt(
                                new Element('span').set('class', cls),
                                new Element('span.name').set('text', name),
                                new Element('a.glyphicon.glyphicon-trash.jslink.rm'),
                                new Element('span.info.denied').set('text', access)
//                                new Element('a.glyphicon.glyphicon-pencil.jslink.edit')
                            ).set('data-value', name));
                        });

                        var groups = group.groups;
                        var handled = [];
                        while (groups.length) {
                            var g = groups.pop();
                            if (handled.indexOf(g) != -1 || !results[g]) continue;

                            handled.push(g);
                            Array.prototype.push.apply(groups, results[g].groups);
                            results[g].members.forEach(function(name) {
                                ul.grab(new Element('li.recursive').adopt(
                                    new Element('span.glyphicon.glyphicon-link'),
                                    new Element('span.name').set('text', name),
                                    new Element('span.info.groupname').set('text', '(' + g + ')')
                                ));
                            })
                        }

                        cont.adopt(
                            new Element('a.jslink.glyphicon.glyphicon-plus.add')
                        );
                    });

                    el.adopt(
                        new Element('br'),
                        new Element('a.btn.btn-primary.btn-sm.save[text=save]')
                    );
                }.bind(this),
                onFailure: function(xhr) {
                    alert(xhr.response);
                }
            }).get();
        }
    });
});
