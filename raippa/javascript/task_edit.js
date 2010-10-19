(function(exports) {
    var questionListData;

    function questionQuery() {
        var query = new Request.JSON({
            url: '?action=searchMetasJSON',
            onSuccess : function(questions) {
                questions.each(function(q) {
                    if (questionListData.get("selected").some(function(selected) {
                        return selected["page"] == q.page;
                    })) {
                        q.task = false;
                    }
                });
                questionListData.set("questionData", questions);
                var field = $('filterField');
                if (field) {
                    field.fireEvent('keyup');
                }
            }
        });
        query.get({'args' : 'questions'});
    }

    var qSortList = new Class({
        Extends: Sortables,

        initialize: function(lists, options) {
            this.parent(lists, options);
            this.addEvents({
                'sort' : function(el) {
                    el.addClass('sorting');
                },
                'complete' : function(el) {
                    el.removeClass('sorting');
                    questionListData.set('edited', true);
                }
            });

        },
        addQuestion: function(page, name, hilight, pool, incomplete) {
            var default_opacity = 1;
            var li = new Element('li', {
                events: {
                    'mouseenter' : function() {
                        if ($$('li.sorting').length == 0) {
                            var a = this.getElement('a');
                            this.addClass('hovered');
                            if (default_opacity != 1) {
                                a.fade('show');
                            }
                        }
                    },
                    'mouseleave' : function() {
                        var a = this.getElement('a');
                        this.removeClass('hovered');
                        if (default_opacity != 1) {
                            a.fade('hide');
                        }
                    }
                }
            });
            var namespan = new Element('span', {
                'text' : name,
                'styles': {
                    'float' : 'left',
                    'width' : '95%'
                }
            });
            li.grab(namespan);
            if (pool) {
                var sign = "+";
                var color = "green";
            } else {
                var sign = "&minus;";
                var color = "red";
            }

            var thislist = this;
            li.store("page", page);
            if (incomplete) {
                namespan.grab(new Element('a', {
                    'text' : ' (incomplete)',
                    'href' : page,
                    'styles' :{
                        'color' : 'red',
                        'font-style' : 'italic'

                    },
                    'events' : {
                        'click' : function() {
                            return confirm("Disgard changes and go to edit question '" + page + "'?");
                        }
                    }
                }));
            }
            li.grab(new Element('a', {
                'html': sign,
                styles: {
                    'color' : color,
                    'opacity' : default_opacity,
                    'float' : 'right',
                    'clear' : 'right',
                    'font-size' : '15px',
                    'font-weight' : 'bold',
                    'cursor' : 'pointer',
                    'width' : '5%',
                    'text-align' : 'center'
                },
                events: {
                    'click': function() {
                        questionListData.set('edited', true);
                        thislist.removeItems(li).destroy();
                        if (thislist.lists.length > 1) {
                            thislist.addQuestion(page, name, true, Math.abs(pool - 1), incomplete);
                        }
                    }
                }
            }));
            if (this.lists.length > 1) {
                li.inject(this.lists[pool]);
            } else {
                li.inject(this.lists[0]);
            }

            if (hilight) {
                li.highlight();
            }
            this.addItems(li);

        },

        rmQpool : function() {
            if (this.lists.length > 1) {
                this.removeLists(this.lists.slice(1)).destroy();
            }
        },
        serializeQ : function() {
            return this.serialize(0, function(el) {
                return el.retrieve("page");
            });
        }
    });


    var questionListModal = new Class({
        Extends: modalizer,
        click : function() {
            var edited = questionListData.get('edited');
            if (!edited || confirm('Discard changes and close editor?')) {
                this.close();
            }
        }
    });

    function editQuestionList() {
        questionListData.set('edited', false);
        var searchCont = new Element('div', {
            styles : {
                'width' : '450px',
                'background' : 'white',
                'border' : '1px solid black',
                'margin-top' : '100px',
                'padding' : '5px 10px 5px 10px'
            }
        });
        var newQuestionCont = new Element('div', {
            'styles': {
                'float': 'right'
            }
        }).grab(
            new Element('form', {
                'method' : 'get',
                'action' : window.location.href,
                'events': {
                    'submit' : function(e) {
                        var e = new Event(e).stop();
                        var field = this.getElement('input[name=pagename]');
                        this.set('action', field.get('value'));
                        this.set('send', {
                            url : window.location.href,
                            async : false
                        });
                        this.send();
                        questionQuery();
                        field.set('value', '');
                    }
                }
            }).adopt(
                new Element('input', {
                    'type' : 'hidden',
                    'name' : 'action',
                    'value': 'editQuestion'
                }),
                new Element('input', {
                    'type' : 'hidden',
                    'name' : 'newQuestion',
                    'value' : 'true'
                }),
                new Element('input', {
                    'name' : 'pagename',
                    'maxlength' : '240'
                }),
                new Element('input', {
                    'type' : 'submit',
                    'value' : 'New Question'
                })
                )
            );
        var search_hint = "Filter...";
        var field = new Element('input', {
            'value' : search_hint,
            'id' : 'filterField',
            events : {
                'focus': function() {
                    if (this.get('value') == search_hint) this.set('value', '');
                },
                'blur' : function() {
                    if (this.get('value') == '') this.set('value', search_hint);
                },
                'keyup' : function() {
                    var search = this.get('value');
                    if (search == search_hint) search = '';
                    var cont = $('qSearchResults');

                    if (questionListData.get("questionData") && cont) {
                        var qPool = new Element('ul', {
                            id: 'qPool' ,
                            'class' : 'sortable'
                        });
                        var eList = questionListData.get('editList');
                        eList.rmQpool();
                        eList.addLists(qPool);
                        var selected = eList.serializeQ();
                        questionListData.get("questionData").each(function(q) {
                            var title = q.title;
                            var page = q.page;
                            var incomp = q.incomplete;
                            var task = q.task;
                            if (title.test(search, "i") && !selected.contains(page) && !task) {
                                eList.addQuestion(page, title, 0, 1, incomp);
                            }
                        });
                        cont.getElements('ul').destroy();
                        cont.removeClass('ajax_loading');
                        qPool.inject(cont);
                        //qPool.inject(newQuestionCont, "before");
                    } else {
                        if (cont) cont.addClass('ajax_loading');
                        var refresh = function() {
                            this.fireEvent('keyup')
                        };
                        refresh.delay(500, this);
                    }
                }
            }
        });

        var fieldCont = new Element('div', {
            styles : {
                'margin': '5px auto 5px auto',
                'width' : '350px'
            }
        }).grab(field);

        var typesel = new Element('select', {
            'id' : 'typesel',
            'name' : 'type',
            'events' : {
                'change' : function() {
                    if (['exam'].contains(this.get('value'))) {
                        $('consecutiveCont').addClass('hidden');
                    } else {
                        $('consecutiveCont').removeClass('hidden');
                    }
                }
            }
        })
        var oldtype = questionListData.get("old_type");
        ["basic", "exam", "questionary"].each(function(type) {
            var selected = oldtype == type ? "selected" : "";
            typesel.grab(new Element('option', {
                'value' : type,
                'selected' : selected,
                'text' : type
            }));
        });
        var consecutive = questionListData.get("consecutive") == "True";
        var typeCont = new Element('div').adopt(new Element('label', {
            'for' : 'typesel',
            'text' : 'Task type: '
        }),
            typesel);
        var consecutiveCont = new Element('div', {'id': 'consecutiveCont'}).adopt(
            new Element('label', {
                'for' : 'consecutiveCheck',
                'text' : 'Is consecutive: '
            }),
            new Element('input', {
                'type' : 'checkbox',
                'name' : 'consecutive',
                'checked' : consecutive,
                'id' : 'consecutiveCheck'
            }));
        typeCont.grab(consecutiveCont);
        var deadlineCont = new Element('div').adopt(new Element('label', {
            'for' : 'deadline',
            'text' : 'Deadline: '
        }), new Element('input', {
            'id' : 'deadline',
            'name' : 'deadline',
            'value' : questionListData.get("deadline")
        }),
            new Element('a', {
                'class' : 'jslink',
                'text' : 'clear',
                'events' : {
                    'click' : function() {
                        $('deadline').set('value', '');
                    }
                }
            }));
        var qSelectedList = new Element('ul', {
            id : 'qSelectedList',
            'class' : 'sortable'
        });

        var selected = new Element('div', {
            id : 'qSelected',
            styles : {
                'width' : '100%',
                'min-height' : '20px',
                'border' : '1px solid green',
                'margin' : '5px auto  5px auto'
            }
        }).grab(qSelectedList);
        var results = new Element('div', {
            id : 'qSearchResults',
            styles : {
                'width' : '100%',
                'min-height' : '20px',
                'margin' : '5px auto 5px auto',
                'border' : '1px solid red'
            }
        });
        var formCont = new Element('div', {
            'styles' : {
                'width' : '100%',
                'overflow' : 'hidden'
            }});
        var form = new Element('form', {
            'method' : 'post',
            'id' : 'taskEditForm',
            'action' : window.location.href
        });

        form.setStyle('float', 'left');

        var submit = new Element('input', {
            'type' : 'button',
            'value' : 'Save',
            events: {
                'click' : function() {
                    submitCheck();
                }
            }
        });

        var cancel = new Element('input', {
            'type' : 'button',
            'value' : 'Cancel',
            events :{
                'click' : function() {
                    $('overlay').fireEvent('click');
                }
            }
        });

        form.adopt(new Element('input', {
            'type' : 'hidden',
            'name' : 'action',
            'value' : 'editQuestionList'
        }), submit, cancel);
        formCont.adopt(form, newQuestionCont);
        searchCont.adopt(typeCont, deadlineCont, selected, results, formCont);
        //results.adopt( newQuestionCont);

        new Element('label', {text : 'Selected questions: '}).inject(selected, "before");
        new Element('label', {text : 'Available questions: '}).inject(results, "before");
        field.inject(results, "before");

        questionListData.set('editList', new qSortList(qSelectedList, {revert : true, constrain : true}));
        questionListData.get('selected').each(function(el) {
            questionListData.get('editList').addQuestion(el["page"], el["title"], false, 0, el["incomplete"]);
        });
        $(document.body).grab(searchCont);
        var calendar = new Calendar({
            'deadline' : 'Y-m-d'
        }, {
            draggable : false,
            fixed: true
        });
        var calCSS = new Asset.css(questionListData.get("prefix") +'/raippa/css/calendar.css');

        typesel.fireEvent('change');
        field.fireEvent('keyup');
        return searchCont;
    }

    var editor = function(view) {
        var edit = editQuestionList();
        var statsdiv = new Element('div');
        var modal = new questionListModal([edit, statsdiv], {
            defTab : view,
            tabLabels : ["edit", "stats"],
            containerStyles :{
                'margin-top' : '100px',
                'background' : 'white'
            }
        });
        var stats = new TaskStats(statsdiv);
    };

    exports.TaskEditor = function(options) {
        questionListData = new Hash(options);
        questionListData.set("editList", new Object());
        questionListData.set("selected", options.selected);
        questionQuery();
        return editor;
    };
    
    function submitCheck(ajax) {
        var form = $("taskEditForm");
        var qList = questionListData.get("editList").serializeQ();

        qList.unshift("first");

        for (var i = 0; i < (qList.length - 1 ); i++) {
            form.grab(new Element('input', {
                'type' : 'hidden',
                'name' : 'flow_' + qList[i],
                'value' : qList[i + 1]
            }));
        }
        form.grab(new Element('input', {
            'type' : 'hidden',
            'name' : 'type',
            'value' : $('typesel').get('value')
        }));
        form.grab(new Element('input', {
            'type' : 'hidden',
            'name' : 'deadline',
            'value' : $('deadline').get('value')
        }));
        if ($('consecutiveCheck').get('checked')) {
            form.grab(new Element('input', {
                'type' : 'hidden',
                'name' : 'consecutive',
                'value' : 'consecutive'
            }));
        }
        if (!ajax) {
            form.submit();
        } else {
            form.set('send', {
                method: 'post',
                async : false,
                url : window.location.href
            });
            form.send();
        }
    }
})(this);