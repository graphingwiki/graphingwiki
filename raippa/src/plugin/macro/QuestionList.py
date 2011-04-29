from MoinMoin.Page import Page
from graphingwiki.editing import get_metas
from raippa.pages import Question, Task, MissingMetaException, TooManyValuesException
from raippa.user import User
from raippa import page_exists

def question_list_gui(macro, task, user):
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
                (function(){check.get();}).periodical(45000);
            });
        }
    });
}
    </script>'''))

    questionlist = task.questionlist()
 
    if len(questionlist) > 1:
        tasktype = task.options().get('type', None)
    else:
        tasktype = None

    deadline, deadlines = task.deadline()
                  
    user_deadline = deadlines.get(user.name, None)
    if user_deadline:
        result.append("Your deadline: %s" % user_deadline)
    elif deadline:
        result.append("Deadline: %s" % deadline)

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
                result.append(f.text(question.title() + u' '))
                result.append(f.pagelink(False, questionpage))

                if tasktype in ['exam', 'questionary']:
                    done, info = user.has_done(question)

                    if done:
                        result.append(f.icon('(./)'))
                    elif info not in ['pending', 'picked', None]:
                        result.append(f.icon('(./)'))
                    elif info == 'pending':
                        result.append(f.rawHTML(''' <span ref="%s" class="pending"></span>''' % questionpage))
                    elif info == 'picked':
                        result.append(f.rawHTML(''' <span ref="%s" class="picked"></span>''' % questionpage))
                else:
                    if reason == "pending":
                        result.append(f.rawHTML(''' <span ref="%s" class="pending"></span>''' % questionpage))
                    else:
                        done, info = user.has_done(question)
                        answertype = question.options().get('answertype', 'text')
                        partly = False

                        if info and Page(request, info).exists() and answertype == 'file':
                            keys = ['right', 'wrong']
                            metas = get_metas(request, info, keys, checkAccess=False)

                            right = int()
                            wrong = int()
        
                            wrongs = metas.get('wrong', list())
                            wrong = len(wrongs)

                            if wrong > 0:
                                partly = True

                            rights = metas.get('right', list())
                            right = len(rights)
                
                            if right > 0 or wrong > 0:
                                result.append(f.text('%i/%i ' % (right, right+wrong)))

                        if done:
                            if partly:
                                result.append(f.icon(':\\'))
                            else:
                                result.append(f.icon('B)'))
                        elif info not in ['pending', 'picked', None]:
                            result.append(f.icon('X-('))
            else:
                result.append(f.text(question.title() + u' '))
                if reason == "done":
                    if tasktype in ['exam', 'questionary']:
                        result.append(f.icon('(./)'))
                    else:
                        result.append(f.icon('B)'))
                elif reason == "pending":
                    result.append(f.rawHTML(''' <span ref="%s" class="pending"></span>''' % questionpage))
                elif reason == "picked":
                    result.append(f.rawHTML(''' <span ref="%s" class="picked"></span>''' % questionpage))

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


    res.extend(question_list_gui(macro, task, user))

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
        qname = question.title().replace("'", "\\'")
        page = qpage.replace("'", "\\'")
        incomplete = "false"
        if not page_exists(request, qpage + '/options'):
            incomplete = "true"
        jsQlist.append("{'page' : '%s','title' : '%s', 'incomplete' : %s}" % (page, qname, incomplete))

    res.append(f.div(True, id="editList"))
    prefix =request.cfg.url_prefix_static 
    old_type = task.options().get('type', u'')
    consecutive = task.options().get("consecutive", False)
    deadline, alldeadlines = task.deadline()
    if deadline == None:
        deadline = ""
    res.append(f.rawHTML('''
<script type="text/javascript" src="%s/raippajs/raippa-common.js"></script>
<script type="text/javascript" src="%s/raippajs/calendar.js"></script>
<script type="text/javascript" src="%s/raippajs/stats.js"></script>
<script type="text/javascript" src="%s/raippajs/task_edit.js"></script>
<script type="text/javascript">

var options = {
    selected: [%s],
    old_type: "%s",
    consecutive: "%s",
    deadline: "%s",
    prefix: "%s"
};
var editor;

window.addEvent('domready', function(){
    editor = TaskEditor(options);
});


</script>
<a class="jslink" onclick="editor(0);">edit</a>
&nbsp;
<a class="jslink" onclick="editor(1);">stats</a>
    ''' % (prefix, prefix, prefix,  prefix, ",".join(jsQlist), old_type, consecutive, deadline, prefix)))

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
        result.extend(question_list_gui(macro, task, user))

    return "".join(result)
