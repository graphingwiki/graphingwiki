# -*- coding: utf-8 -*-"
action_name = 'editQuestion'
import os

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.action.AttachFile import getAttachDir

from graphingwiki.editing import getmetas
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import encode
from graphingwiki.patterns import getgraphdata
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input

from raippa import addlink, randompage
from raippa import Question

usercategory = u'CategoryUser'
questioncategory = u'CategoryQuestion'
answercategory = u'CategoryAnswer'
tipcategory = u'CategoryTip'
taskpointcategory = u'CategoryTaskpoint'


def getattachments(request, pagename):
    attach_dir = getAttachDir(request, pagename)
    if os.path.isdir(attach_dir):
        files = map(lambda a: a.decode(config.charset), os.listdir(attach_dir))
        files.sort()
        return files
    return []

def do_upload(request, pagename):
    filename = None
    if request.form.has_key('file__filename__'):
        filename = request.form['file__filename__']
        target = filename

    filecontent = request.form['file'][0]
    if len(target) > 1 and (target[1] == ':' or target[0] == '\\'):    
        bsindex = target.rfind('\\')
        if bsindex >= 0:
            target = target[bsindex+1:]        

    target = wikiutil.taintfilename(target)
    attach_dir = getAttachDir(request, pagename, create=1)
    fpath = os.path.join(attach_dir, target).encode(config.charset)
    exists = os.path.exists(fpath)
    if exists:
        try:
            os.remove(fpath)
        except:
            pass
    stream = open(fpath, 'wb')
    try:
        stream.write(filecontent)
    finally:
        stream.close()

