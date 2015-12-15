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
                li.getElement('input').focus();
            });

            this.element.addEvent('click:relay(a.inv)', function(e) {
                e.target.getParent('li, h4').hasClass('reinvite');

                var parent = e.target.getSiblings('.name')[0].parentElement;

                parent.toggleClass('reinvite');

                if (parent.get('tag') !== "li") {
                    parent.getParent('ul').getElements('li[data-value]').each(function(li) {
                        if (li.hasClass('group') || li.hasClass('recursive')) {
                            return
                        }

                        if (parent.hasClass('reinvite')) {
                            li.addClass('reinvite');
                        } else {
                            li.removeClass('reinvite');
                        }
                    })
                }
            });

            this.element.addEvent('click:relay(a.rm)', function(e) {
                e.target.getParent('li, ul').toggleClass('delete');
            });

            this.element.addEvent('click:relay(.save)', this.save.bind(this));

            this.element.addEvent('click:relay(.jslink)', function() {
                if (this.element.getElements('input, .delete, .reinvite').length) {
                    this.element.addClass('edited');
                } else {
                    this.element.removeClass('edited');
                }
            }.bind(this));
        },

        save: function() {
            var ops = [];

            var alreadyInvited = function(user) {
                return ops.filter(function(op) {
                    return user == op.name;
                }).length > 0;
            };

            var traverseGroup = function(name) {
                var group = this.groups[name];
                var members = group.members.slice();
                group.groups.map(traverseGroup).forEach(function(mems) {
                    mems.forEach(function(member) {
                        if (members.indexOf(member) === -1) {
                            members.push(member);
                        }
                    })
                });
                return members;
            }.bind(this);

            var accessibleUsers = traverseGroup("AccessGroup");

            this.element.getElements('.delete').each(function(el) {
                var group = el.getParent('ul').getElement('h4').get('data-value');
                var name = el.get('data-value');
                ops.push({op: 'del', group: group, name: name});
            });

            this.element.getElements('li.reinvite').each(function(el) {
                if (el.hasClass('delete')) {
                    return;
                }
                var group = el.getParent('ul').getElement('h4').get('data-value');
                var name = el.get('data-value');
                if (!alreadyInvited(name)) {
                    ops.push({op: 'invite', group: group, name: name});
                }
            });

            this.element.getElements('input').each(function(el) {
                var group = el.getParent('ul').getElement('h4').get('data-value');
                var name = el.get('value');

                // Invite users only if they haven't previously been able to access the collab
                (name.match(/Group$/) ? traverseGroup(name) : [name]).forEach(function(n) {
                    if (accessibleUsers.indexOf(n) === -1 && !alreadyInvited(n)) {
                        ops.push({op: 'invite', group: group, name: n});
                    }
                });

                ops.push({op: 'add', group: group, name: name});
            }.bind(this));


            var inviteConfirmation = "";

            ops
                .filter(function(op) {
                    return op.op === "invite"
                })
                .forEach(function(op) {
                    if (inviteConfirmation.length == 0) {
                        inviteConfirmation += "Following users will be sent an invitation email:"
                    }

                    inviteConfirmation += "\n * " + op.name;
                });

            if (inviteConfirmation.length > 0 && !confirm(inviteConfirmation)) {
                return;
            }

            new Request({
                headers: {
                    'Content-Type': "application/json;charset=UTF-8"
                },
                url: '?action=groupsJSON',
                onSuccess: function() {
                    this.update();
                }.bind(this),
                onFailure: function(xhr) {
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
                        var cont = new Element('div.groupcontainer').inject(el);
                        var ul = new Element('ul').grab(new Element('h4').adopt(
                            new Element('a.name').set({
                                'text': name,
                                'href': baseurl + "/" + name
                            }),
                            new Element('a.glyphicon.glyphicon-envelope.jslink.inv')
                        ).set('data-value', name));
                        cont.grab(ul);
                        (group.members.concat(group.groups)).forEach(function(name) {
                            var isgroup = group.members.indexOf(name) == -1,
                                cls,
                                access = "";
                            if (isgroup) {
                                ul.grab(new Element('li.group').adopt(
                                    new Element('span').set('class', 'glyphicon glyphicon-folder-open'),
                                    new Element('span.name').set('text', name),
                                    new Element('a.glyphicon.jslink').set('html', '&nbsp;'),
                                    new Element('a.glyphicon.glyphicon-trash.jslink.rm'),
                                    new Element('span.info.denied').set('text', results[name] ? "" : "(no access)")
                                ).set('data-value', name));
                            } else {
                                ul.grab(new Element('li').adopt(
                                    new Element('span.name').set('text', name),
                                    new Element('a.glyphicon.glyphicon-envelope.jslink.inv'),
                                    new Element('a.glyphicon.glyphicon-trash.jslink.rm')
                                ).set('data-value', name));
                            }
                        });

                        var groups = group.groups.slice();
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
                        cont.grab(new Element('br'), 'after')
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
