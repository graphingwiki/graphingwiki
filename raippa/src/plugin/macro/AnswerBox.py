#-*- coding: iso-8859-1 -*-
import re, random, time

from MoinMoin.Page import Page
from MoinMoin.support import difflib
from MoinMoin import wikiutil
from graphingwiki.editing import get_metas
from raippa import removelink, attachment_list, attachment_content, to_json
from raippa import raippacategories as rc
from raippa.pages import Question, Answer, MissingMetaException, TooManyValuesException
from raippa.pages import Course
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
    prefix = request.cfg.url_prefix_static
    res.append(f.rawHTML('''
 <script type="text/javascript" src="%s/raippajs/question_edit.js"></script>
 <script type="text/javascript" src="%s/raippajs/stats.js"></script>
 <script type="text/javascript" src="%s/raippajs/raphael.js"></script>
    <script type="text/javascript">

function editor(view){ 
    var editdiv = new Element('div');
    var statsdiv = new Element('div'); 
    var modal = new modalizer([editdiv, statsdiv], { 
        tabLabels : ["edit", "stats"],
        defTab : view,
        destroyOnExit : false
        });     
    
    var edit = new QuestionEditor(editdiv, editoptions);
    var stats = new QuestionStats(statsdiv);
    }

</script>
<br>
<a class="jslink" onClick="editor(0);">edit</a>
<a class="jslink" onClick="editor(1);">stats</a>
''' % (prefix, prefix, prefix)))
    #edit ui
    res.extend(draw_answer_edit_ui(macro, question))

    res.append(f.div(0))

    return res

def draw_answer_edit_ui(macro, question):
    answers = question.answers()
    qtype = question.options().get('answertype', '')
    if question.options().get('redo', False):
        redo = "true"
    else:
        redo = "false"

    if question.options().get('shuffle', False):
        shuffle = "true"
    else:
        shuffle = "false"

    request = macro.request
    f = macro.formatter
    res = list()

    ans_js = []
    if qtype in ["checkbox", "radio", "text"]:
    #generating old answers using javascript
        for i, anspage in enumerate(answers):
            answer = Answer(request, anspage)
            ans = answer.answer()
            tips = answer.tips()
            com = answer.comment()
            options = answer.options()

            if com == None:
                com =""

            if len(tips)<1:
                tips =[""]

            val = answer.value()
            tip = tips[0]

            ans_js.append(to_json({
                "name" : ans,
                "value": val,
                "tip": tip,
                "comment": com,
                "page": anspage,
                "options": options
                }))

    elif qtype == "file":
        for i, anspage in enumerate(answers):
            answer = Answer(request, anspage).answer()

            ans_js.append(to_json({
                    "name":  answer[0],
                    "cmd" : answer[1],
                    "input" : answer[2],
                    "output" : answer[3],
                    "infiles" : answer[4],
                    "outfiles" : answer[5]
                    }))

   #options for editor
    res.append(f.rawHTML('''
    <script type="text/javascript">
    var editoptions = {
            types :  ["checkbox", "radio", "text", "file"],
            redo : %s,
            type: '%s',
            shuffle: %s,
            answers : [%s]
        };
    </script>''' % (redo, qtype, shuffle, ",".join(ans_js))))
    

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
        if question.options().get("shuffle", False):
            random.shuffle(answers)

        for i, anspage in enumerate(answers):
            answer = Answer(request, anspage)

            page = anspage.split("/")[-1]
            
            res.append(f.rawHTML(
    '''<input type="%s" id="ans%s" name="answer" value="%s">''' % (qtype, i, page)))

            if 'latex' in answer.options():
                execute = wikiutil.importPlugin(request.cfg, "macro", 'latex', 'execute')
                value = execute(macro, answer.answer())
            else:
                value = answer.answer()

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
