#-*- coding: iso-8859-1 -*-
import random, time

from MoinMoin.Page import Page

from raippa.pages import Question, Answer
from raippa.user import User

def sanitize(input):
    if input == None:
        input = u""
    input = unicode(input)
    input = input.replace("'", "\\'")
    input = input.replace("\n", " ")
    return input.strip()

def draw_teacherui(macro, user, question):
    
    request = macro.request
    f = macro.formatter
    res = list()

    res.append(f.div(1,id="teacherUiBox"))

    res.append(f.rawHTML('''
    <ul id="answerUiMenu" class="tabMenu">
        <li id="tab1">View</li>
        <li id="tab2">Edit</li>
        <li id="tab3">Statistics</li>
    </ul>
    '''))
    res.append(f.rawHTML('''<script type="text/javascript">
if(MooTools){
window.addEvent('domready', function(){
    var lis = $('answerUiMenu').getElements('li');
     lis.addEvent('click',function(){
        changeTab(this.id);
        lis.removeClass('selected');
        this.addClass('selected');
    });

    $('tab2').fireEvent('click');
    });
}
function changeTab(box){
    var eb = $('answerEditBox');
    var vb = $('answerBox');
    var sb = $('answerStatBox');

    if(box == "view" || box == "tab1"){
       sb.addClass('hidden');
       eb.addClass('hidden');
       vb.removeClass('hidden');
    }else if(box == "edit" || box == "tab2"){
       sb.addClass('hidden');
       vb.addClass('hidden');
       eb.removeClass('hidden');
    }else if(box == "stats" || box == "tab3"){
       vb.addClass('hidden');
       eb.addClass('hidden');
       sb.removeClass('hidden');
    }
}
</script>
'''))
    #answer box
    res.extend(draw_answers(macro, user, question))
    #edit ui
    res.extend(draw_answer_edit_ui(macro, question))
    #stats window
    res.extend(draw_statistics(macro, question))

    res.append(f.div(0))

    return res

