from raippa.pages import Question, Task
from raippa.user import User
from raippa import page_exists

def question_list_gui(macro, questionlist, user):
    request = macro.request
    f = macro.formatter
    result = list()

    result.append(f.rawHTML('''<script type="text/javascript">
if(MooTools){
    window.addEvent('domready', function(){
        var pendings = $$('span.pending, span.picked');
        if (pendings){
            pendings.each(function(el){
                el.grab(new Element('span', { 
                    'class' : 'ajax_loading',
                    'html' : '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
                    }));
                var check = new Request.JSON({
                    url : '?action=searchMetasJSON&args=has_done&s=' + el.get('ref'),
                    onSuccess : function(result){
                        if(result.checked == true){
                            window.location.reload(true);
                            }
                        if(el.hasClass('pending') && result.status == "picked"){
                            window.location.reload(true);
                            }
                        }

                    });
                (function(){check.get();}).periodical(5000);
            });
        }
    });
}
    </script>'''))
    result.append(f.div(True,id="questionList"))
    result.append(f.bullet_list(True))

    for questionpage in questionlist:
        question = Question(request, questionpage)

        result.append(f.listitem(True))

        if user.is_teacher():
            result.append(f.pagelink(True, questionpage))
            result.append(f.text(question.title()))
            result.append(f.pagelink(False, questionpage))
        else:
            may, reason = user.can_do(question) 
            if may:
                result.append(f.pagelink(True, questionpage))
                result.append(f.text(question.title()))
                result.append(f.pagelink(False, questionpage))
                if reason == "redo":
                    result.append(f.icon('(./)'))
                elif reason == "pending":
                    result.append(f.rawHTML(''' <span ref="%s" class="pending">pending</span>''' % questionpage))
            else:
                result.append(f.text(question.title()))
                if reason == "done":
                    result.append(f.icon('(./)'))
                elif reason == "pending":
                    result.append(f.rawHTML(''' <span ref="%s" class="pending">pending</span>''' % questionpage))
                elif reason == "picked":
                    result.append(f.rawHTML(''' <span ref="%s" class="picked">picked</span>''' % questionpage))

        result.append(f.listitem(False))

    result.append(f.bullet_list(False))
    result.append(f.div(False))

    return result

def question_list_teacher_gui(macro, task, user):
    request = macro.request
    f = macro.formatter
    questionlist = task.questionlist()
    res = list()

    res.append(f.div(1,id="teacherUiBox"))


    res.extend(question_list_gui(macro, questionlist, user))

    res.extend(question_list_editor(macro, task))

    res.extend(question_list_stats(macro, task))

    res.append(f.div(0))
    return res