def show_basicform(request, questionpage=None):
    html = unicode()
    if questionpage:
        question = Question(request, questionpage)
    html += u'''
 <script type="text/javascript">
/*	Using mootools javascript framework */
window.addEvent('domready', function(){
  /* Hide tip-fields, regexp and casesensitive checkboxes on pageload */
  typeCheck();
  $('ansRow').getElements('span').set('style', 'visibility:hidden');

  /* Making tip-fields visible for loaded wrong answers*/
 $('ansRow').getElements('input[type=radio]').each(function(el){
   if(el.value == 'false' && el.checked){
     show(el);
     }
   });
});

/* Set object given in parameters visible */
function show(obj){
    var tr = $(obj).getParent('tr');
	tr.getElement('span').style.visibility = "";
 }
 /* Hide given object */
function hide(obj){
    var tr = $(obj).getParent('tr');
	tr.getElement('span').style.visibility = "hidden";
}
var deleted = 0;

/* Generates answerfield dynamically and sets right visibility values  */
function addField(){

var sel = document.getElementById('typeSelect').value;
var lkm = deleted;
var to = document.getElementById('ansRow').tBodies[0];
    for(var i = 0; i< to.childNodes.length; i++){
       if(to.childNodes[i].tagName){
	      if(to.childNodes[i].tagName == "TR"){
		     lkm++;
		  }
		}
	}

var newRow = new Element('tr',{'id': 'ansTr'+lkm});
var td1 = new Element('td');
var td2 = new Element('td');
var td3 = new Element('td', { 'class' : 'rexp' });
var td4 = new Element('td', { 'class' : 'rexp' });
var td5 = new Element('td');
var td6 = new Element('td');
var td7 = new Element('td');

td1.grab(new Element('input', {
	'type' : 'checkbox',
	'name' : 'rmcheck'+lkm,
	'value' : 'rm',
	'title' : 'Select this answer to be deleted'
  })
);

td2.grab(new Element('input', {
	'type' : 'text',
	'name' : 'answer'+lkm
  })
);

td3.grab(new Element('input' , {
	'type' : 'checkbox',
	'name' : 'cSens'+lkm,
	'value' : 'true',
	'title' : 'Answer is case sensitive'
  })
);


td4.grab(new Element('input' , {
	'type' : 'checkbox',
	'name' : 'rexp'+lkm,
	'value' : 'true',
	'title' : 'Answer is a regular expression'
  })
);
var radioTrue = new Element('input', {
	'type' : 'radio',
	'id' : 'value'+lkm,
	'name' : 'value'+lkm,
	'value' : 'true',
	'checked': 'true'
});
td5.grab(radioTrue);
var radioFalse = new Element('input', {
	'type' : 'radio',
	'name' : 'value'+lkm,
	'value' : 'false'
});

td6.grab(radioFalse);
var span = new Element('span', {
	'class' : 'tip',
	'style' : 'visibility: hidden;'
  });

span.set('text', 'Tip: ');

span.grab(new Element('input', {
	'type' : 'text',
	'name' : 'tip' + lkm
  })
);

td7.grab(span);

newRow.adopt(td1, td2);
//newRow.adopt(td3, td4);
newRow.adopt(td5, td6, td7);

/* Add tip-field visibility controlling */
td5.getFirst('input').addEvent('click', function(){
	var tr = this.getParent('tr');
	tr.getElement('span').style.visibility = "hidden";
  });

td6.getFirst('input').addEvent('click', function(){
	var tr = this.getParent('tr');
	tr.getElement('span').style.visibility = "";
  });

$('ansRow').getFirst('tbody').grab(newRow);

//make rexp classes visible if needed
typeCheck();
}


/* Removes selected answer fields */
function rmField(){
var input, name, value, type, checked;
var tab = document.getElementById('ansRow').tBodies[0];
var regExp = /rmcheck\d+/;
var done = 0;

while(done != 1){
done = 1;
var checks = document.getElementsByTagName('INPUT');
for(var i in checks){
    try{
		input = checks[i];
        name = input.getAttribute('name');
        value = input.getAttribute('value');
        type = input.getAttribute('type');
        if(type == "checkbox"){
		  checked = input.checked;
		  }

	  if(regExp.test(name) == true && checked == true){
	  tab.removeChild(input.parentNode.parentNode);
      done = 0;
      deleted++;
	  break;
        }
    }catch(err){
	  }
  }
}
}

/* Change visibility of answer data fields depending on which answertype has
been selected */
function typeCheck(){
var sel = $('typeSelect').value;
var tds = $$('td.rexp');
var td = null;
  if(sel === "file"){
	document.getElementById('ansRow').style.display = "none";
	document.getElementById('fieldCreator').style.display = "none";
 }else{
	document.getElementById('ansRow').style.display = "";
  	document.getElementById('fieldCreator').style.display = "";
  }

for(var i in tds){
  if(tds[i]){
	td = tds[i];
    if(td.className === "rexp" && sel !== "text"){
	  td.style.display = "none";
    }else if(td.className === "rexp" && sel === "text"){
	  td.style.display = "";
    }
  }
}
}

function submitCheck(button){
  /* Checking if cancel button was pressed*/
  if(button.value == "Cancel"){
    return true;
    }
  var form = $('dataform');
  if($('questionfield').value == ''){
	alert('Please insert question before saving!');
	return false;
	}
var type = $('typeSelect').value;
  if(type != 'file'){
	var ans = $$('input[name^=answer]');
	hasAnswer = ans.some(function(a){
	  var value = $(a.name.replace(/answer/,'value')).checked;
	  var pass = a.value.length > 0  && value;
	  return pass == true;
	  });
	if(!hasAnswer){
	  var msg = "There is no right answer! Do you still want to save the question?";
	  return confirm(msg);
	  }
	}
return true;
  }
</script>'''
    if questionpage:
        html += u'Pagename: %s\n' % questionpage

    html += u'''
<form id="dataform" method="POST" enctype="multipart/form-data">
<input type="hidden" name="action" value="%s">
<table style="border-style:hidden">
<tr style="border-style:hidden">
<td style="border-style:hidden">question:</td>
<td style="border-style:hidden"colspan="2">''' % action_name
    if questionpage:
        html += u'<input type="hidden" name="questionpage" value="%s">' % questionpage
        html += u'<textarea id="questionfield" name="question" rows="3" cols="70">%s</textarea>' % question.question
    else:
        html += u'<textarea id="questionfield" name="question" rows="3" cols="70"></textarea>'
    html += u'''
</td>
<tr>
<tr style="border-style:hidden">
<td  style="border-style:hidden">note:</td>
<td colspan="2"style="border-style:hidden">'''
    if questionpage:
        html += u'<textarea name="note" rows="7" cols="70">%s</textarea>' % question.note
    else:
        html += u'<textarea name="note" rows="7" cols="70"></textarea>'
    html += u'''
</td>
<tr>
<tr style="border-style:hidden">
<td style="border-style:hidden">type:</td>
<td colspan="2"style="border-style:hidden">
<select name="type">
<option value=""> </option>\n'''
    globaldata, questions, metakeys, styles = metatable_parseargs(request, questioncategory)
    questiontypes = list()
    for question_in_list in questions:
        metas = getmetas(request, request.graphdata, question_in_list, ["type"])
        for type, metatype in metas["type"]:
            questiontypes.append(type)
    for type in list(set(questiontypes)):
        if questionpage:
            if type in question.types:
                html += u'<option value="%s" selected="selected">%s</option>\n' % (type, type)
            else:
                html += u'<option value="%s">%s</option>\n' % (type, type)
        else:
            html += u'<option value="%s">%s</option>\n' % (type, type)
    html += u'''
</select> &nbsp; 
<input size="30" type="text" name="type">
</td>
<tr>
<tr style="border-style:hidden">
<td style="border-style:hidden">image:</td>
<td colspan="2"style="border-style:hidden">\n'''
    if questionpage:
        files = getattachments(request, questionpage)
        if files:
            for file in files:
                html += u'%s\n' % file
        html += u'<input type="file" name="file" value="Select...">'
    else:
        html += u'<input type="file" name="file" value="Select...">'
    html += u'''
</td>
<tr>
</table>
    <hr>
    answer type: &nbsp; <select id="typeSelect" name="answertype" onChange="typeCheck();">\n'''
    answertypes = ["radio", "checkbox", "text", "file"]
    for type in answertypes:
        if questionpage:
            if type == question.answertype:
                html += u'<option value="%s" selected="selected">%s</option>\n' % (type, type)
            else:
                html += u'<option value="%s">%s</option>\n' % (type, type)
        else:
            html += u'<option value="%s">%s</option>\n' % (type, type)
    html += u'''
    </select> &nbsp; 
    <input id="fieldCreator" type="button" name="addButton" title="Add more answer fields"
    value="Add new field" onClick="addField();">
<br>
 <table id="ansRow">
<tr>
    <td style="text-align:center"><a title="Remove selected answers"
	style="color:red"  href="javascript: rmField();">X</a></td>
    <td style="width:150px">Answer:</td>'''
    #html += u'''
    #<td title="Case sensitive" class="rexp" style="width:110px; text-align: center">Case sensitive</td>
    #<td title="Regular Expression" class="rexp" style="width:75px; text-align: center">Regexp</td>
    #'''
    html += u'''
    <td style="width:50px">Right</td>
    <td style="width:50px">Wrong</td>
    <td></td>
</tr>'''

    if questionpage:
        if question.answertype != "file":
            answerdict = question.getanswers()
            number = 0
            for answer, answeroptions in answerdict.iteritems():
                number += 1
                html += u'''
<tr id="ansTr%s">
<td><input type="checkbox" name="rmcheck%s" value="rm" title="Select this answer to be deleted"></td>
<td><input type="text" name="answer%s" value="%s"></td>''' % (number, number, number, answer)
                #regexp and CaseSens goes here
                value = answeroptions[0]
                if value == "true":
                    html += u'''
<td><input type="radio" id="value%s" name="value%s" value="true" onClick="hide(this);" checked></td>
<td><input type="radio" name="value%s" value="false" onClick="show(this);"></td>''' % (number, number, number)
                else:
                    html += u'''
<td><input type="radio" id="value%s" name="value%s" value="true" onClick=""></td>
<td><input type="radio" name="value%s" value="false" onClick="show(this);" checked></td>''' % (number, number, number)
                tip = answeroptions[1]
                if tip:
                    tippage = "Tip/%s" % tip
                    meta = getmetas(request, request.graphdata, tippage, ["tip"])
                    for tipnote, type in meta["tip"]:
                        break
                    html += u'''
<td><span class="tip">Tip: <input type="text" name="tip%s" value="%s"></span></td>
</tr>''' % (number, tipnote)
                else:
                    html += u'''
<td><span class="tip">Tip: <input type="text" name="tip%s"></span></td>
</tr>''' % number
    else:
        for answernumber in range(1,5):
            html += '''
<tr id="ansTr%s">
<td><input type="checkbox" name="rmcheck%s" value="rm" title="Select this answer to be deleted"></td>
<td><input type="text" name="answer%s"></td>''' % (answernumber, answernumber, answernumber)
    #<td class="rexp"><input type="checkbox" name="cSens%s" value="true" title="Answer is case sensitive"></td>
    #<td class="rexp"><input type="checkbox" name="rexp%s"value="true" title="Answer is regular expression" ></td>
            html += '''
<td><input type="radio" id="value%s" name="value%s" value="true" onClick="hide(this);" checked ></td>
<td><input type="radio" name="value%s" value="false" onClick="show(this);"></td>
<td><span class="tip">Tip: <input type="text" name="tip%s"></span></td>
</tr>''' % (answernumber, answernumber, answernumber, answernumber)

    html += u'''
  </table>
    <hr>
     <input type="submit" name="save" value="Save" onclick="return submitCheck(this);">
     <input type="submit" name="cancel" value="Cancel" onclick="return submitCheck(this);">
    </form>
'''

    request.write(html)