def draw_answer_edit_ui(macro, question):
    answers = question.answers()
    qtype = question.options().get('answertype', '')
    redo = question.options().get('redo', '')
    request = macro.request
    f = macro.formatter
    res = list()

    res.append(f.rawHTML('''<script type="text/javascript">
window.addEvent('domready', function(){
    $try(function(){
        initAns();
    });
    addAns();
    checkType();
    clearRms();
    showTip(0);
});
function clearRms(){ 
    $$('input.rmcheck').each(function(el){
        el.set('checked', '');
    });
    }

function rmRows(){
    $$('input.rmcheck').each(function(el){
        if(el.get('checked') == true){
            $('row'+el.get('value')).destroy();
            }
        });
}

function checkType(){
   var select = $('typeselect'); 
   var value = select.get('value');
   var file_row = $('file_row');
   var norm_rows = $$('tr[id^=row]');
   if (value == "file"){
       file_row.removeClass('hidden');
       norm_rows.addClass('hidden');
       clearRms();
    }else{
       file_row.addClass('hidden');
       norm_rows.removeClass('hidden');
    }
}

function showTip(num){
    $$('tr.tiprow').addClass('hidden');
    $$('tr.comrow').addClass('hidden');
    if ($('tiprow'+num)){
        $('tiprow' +num).removeClass('hidden');
        $('comrow' +num).removeClass('hidden');
    }
}

function addAns(ans, val, tip, comment, page){
    var table = $('ansTable');
    var tbody = table.getElement('tbody');
    var checks = table.getElements('input.rmcheck');
    var num = 0;
    if (checks.length > 0){
        num = checks.getLast().get('value').toInt() +1;
    }
    var row = new Element('tr',{
        'id' : 'row' + num,
        'class' : 'no_border'
        });

    row.grab(new Element('td')
        .grab(new Element('input',{
            'type': 'checkbox',
            'class' : 'rmcheck',
            'value' : num,
            'name' : 'rm'+num
        })));
    var tab = new Element('table',{
            'class' : 'no_border'
        });
    var tabTbody = new Element('tbody');
    tab.grab(tabTbody);

    var ansRow = new Element('tr');
    var valRow = new Element('tr');
    var tipRow = new Element('tr',{ 'id': 'tiprow' + num, 'class' : 'tiprow hidden'});
    var comRow = new Element('tr',{ 'id': 'comrow' + num, 'class' : 'comrow hidden'});

    var ansTd = new Element('td',{
            'rowspan' : '2'
            }).grab(new Element('textarea',{
                    'cols' : 60,
                    'text' : ans,
                    'name' : 'answer' + num,
                    'rows' : 2,
                    'events' :{
                        'focus' : function(){
                            showTip(num);
                            }
                        }
        }));
    var rightChk = !val || val == "right" ? true : false;
    var wrongChk = rightChk ?  false : true;
    var valTd1 = new Element('td')
            .adopt(new Element('input',{
                'type' : 'radio',
                'name' : 'value' +num,
                'value' : 'right',
                'id' : 'right' + num,
                'checked': rightChk
                }),new Element('label',{
                    'for': 'right' + num,
                    'text' : 'right'
                    }));
    var valTd2 =  new Element('td')
            .adopt(new Element('input',{
                'type' : 'radio',
                'name' : 'value' +num,
                'value' : 'wrong',
                'id' : 'wrong' + num,
                'checked' : wrongChk
                }),new Element('label',{
                    'for': 'wrong' + num,
                    'text' : 'wrong'
                    }));

    ansRow.adopt(new Element('th',{
            'rowspan' : '2',
            'text' : 'Answer:'
        }), ansTd, valTd1);

    valRow.grab(valTd2);

    tipRow.adopt(new Element('th',{
            'text' : 'Tip:'
        }),new Element('td')
            .grab(new Element('textarea', {
                'name' : 'tip' + num,
                'text' : tip,
                'cols' : 60,
                'rows' : 2
        })));

    comRow.adopt(new Element('th',{
            'text' : 'Comment:'
        }),new Element('td')
            .grab(new Element('textarea', {
                'name' : 'comment' + num,
                'text': comment,
                'cols' : 60,
                'rows' : 2
        })));
 
    tabTbody.adopt(ansRow, valRow, tipRow, comRow);

    row.grab(new Element('td',{
        'colspan': 3
        })
        .grab(new Element('div')
            .grab(tab)
        ));

    if (page){
        row.grab(new Element('input', {
            'type' : 'hidden',
            'name' : 'page' + num,
            'value' : page
        }));
        }
    tbody.grab(row);
}

function hideTips(field){
    var field = $(field);
    

}

function submitCheck(button){
  if(button.value == "Cancel"){
    return true;
  }
  var form = $('editform');
  var type = $('typeselect').get('value');
  if(type != 'file'){
    var ans = $('ansTable').getElements('textarea[name^=answer]');
    hasAnswer = ans.some(function(a){
      if(!a.get('name') || a.getParent('tr').hasClass('hidden')){
        return false;
      }
      var name = a.get('name');
      var value = $(name.replace(/answer/,'right')).checked;
      var pass = a.value.length > 0  && value;
      return pass == true;
    });
    if(!hasAnswer){
      var msg = "There is no right answer! Do you still want to save the question?";
      return confirm(msg);
    }
  }else{
    $('tr[id^=row]').destroy();
  }
  return true;
}

</script>
        '''))

    #edit ui
    res.append(f.div(1,id="answerEditBox", css_class="hidden"))

    res.append(f.rawHTML('<form id="editform" method="post" action="">'))
    res.append(f.rawHTML('<input type="hidden" name="action" value="editQuestion">'))

    res.append(f.table(1, id="ansTable"))
    res.append(f.table_row(1))
    res.append(f.table_cell(1))
    res.append(f.rawHTML('<a class="jslink" style="color:red;" onclick="rmRows();" title="Remove selected answers">X</a>'))
    res.append(f.table_cell(0))

    res.append(f.table_cell(1))
    res.append(f.text("Answer type: "))
    res.append(f.rawHTML('<select id="typeselect" name="answertype" onchange="checkType();">'))
    for type in ["checkbox", "radio", "text", "file"]:
        selected = ""
        if type == qtype:
            selected = "selected"

        res.append(f.rawHTML('<option value="%s" %s>%s</option>' %(type,selected, type)))

    res.append(f.rawHTML('</select>'))
    res.append(f.table_cell(0))
    res.append(f.table_cell(1))
    if redo == "True":
        redo = "checked"

    res.append(f.rawHTML('<input type="checkbox" id="redobox" name="redo" value="True" %s>') % redo)
    res.append(f.rawHTML('<label for="redobox">Allow redoing question.</label>'))
    res.append(f.table_cell(0))
    res.append(f.table_cell(1))
    res.append(f.rawHTML('<input type="button" value="new answer" onclick="addAns();">'))
    res.append(f.table_cell(0))
    res.append(f.table_row(0))
    
    file_ans = ""

    if qtype in ["checkbox", "radio", "text"]:
    #generating old answers using javascript
        res.append(f.rawHTML('<script type="text/javascript">function initAns(){'))
        for i, anspage in enumerate(answers):
            answer = Answer(request, anspage)
            ans = sanitize(answer.answer())
            tips = answer.tips()
            com = sanitize(answer.comment())
            if com == None:
                com =""

            if len(tips)<1:
                tips =[""]

            val = answer.value()
            tip = sanitize(tips[0])

            res.append(f.linebreak(1))
            res.append(f.rawHTML('''addAns('%s', '%s', '%s', '%s', '%s');''' % (ans, val, tip, com, anspage)))

        res.append(f.rawHTML('}</script>'))

    elif qtype == "file":
        if len(answers) > 0:
            answer = Answer(request,answers[0])
            file_ans = answer.answer()
        else: 
            file_ans = u''

    res.append(f.table_row(1, id="file_row", css_class="no_border"))
    res.append(f.table_cell(1, colspan="4"))
    res.append(f.rawHTML('<textarea name="answer" cols="80" rows="30">%s</textarea>' % file_ans))
    res.append(f.table_cell(0))
    res.append(f.table_row(0))

    res.append(f.table(0))
    res.append(f.rawHTML('<input type="submit" onclick="return submitCheck(this);" value="Save">'))
    res.append(f.rawHTML('</form>'))
    res.append(f.div(0))

    return res