def question_list_editor(macro, task):
    request = macro.request
    f = macro.formatter
    res = list()

    questionlist = task.questionlist()
    jsQlist = list()
    for qpage in questionlist:
        question = Question(request, qpage)
        qname = question.title().replace("'", "\'")
        incomplete = "false"
        if not page_exists(request, qpage + '/options'):
            incomplete = "true"
        jsQlist.append("{'page' : '%s','title' : '%s', 'incomplete' : %s}" % (qpage, qname, incomplete))

    res.append(f.div(True, id="editList"))
    prefix =request.cfg.url_prefix_static 
    old_type = task.options().get('type', u'')
    deadline = task.options().get('deadline', u'')
    res.append(f.rawHTML('''
<script type="text/javascript" src="%s/raippajs/mootools-1.2-more.js"></script>
<script type="text/javascript" src="%s/raippajs/calendar.js"></script>
<script type="text/javascript">

var questionListData;

window.addEvent('domready', function(){
    questionListData = new Hash();
    questionListData.set("editList", new Object());
    questionListData.set("selected", [%s]);
    questionQuery();
});

function questionQuery(){
     var questionQuery = new Request.JSON({
        onSuccess : function(questions){
            questions.each(function(q){
                if (questionListData.get("selected").some(function(selected){
                        return selected["page"] == q.page;
                    })){
                    q.task = false;
                    }
                });
            questionListData.set("questionData", questions);
            var field = $('filterField');
            if(field){
                field.fireEvent('keyup');
            }
        }
        }).get({'action': 'searchMetasJSON' , 'args' : 'questions'});
    }

var qSortList = new Class({
    Extends: Sortables,
   
    initialize: function(lists, options){
        this.parent(lists, options);
        this.addEvents({
        'sort' : function(el){
            el.addClass('sorting');
        },
        'complete' : function(el){
            el.removeClass('sorting');
        }
    });
 
    },
    addQuestion: function(page, name, hilight, pool, incomplete){
      var default_opacity = 1;
       var li = new Element('li',{
           events: {
            'mouseenter' : function(){
                if($$('li.sorting').length == 0){
                    var a = this.getElement('a');
                    this.addClass('hovered');
                    if(default_opacity != 1){
                        a.fade('show');
                    }
                    }
                },
            'mouseleave' : function(){
                var a = this.getElement('a');
                this.removeClass('hovered');
                if(default_opacity != 1){
                    a.fade('hide');
                }
                }
               }
        });
        var namespan = new Element('span', {
                'text' : name,
                'styles': {
                    'float' : 'left',
                    'width' : '95%%'
                }
            });
        li.grab(namespan);
        if (pool){
            var sign = "+";
            var color = "green";
        }else{
            var sign = "&minus;";
            var color = "red";
        }

        var thislist = this;
        li.store("page", page);
        if(incomplete){
            namespan.grab(new Element('span',{
                'text' : ' (incomplete)',
                'styles' :{
                    'color' : 'red',
                    'font-style' : 'italic'

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
                'width' : '5%%',
                'text-align' : 'center'
                },
            events: {
                'click': function(){
                    thislist.removeItems(li).destroy();
                    if (thislist.lists.length > 1){
                        thislist.addQuestion(page, name, true, Math.abs(pool - 1), incomplete);
                        }
                    }
                }
        }));
        if(this.lists.length > 1){
            li.inject(this.lists[pool]);
        }else{
            li.inject(this.lists[0]);
        }

        if(hilight){
            li.highlight();
        }
        this.addItems(li);

    },

    rmQpool : function(){
        if (this.lists.length >1){
            this.removeLists(this.lists.slice(1)).destroy();
        }
    },
    serializeQ : function(){
        return this.serialize(0, function(el){
            return el.retrieve("page");
            });
        }
});

function modalize(div){
     var overlay = new Element('div', {
            id : 'overlay',
            'tween' :{
                'duration' : 'short'
                },
            styles : {
                'width' : '100%%',
                'height' : '100%%',
                'opacity' : 0.8,
                'z-index' : 990,
                'background' : '#333333',
                'position' : 'fixed',
                'top' : 0,
                'left' : 0
                },
            events : {
                'click' : function(){
                    this.tween('opacity', 0.2);
                    (function(){
                        this.destroy();
                        var l = $('lightContainer');
                        if(l) l.destroy();
                    }).delay(150, this);
                    }
                }
        
        });
       var container = new Element('div',{
            id : 'lightContainer',
            styles : {
                'left' : '50%%',
                'position' : 'absolute',
                'top' : 0,
                'z-index' : 1000
                }
        }).grab(div);
    
    if (!Browser.Engine.trident){
        overlay.setStyle('opacity', 0.2);
        overlay.tween('opacity', 0.8);
    }
 
    $(document.body).adopt(overlay, container);
    div.setStyle('margin-left', -0.5 * div.getCoordinates().width);
   }

function editQuestionList(){
    var searchCont = new Element('div',{
            styles : {
                'width' : '450px',
                'background' : 'white',
                'border' : '1px solid black',
                'margin-top' : '100px',
                'padding' : '5px 10px 5px 10px'
            }
        });
    var newQuestionCont = new Element('div',{
            'styles': {
                'float': 'right'
                }
        }).grab(
        new Element('form', {
            'method' : 'get',
            'action' : window.location.href,
            'events': {
                'submit' : function(e){
                    var e = new Event(e).stop();
                            var field = this.getElement('input[name=pagename]');
                            this.set('action', field.get('value'));
                            this.set('send',{
                                url : window.location.href,
                                async : false
                                });
                            this.send();
                            questionQuery();
                            field.set('value','');
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
                new Element('input',{
                    'name' : 'pagename',
                    'maxlength' : '255' 
                    }),
                new Element('input',{
                    'type' : 'submit',
                    'value' : 'New Question'
                    })
            )
    );
    var search_hint = "Filter...";
    var field = new Element('input',{
            'value' : search_hint,
            'id' : 'filterField',
            events : {
                'focus': function(){
                    if(this.get('value') == search_hint) this.set('value', '');
                    },
                'blur' : function(){
                    if (this.get('value') == '') this.set('value', search_hint);
                    },
                'keyup' : function(){
                    var search = this.get('value');
                    if (search == search_hint) search = '';
                    var cont = $('qSearchResults');

                    if(questionListData.get("questionData")){
                        var qPool = new Element('ul',{
                            id: 'qPool' ,
                            'class' : 'sortable'
                            });
                        var eList = questionListData.get('editList');
                        eList.rmQpool();
                        eList.addLists(qPool);
                        var selected = eList.serializeQ();
                        questionListData.get("questionData").each(function(q){
                            var title = q.title;
                            var page = q.page;
                            var incomp = q.incomplete;
                            var task = q.task;
                            if (title.test(search, "i") && !selected.contains(page) && !task){
                                eList.addQuestion(page, title, 0, 1, incomp);
                                }
                            });
                        cont.getElements('ul').destroy();
                        cont.removeClass('ajax_loading');
                        qPool.inject(cont);
                        //qPool.inject(newQuestionCont, "before");
                    }else{
                        cont.addClass('ajax_loading');
                        var refresh = function(){ this.fireEvent('keyup') };
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

    var typesel = new Element('select',{
        'id' : 'typesel',
        'name' : 'type'
        })
    var oldtype = "%s";
    ["basic", "exam", "questionary"].each(function(type){
        var selected = oldtype == type ? "selected" :"";
        typesel.grab(new Element('option',{
            'value' : type,
            'selected' : selected,
            'text' : type
            }));
        });
    var typeCont = new Element('div').adopt(new Element('label', {
            'for' : 'typesel',
            'text' : 'Task type: '
            }),typesel);
    var deadlineCont = new Element('div').adopt(new Element('label',{
            'for' : 'deadline',
            'text' : 'Deadline: '
        }), new Element('input',{
            'id' : 'deadline',
            'name' : 'deadline',
            'value' : '%s'
            }));
    var qSelectedList = new Element('ul', {
            id : 'qSelectedList',
            'class' : 'sortable'
            });
 
    var selected = new Element('div', {
            id : 'qSelected',
            styles : {
                'width' : '100%%',
                'min-height' : '20px',
                'border' : '1px solid green',
                'margin' : '5px auto  5px auto'
                }
        }).grab(qSelectedList);
   var results = new Element('div', {
            id : 'qSearchResults',
            styles : {
                'width' : '100%%',
                'min-height' : '20px',
                'margin' : '5px auto 5px auto',
                'border' : '1px solid red'
                }
        });
   var formCont = new Element('div', {
       'styles' : {
           'width' : '100%%',
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
            'click' : function(){
                submitCheck();
                }
            }
        });

    var cancel = new Element('input', {
        'type' : 'button',
        'value' : 'Cancel',
        events :{
            'click' : function(){
                $('overlay').fireEvent('click');
                }
            }
        });
 
    form.adopt(new Element('input',{
        'type' : 'hidden',
        'name' : 'action',
        'value' : 'editQuestionList'
        }), submit, cancel);
    formCont.adopt(form, newQuestionCont);
    searchCont.adopt(typeCont, deadlineCont, selected, results, formCont);
    //results.adopt( newQuestionCont);

    new Element('label',{text : 'Selected questions: '}).inject(selected, "before");
    new Element('label',{text : 'Available questions: '}).inject(results, "before");
    field.inject(results,"before"); 

    questionListData.set('editList', new qSortList(qSelectedList, {revert : true, constrain : true}));
   questionListData.get('selected').each(function(el){
        questionListData.get('editList').addQuestion(el["page"], el["title"], false, 0, el["incomplete"]);
        });

    modalize(searchCont);
    
    var calendar = new Calendar({
            'deadline' : 'Y-m-d'
        },{
            draggable : false,
            fixed: true
        });
    var calCSS = new Asset.css('%s/raippa/css/calendar.css');


    field.fireEvent('keyup');
}

function submitCheck(ajax){
    var form = $("taskEditForm");
    var qList = questionListData.get("editList").serializeQ();
    
    qList.unshift("first");
    
    for(var i=0; i < (qList.length -1 ); i++){
        form.grab(new Element('input', {
            'type' : 'hidden',
            'name' : 'flow_'+ qList[i],
            'value' : qList[i+1]
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
    if (!ajax){
        form.submit();
    }else{
        form.set('send', {
            method: 'post',
            async : false,
            url : window.location.href
            });
        form.send();
        }
    }

</script>
<a class="jslink" onclick="editQuestionList();">edit</a>
&nbsp;
<a class="jslink" onclick="">stats</a>
    ''' % (prefix, prefix, ",".join(jsQlist), old_type, deadline, prefix)))

    res.append(f.div(False))
    return res

def question_list_stats(macro, task):
    request = macro.request
    f = macro.formatter
    res = list()
    
    res.append(f.div(True, id="statBox"))
    res.append(f.div(False))

    return res

def macro_QuestionList(macro):
    request = macro.request
    formatter = macro.formatter
    pagename = macro.request.page.page_name
    result = list()

    task = Task(request, pagename)
    user = User(request, request.user.name)

    if user.is_teacher():
        result.extend(question_list_teacher_gui(macro, task, user))
    else:
        result.extend(question_list_gui(macro, task.questionlist(), user))

    return "".join(result)
