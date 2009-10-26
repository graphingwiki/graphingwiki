#-*- coding: iso-8859-1 -*-
import re, random, time

from MoinMoin.Page import Page
from MoinMoin.support import difflib
from graphingwiki.editing import get_metas
from raippa import removelink, attachment_list, attachment_content
from raippa import raippacategories as rc
from raippa.pages import Question, Course,  Answer, MissingMetaException, TooManyValuesException
from raippa.user import User

def sanitize(input):
    if input == None:
        input = u""
    input = unicode(input)
    input = input.replace("\\", "\\\\")
    input = input.replace("'", "\\'")
    input = input.replace("\n", " ")
    return input.strip()

def paint_diff(diff, previous=""):
    colored = str()

    if previous == "\n":
        for char in diff:
            if char == "\n":
                colored += "&nbsp;\n"
            else:
                colored += char
    else:
        for char in diff:
            if char == "\n":
                colored += "\n&nbsp;"
            else:
                colored += char

    return colored

def diff_html(expected, users_output):
    charobj = difflib.SequenceMatcher(None, expected, users_output)
    charmatch = charobj.get_matching_blocks()
    left = str()
    right = str()
    lastleft = 0
    lastright = 0

    for leftindex, rightindex, length in charmatch:
        if leftindex > lastleft:
            if lastleft > 0:
                previous = expected[lastleft-1]
            else:
                previous = ""
            colored = paint_diff(expected[lastleft:leftindex], previous)
            left += '<span>%s</span>' % colored.replace(" ", "&nbsp;")

        left += expected[leftindex:leftindex+length].replace(" ", "&nbsp;")
        lastleft = leftindex+length

        if rightindex > lastright:
            if lastright > 0:
                previous = users_output[lastright-1]
            else:
                previous = ""
            colored = paint_diff(users_output[lastright:rightindex], previous)
            right += '<span>%s</span>' % colored.replace(" ", "&nbsp;")

        right += users_output[rightindex:rightindex+length].replace(" ", "&nbsp;")
        lastright = rightindex+length

    return """
<table class="answer-diff">
<tr>
<td class="answer-diff-expected">
<b>Expected output</b>&nbsp;&nbsp;(<span>missing</span>)
</td>
<td class="answer-diff-users">
<b>Your program outputs</b>&nbsp;&nbsp;(<span>not wanted</span>)
</td>
</tr>
<tr>
<td class="answer-diff-expected">
%s
</td>
<td class="answer-diff-users">
%s
</td>
</tr>
</table>
""" % ("<br>\n".join(left.split("\n")), "<br>\n".join(right.split("\n")))


def draw_teacherui(macro, user, question):
    
    request = macro.request
    f = macro.formatter
    res = list()

    res.append(f.div(1,id="teacherUiBox"))

    res.append(f.rawHTML('''
 <script type="text/javascript" src="%s/raippajs/stats.js"></script>
 <script type="text/javascript" src="%s/raippajs/raphael.js"></script>
    <script type="text/javascript">

function editor(view){ 
    var edit = $('answerEditBox');
    var statsdiv = new Element('div'); 
    var modal = new modalizer([edit, statsdiv], { 
        tabLabels : ["edit", "stats"],
        defTab : view,
        destroyOnExit : false
        });     
    
    var stats = new QuestionStats(statsdiv);
    }

</script>
<br>
<a class="jslink" onClick="editor(0);">edit</a>
<a class="jslink" onClick="editor(1);">stats</a>
''' % (request.cfg.url_prefix_static,request.cfg.url_prefix_static)))
    #edit ui
    res.extend(draw_answer_edit_ui(macro, question))

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
    showTip($$('tr.tiprow').length -1);
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
/* Shows tip and comment fields of <num>th answer*/
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
  //trying to prevent double saves
  if($(button).retrieve('saved') == 'true'){
    return false;  
    }

  $(button).store('saved', 'true');
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
    res.append(f.rawHTML('<input type="button" onclick="window.location.reload();" value="Cancel">'))
    res.append(f.rawHTML('</form>'))
    res.append(f.div(0))

    return res