def draw_statistics(macro, question):
    res = list()
    f = macro.formatter

    res.append(f.div(1,id="answerStatBox"))
    res.append(f.div(0))
    return res

def draw_answers(macro, user, question):
    f = macro.formatter
    request = macro.request

    res = list()
    qtype = question.options().get('answertype', '')
    
    res.append(f.div(1, id="answerBox"))
    res.append(f.rawHTML('<form id="ansForm" enctype="multipart/form-data" method="post" action="">'))
    res.append(f.rawHTML('<input type="hidden" name="action" value="checkAnswers">'))
    res.append(f.rawHTML('<input type="hidden" name="time" value="%s">' % str(time.time())))

    answers = question.answers()
    #possible types: radio,checkbox, text (+file?)
    
    if qtype in ["checkbox", "radio"]:
        random.shuffle(answers)
        for i, anspage in enumerate(answers):
            answer = Answer(request, anspage)

            value = answer.answer()
            res.append(f.rawHTML(
    '''<input type="%s" id="ans%s" name="answer" value="%s">''' % (qtype, i,value)))
            res.append(f.rawHTML('''<label for="ans%s">%s</label>''' %(i, value)))
            res.append(f.linebreak(0))

    elif qtype == "text":
        res.append(f.rawHTML('<input name="answer">'))
        res.append(f.linebreak(0))

    elif qtype == "file":
        done, value = user.has_done(question)
        if value == "pending":
            res.append(f.rawHTML('Your answer is not yet processed. Wait or submit new answer.'))
            res.append(f.linebreak(0))
        elif value not in ['picked', 'pending', None] and Page(request, value).exists():
            res.append(f.rawHTML('Your old answer is in %s.' % value))
            res.append(f.rawHTML('TODO: comment or something goes here.'))
            res.append(f.linebreak(0))

        res.append(f.rawHTML('''
<script type="text/javascript">
    window.addEvent('domready', function(){
        addFileField();
    });

    function addFileField(){
        var form = $('ansForm');
        var fields = form.getElements('input[type=file]');
        var cnt = fields.length;
        fields.removeEvents();
        var field = new Element('input' , {
            'type' :'file',
            'name' : 'answer'+cnt,
            events : {
                'change': function(){
                    addFileField();
                    }
                }
            });
        var submit = form.getElement('input[type=submit]');
        field.inject(submit, 'before');
        new Element('br').inject(submit, 'before');
    }
</script>
        '''))

    else:
        res.append(f.rawHTML('</form>'))
        if len(answers) == 0:
            res.append(f.text('Answers are not yet defined.'))

        else:
            res.append(f.text('Invalid question type!'))

        res.append(f.div(0))
        return "".join(res)

    res.append(f.rawHTML('''<input type="submit" value="Save">'''))
    res.append(f.rawHTML('</form>'))
    res.append(f.div(0))
    return res

def macro_AnswerBox(macro):
    pagename = macro.formatter.page.page_name
    request = macro.request
    result = list()

    name = request.user.name
    user = User(request, name)

    question = Question(request, pagename)

    if user.is_teacher():
        result.extend(draw_teacherui(macro, user, question))
    else:
        result.extend(draw_answers(macro, user, question))

    return "".join(result)