def show_socialform(request):
    globaldata, userlist, metakeys, styles = metatable_parseargs(request, usercategory)
    users = dict()
    for user in userlist:
        metas = getmetas(request, request.graphdata, encode(user), ["name"], checkAccess=False)
        if metas["name"]:
            users[user] = metas["name"][0][0]

    html = str()
    html += u'''
<form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="action" value="%s">
    select user: <select name="question">''' % action_name
    for userpage in users:
        html += u'<option value="%s">%s\n' % (userpage, users[userpage])
    html += u'''
    </select><br>
    note: <input type="text" name="note"><br>
    <input type="hidden" name="answertype" value="radio">
    answer: <input type="text" name="answer1"><br>
    <input type="hidden" name="value1" value="true">

    answer: <input type="text" name="answer2"<br>
    <input type="hidden" name="value2" value="true">

    answer: <input type="text" name="answer3"><br>
    <input type="hidden" name="value3" value="true">
'''
    html += u'''
    <input type="submit" name="save" value="Save" >
    <input type="submit" name="cancel" value="Cancel" >
</form>'''

    request.write(html)

def show_typeselector(request):
    html = str()
    html += u'''
<form method="POST">
    <input type="hidden" name="action" value="%s">
    select question type: <select name="type">
        <option value="basic">basic text/image
        <option value="social">social questinary
    </select>
''' % action_name
    html += u'''
    <input type="submit" name="select" value="Select">
</form>'''

    request.write(html)