def draw_answers(macro, user, question):
    f = macro.formatter
    request = macro.request

    res = list()
    qtype = question.options().get('answertype', '')
    
    res.append(f.div(1, id="answerBox"))
    res.append(f.rawHTML('''<script type="text/javascript">
    var cansubmit = true;
    function disableform(el){
        if(cansubmit){
            cansubmit = false;
            $(el).getElement('input[type=submit]').set('disabled', 'true');
            return true;
        }else{
            return false;
        }
    }
    </script>'''))

    res.append(f.rawHTML('<form id="ansForm" enctype="multipart/form-data" method="post" onsubmit="disableform(this);"action="">'))
    res.append(f.rawHTML('<input type="hidden" name="action" value="checkAnswers">'))
    res.append(f.rawHTML('<input type="hidden" name="time" value="%s">' % str(time.time())))

    answers = question.answers()
    #possible types: radio,checkbox, text (+file?)
    
    if qtype in ["checkbox", "radio"]:
        random.shuffle(answers)
        for i, anspage in enumerate(answers):
            answer = Answer(request, anspage)

            page = anspage.split("/")[-1]
            
            value = answer.answer()
            res.append(f.rawHTML(
    '''<input type="%s" id="ans%s" name="answer" value="%s">''' % (qtype, i, page)))
            res.append(f.rawHTML('''<label for="ans%s">%s</label>''' %(i, value)))
            res.append(f.linebreak(0))

    elif qtype == "text":
        res.append(f.rawHTML('<input name="answer">'))
        res.append(f.linebreak(0))

    elif qtype == "file":
        done, value = user.has_done(question)
        if value == "pending":
            course = Course(request, request.cfg.raippa_config)
            coursepage = course.graphpage
            res.append(f.rawHTML('''
<script type="text/javascript">
    if (MooTools){
        window.addEvent('domready', function(){
            var check = new Request.JSON({
                url: '?action=searchMetasJSON&args=has_done',
                onSuccess: function(result){
                    if(result.checked == true || result.status == "picked"){
                        window.location = "%s";
                    }
                }
            });
        (function(){check.get();}).periodical(5000);
        });
    }
</script>
            '''  % coursepage)) 
            res.append(f.rawHTML('Your answer is not yet processed. Wait or submit new answer. '))
            res.append(f.rawHTML('<span class="ajax_loading">&nbsp;&nbsp;&nbsp;&nbsp;</span>'))
            res.append(f.linebreak(0))
        elif value not in ['picked', 'pending', None] and Page(request, value).exists():
            task = question.task()
            if task and task.options().get('type', 'basic') not in ['exam', 'questionary']:
                keys = ['output', 'right', 'wrong']
                metas = get_metas(request, value, keys, checkAccess=False)

                right = int()
                wrong = int()

                wrongs = metas.get('wrong', list())
                wrong = len(wrongs)

                rights = metas.get('right', list())
                right = len(rights)

                if right > 0 or wrong > 0:
                    res.append(f.text('Your last answer passed %s test(s) out of %i.' % (right, right+wrong)))
                    res.append(f.linebreak(0))
             
                outputs = metas.get('output', list())
                if outputs and wrong > 0:
                    answer_testnames = dict()
                    for answerpage in answers:
                        ameta = get_metas(request, answerpage, ['testname'], checkAccess=False)
                        if ameta.get('testname', list()):
                            answer_testnames[ameta['testname'][0]] = answerpage

                    for output in outputs:
                        output = removelink(output)
                        outputpage = Page(request, output)
                        if not outputpage.exists():
                            continue

                        hmeta = get_metas(request, output, ['testname'], checkAccess=False)

                        testnames = hmeta.get('testname', list())
                        if not testnames:
                            continue

                        testname = testnames[0]
                        if testname not in answer_testnames:
                            continue

                        answerpagename = answer_testnames[testname]

                        answerpage = Page(request, answerpagename)
                        if not answerpage.exists():
                            continue

                        keys = ['gwikicategory', 'parameters', 'input', 'output']
                        ameta = get_metas(request, answerpagename, keys, checkAccess=False)

                        if rc['answer'] not in ameta.get('gwikicategory', list()):
                            continue

                        res.append(f.rawHTML("<b>Test: %s</b>" % testname))
                        res.append(f.linebreak(0))

                        regexp = re.compile('{{{\s*(.*)\s*}}}', re.DOTALL)

                        #answer parameters
                        if ameta.get('parameters', list()):
                            res.append(f.text('Used commandline parameters:'))
                            res.append(f.preformatted(1))
                            res.append(f.rawHTML(ameta['parameters'][0]))
                            res.append(f.preformatted(0))
                            res.append(f.linebreak(0))

                        #answer input
                        if ameta.get('input', list()):
                            input_page = Page(request, removelink(ameta['input'][0]))

                            if input_page.exists():
                                answer_input = regexp.search(input_page.get_raw_body())

                                if answer_input:
                                    answer_input = answer_input.groups()[0]
                                    res.append(f.text('Used input:'))
                                    res.append(f.preformatted(1))
                                    res.append(f.rawHTML(answer_input))
                                    res.append(f.preformatted(0))
                                    res.append(f.linebreak(0))

                                attachments = attachment_list(request, input_page.page_name)
                                for ifile in attachments:
                                    res.append(f.text('Used input file: %s' % ifile))
                                    res.append(f.preformatted(1))
                                    fc = attachment_content(request, input_page.page_name, ifile)
                                    res.append(f.text(fc))
                                    res.append(f.preformatted(0))
                                    res.append(f.linebreak(0))

                        #answer output
                        if ameta.get('output', list()):
                            output_page = Page(request, removelink(ameta['output'][0]))

                        if not output_page.exists():
                            continue

                        answer_output = regexp.search(output_page.get_raw_body())
                        if answer_output:
                            answer_output = answer_output.groups()[0]

                            output_text = outputpage.get_raw_body()
                            raw_output = regexp.search(output_text)
                            
                            if raw_output:
                                output_text = raw_output.groups()[0]
                                res.append(f.text('Output: '))
                                if answer_output == output_text:
                                    res.append(f.icon('B)'))
                                else:
                                    res.append(f.icon('X-('))
                                res.append(f.rawHTML(diff_html(answer_output, output_text)))
                                res.append(f.linebreak(0))
                            else:
                                res.append(f.text('Missing output.'))
                                res.append(f.linebreak(0))

                            #file diff
                            user_attachments = attachment_list(request, output)

                            attachments = attachment_list(request, output_page.page_name)
                            for ofile in attachments:
                                if ofile not in user_attachments:
                                    res.append(f.text('Missing output file: %s' % ofile))
                                    res.append(f.linebreak(0))
                                    continue

                                ufile_output = attachment_content(request, output, ofile)
                                afile_output = attachment_content(request, output_page.page_name, ofile)
                                res.append(f.text('File output: %s ' % ofile))
                                if afile_output == ufile_output:
                                    res.append(f.icon('B)'))
                                else:
                                    res.append(f.icon('X-('))
                                res.append(f.rawHTML(diff_html(afile_output, ufile_output)))
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

    result.extend(draw_answers(macro, user, question))
    
    if user.is_teacher():
        result.extend(draw_teacherui(macro, user, question))

    return "".join(result)