def savequestion(request,  oldquestion=None):
    #edit questionpage
    questiondata = {"question": [request.form["question"][0]],
                    "note": [request.form["note"][0]],
                    "answertype": [request.form["answertype"][0]],
                    "type": request.form["type"]}

    if oldquestion:
        questionpage = oldquestion
        input = order_meta_input(request, questionpage, questiondata, "repl")
        process_edit(request, input)
        question = Question(request, questionpage)
        oldanswers = question.getanswers()
    else:
        questionpage = randompage(request, "Question")
        input = order_meta_input(request, questionpage, questiondata, "add")
        process_edit(request, input, True, {questionpage:[questioncategory]})

    #find all the answers
    answerdict = dict()
    for key in request.form:
        if key != "answertype" and key.startswith("answer"):
            answer = request.form[key][0]
            if not answer:
                continue
            answernumber = key[6:]
            value = request.form["value"+answernumber][0]
            tip = request.form.get("tip"+answernumber, [u''])[0]
            
            #edit answerpage
            answerdata = {u'question': [addlink(questionpage)]} 
            if value == u'true': 
                answerdata[u'true'] = [answer]
                answerdata[u'false'] = [u' ']
            else:
                answerdata[u'false'] = [answer]
                answerdata[u'true'] = [u' ']

            if oldquestion and oldanswers.has_key(answer):
                answerpage = oldanswers[answer][3] 
                input = order_meta_input(request, answerpage, answerdata, "repl")
                process_edit(request, input)

                #edit tippage
                tipid = oldanswers[answer][1]
                if value != u'true' and tip != u'':
                    tipdata = {u'answer': [addlink(answerpage)],
                               u'tip': [tip]}
                    if tipid:
                        tippage = "Tip/"+tipid 
                    else:
                        tippage = randompage(request, "Tip")
                    input = order_meta_input(request, tippage, tipdata, "repl")
                    process_edit(request, input, True, {tippage:[tipcategory]})
                elif tipid:
                    tippage = "Tip/"+tipid
                    tippage = PageEditor(request, tippage, do_editor_backup=0)
                    if tippage.exists():
                        tippage.deletePage()
                del oldanswers[answer]
            else:
                answerpage = randompage(request, "Answer")
                input = order_meta_input(request, answerpage, answerdata, "add")
                process_edit(request, input, True, {answerpage:[answercategory]})

                #edit tippage
                if value != u'true' and tip != u'':
                    tipdata = {u'answer': [addlink(answerpage)],
                               u'tip': [tip]}
                    tippage = randompage(request, "Tip")
                    input = order_meta_input(request, tippage, tipdata, "add")
                    process_edit(request, input, True, {tippage:[tipcategory]})

    if oldquestion:
        for answer, answerdata in oldanswers.iteritems():
            deletepage = PageEditor(request, answerdata[3], do_editor_backup=0)
            if deletepage.exists():
                deletepage.deletePage()

    try:
        file = request.form.get('file', [u''])[0]
        do_upload(request, questionpage)
    except:
        pass

def delete(request, pagename):
    pagename = encode(pagename)
    page = PageEditor(request, pagename, do_editor_backup=0)
    if page.exists():
        categories = list()
        metas = getmetas(request, request.graphdata, pagename, ["WikiCategory"])
        for category, type in metas["WikiCategory"]:
            if category == questioncategory:
                linkedpage = request.graphdata.getpage(pagename)
                linking_in = linkedpage.get('in', {})
                linkinglist = linking_in.get("question", [])
                for linkingpage in linkinglist:
                    meta = getmetas(request, request.graphdata, linkingpage, ["WikiCategory"])
                    for category, type in meta["WikiCategory"]:
                        if category == taskpointcategory:
                            return "Question is in use."
                questionpage = request.graphdata.getpage(pagename)
                linking_in = questionpage.get('in', {})
                pagelist = linking_in.get("question", [])
                for answerpage in pagelist:
                    meta = getmetas(request, request.graphdata, answerpage, ["WikiCategory"])
                    for category, type in meta["WikiCategory"]:
                        if category == answercategory:
                            linkedpage = request.graphdata.getpage(answerpage)
                            linking = linkedpage.get('in', {})
                            tiplist = linking.get("answer", [])
                            for tippage in tiplist:
                                tipmeta = getmetas(request, request.graphdata, tippage, ["WikiCategory"])
                                for category, type in tipmeta["WikiCategory"]:
                                    if category == tipcategory:
                                        tippage = PageEditor(request, tippage, do_editor_backup=0)
                                        if tippage.exists():
                                            tippage.deletePage()
                                        break
                            answerpage = PageEditor(request, answerpage, do_editor_backup=0)
                            if answerpage.exists():
                                answerpage.deletePage()
                            break
                page.deletePage()
                break
        return "Success"
    else:
        return "Page doesn't exist!"

def _enter_page(request, pagename):
    request.http_headers()
    _ = request.getText
    
    request.theme.send_title(_('Teacher Tools'), formatted=False,
	html_head='<script type="text/javascript" src="%s/common/js/mootools-1.2-core-yc.js"></script>' % request.cfg.url_prefix_static)
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter

    request.write(request.page.formatter.startContent("content"))

def _exit_page(request, pagename):
    # End content
    request.write(request.page.formatter.endContent())
    # Footer
    request.theme.send_footer(pagename)

def execute(pagename, request):
    if not hasattr(request, 'graphdata'):
        getgraphdata(request)
    if request.form.has_key('cancel'):
        url = u'%s/%s' % (request.getBaseURL(), pagename)
        request.http_redirect(url)
    elif request.form.has_key("save"):
        if request.form.has_key("questionpage"):
            try:
                questionpage = request.form["questionpage"][0]
                savequestion(request, questionpage)
                url = u'%s/%s' % (request.getBaseURL(), pagename)
                request.http_redirect(url)
            except:
                _enter_page(request, pagename)
                request.write("Failed to save the question.")
                _exit_page(request, pagename)
        else:
            savequestion(request)
            url = u'%s/%s' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
    elif request.form.has_key("type"):
        _enter_page(request, pagename)
        if request.form["type"][0] == "social":
            show_socialform(request)
        else:
            show_basicform(request)
        _exit_page(request, pagename)
    elif request.form.has_key("delete") and request.form.has_key("question"):
        try:
            page = request.form["question"][0]
            msg = delete(request, page)
        except:
            msg = "Failed to delete the question."
        if msg == "Success":
            url = u'%s/%s' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
        else:
            _enter_page(request, pagename)
            request.write(msg)
            _exit_page(request, pagename)
    elif request.form.has_key("edit") and request.form.has_key("question"):
        questionpage = request.form["question"][0]
        _enter_page(request, pagename)
        show_basicform(request, questionpage)
        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        show_typeselector(request)
        _exit_page(request, pagename)
