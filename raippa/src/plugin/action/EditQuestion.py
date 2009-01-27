import os

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.action.AttachFile import getAttachDir

from graphingwiki.editing import metatable_parseargs
from graphingwiki.editing import list_attachments
from graphingwiki.editing import get_metas
from graphingwiki.editing import set_metas
from graphingwiki.editing import get_keys

from raippa import addlink, randompage, pageexists, revert
from raippa import raippacategories
from raippa import RaippaUser
from raippa import Question

action_name = 'EditQuestion'

def do_upload(request, pagename, filename, content):
    if not isinstance(content, str):
        temp = content.read()
        content = temp

    if len(filename) > 1 and (filename[1] == ':' or filename[0] == '\\'):    
        bsindex = filename.rfind('\\')
        if bsindex >= 0:
            filename = filename[bsindex+1:]        

    target = wikiutil.taintfilename(filename)
    attach_dir = getAttachDir(request, pagename, create=1)
    fpath = os.path.join(attach_dir, target).encode(config.charset)
    if os.path.exists(fpath):
        try:
            os.remove(fpath)
        except:
            return False
    stream = open(fpath, 'wb')
    try:
        stream.write(content)
        stream.close()
        return True
    except:
        stream.close()
        return False

def show_questioneditor(request, questionpage=None):
    #TODO: edit lock?
    #TODO: delete attachment
    
    answerdict = dict()
    questiontext = unicode()
    note = unicode()
    types = list()
    answertype = unicode()
    doctest = unicode()
    files = unicode()

    if questionpage:
        if not pageexists(request, questionpage):
            return False

        question = Question(request, questionpage)
        answerdict = question.getanswers()

        questiontext = question.question

        if pageexists(request, question.note):
            note = Page(request, question.note).getPageText()
        else:
            note = question.note

        types = question.types

        answertype = question.answertype

        if answertype == "file":
            for answer, answeroptions in answerdict.iteritems():
                doctestpage = Page(request, answer)
                doctest = doctestpage.get_raw_body()
                doctest = "\n".join(doctest.split("\n")[1:])
                break
        else:
            doctest = unicode()

        files = unicode()
        filelist = list_attachments(request, questionpage)
        if filelist:
            for file in filelist:
                files += u'%s ' % file

    html = u'''
 <script type="text/javascript">
var tip_hiding = false;

/*	Using mootools javascript framework */
window.addEvent('domready', function(){
  /* Hide tip-fields, regexp and casesensitive checkboxes on pageload */
  typeCheck();
  $('questionTable').getElements('span').set('style', 'visibility:hidden');

  /* Making tip-fields visible for loaded wrong answers*/
 $('questionTable').getElements('input[type=radio]').each(function(el){ 
   if(el.value == 'false' && el.checked || tip_hiding == false ){ 
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
    var el = tr.getElement('span');
    if(tip_hiding){
      el.setStyle('visibility', "hidden");
    }
}
var deleted = 0;

/* Generates answerfield dynamically and sets right visibility values  */
function addField(){

var sel = document.getElementById('typeSelect').value;
var lkm = deleted;
var to = document.getElementById('questionTable').tBodies[0];
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

td2.grab(new Element('textarea', {
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
	'class' : 'tip'
});

span.grab(new Element('textarea', {
	'name' : 'tip' + lkm
  })
);

td7.grab(span);

newRow.adopt(td1, td2);
//newRow.adopt(td3, td4);
newRow.adopt(td5, td6, td7);

/* Add tip-field visibility controlling */
if(tip_hiding != false){ 
  td5.getFirst('input').addEvent('click', function(){
	var tr = this.getParent('tr');
	tr.getElement('span').style.visibility = "hidden";
  });

  td6.getFirst('input').addEvent('click', function(){
	var tr = this.getParent('tr');
	tr.getElement('span').style.visibility = "";
  });
}

$('questionTable').getFirst('tbody').grab(newRow);

//make rexp classes visible if needed
typeCheck();
}

/* Removes selected answer fields */
function rmField(){
var input, name, value, type, checked;
var tab = document.getElementById('questionTable').tBodies[0]; 
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
var filefield = $('filefield');
  if(sel === "file"){
	filefield.setStyle('display', '');
	filefield.set('name', 'answer1');
    $('questionTable').setStyle('display', 'none');
	$('fieldCreator').setStyle('display', 'none');
 }else{
	filefield.setStyle('display', 'none');
	filefield.set('name', '');
    $('questionTable').setStyle('display', '');
  	$('fieldCreator').setStyle('display', '');
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
    var ans = $$('textarea[name^=answer]');
	hasAnswer = ans.some(function(a){
	  var value = $(a.name.replace(/answer/,'value')).checked;
	  var pass = a.value.length > 0  && value;
	  return pass == true;
	});
	if(!hasAnswer){
	  var msg = "There is no right answer! Do you still want to save the question?";
	  return confirm(msg);
	}
  }else{
    $('questionTable').destroy();
  }
  return true;
}
</script>
<form id="dataform" method="POST" enctype="multipart/form-data">
<input type="hidden" name="action" value="%s">
''' % action_name

    if questionpage:
        html += u'''
<input type="hidden" name="questionpage" value="%s">
Page: <a href="%s/%s">%s</a>
''' % (questionpage, request.getBaseURL(), questionpage, questionpage)

    html += u'''
<table class="no_border">
<tr>
<td >question:</td>
<td colspan="2">
<textarea id="questionfield" name="question" rows="3" cols="70">
%s
</textarea>
</td>
<tr>
<tr>
<td>note:</td>
<td colspan="2">
<textarea name="note" rows="7" cols="70">
%s
</textarea>
</td>
<tr>
<tr>
<td>type:</td>
<td colspan="2">
<select name="type">
<option value=""> </option>
''' % (questiontext, note)

    questions, keys, s = metatable_parseargs(request, raippacategories["questioncategory"])

    alltypes = list()
    for question_in_list in questions:
        typemetas = get_metas(request, question_in_list, ["type"])
        for type in typemetas["type"]:
            if type not in alltypes:
                alltypes.append(type)
                if type in types:
                    html += u'''
<option value="%s" selected="selected">%s</option>\n''' % (type.replace('"','&quot;'), type)
                else:
                    html += u'''
<option value="%s">%s</option>\n''' % (type.replace('"','&quot;'), type)

    html += u'''
</select> &nbsp; 
<input size="30" type="text" name="type">
</td>
<tr>
<tr>
<td>image:</td>
<td colspan="2">
%s<input type="file" name="file" value="Select...">
</td>
<tr>
</table>
    <hr>
    answer type: &nbsp;<select id="typeSelect" name="answertype" onChange="typeCheck();">
''' % files

    answertypes = ["radio", "checkbox", "text", "file"]
    for type in answertypes:
        if type == answertype:
            html += u'<option value="%s" selected="selected">%s</option>\n' % (type, type)
        else:
            html += u'<option value="%s">%s</option>\n' % (type, type)

    html += u'''
    </select> &nbsp; 
    <input id="fieldCreator" type="button" name="addButton" title="Add more answer fields" value="Add new field" onClick="addField();">
<br>
<textarea id="filefield" cols="80" rows="15" name="">%s</textarea>
''' % doctest

    html += u'''
 <table id="questionTable">
<tr>
    <td style="text-align:center"><a title="Remove selected answers" style="color:red"  href="javascript: rmField();">X</a></td>
    <td style="width:250px">Answer</td>'''
    #html += u'''
    #<td title="Case sensitive" class="rexp" style="width:110px; text-align: center">Case sensitive</td>
    #<td title="Regular Expression" class="rexp" style="width:75px; text-align: center">Regexp</td>
    #'''
    html += u'''
    <td style="width:50px">Right</td>
    <td style="width:50px">Wrong</td>
    <td style="width:275px">Tip</td>
</tr>'''

    if questionpage and answertype != "file":
        number = 0

        for answer, answeroptions in answerdict.iteritems():
            number += 1
            html += u'''
<tr id="ansTr%s">
<td><input type="checkbox" name="rmcheck%s" value="rm" title="Select this answer to be deleted"></td>
<td><textarea name="answer%s">%s</textarea></td>
''' % (number, number, number, answer.replace('"','&quot;'))

            #regexp and CaseSens goes here
            value = answeroptions[0]
            if value == "true":
                html += u'''
<td>
<input type="radio" id="value%s" name="value%s" value="true" onClick="hide(this);" checked>
</td>
<td>
<input type="radio" name="value%s" value="false" onClick="show(this);">
</td>
''' % (number, number, number)
            else:
                html += u'''
<td>
<input type="radio" id="value%s" name="value%s" value="true" onClick="hide(this);">
</td>
<td>
<input type="radio" name="value%s" value="false" onClick="show(this);" checked>
</td>
''' % (number, number, number)

            tip = answeroptions[1]
            if tip:
                tips = get_metas(request, tip, ["tip"])
                if tips["tip"]:
                    tipnote = tips["tip"].pop()
                else:
                    tipnote = unicode()

                html += u'''
<td><span class="tip"><textarea name="tip%s">%s</textarea></span></td>
</tr>
''' % (number, tipnote.replace('"','&quot;'))
            else:
                html += u'''
<td><span class="tip"><textarea name="tip%s"></textarea></span></td> 
</tr>
''' % number

    else:
        for answernumber in range(1,5):
            html += '''
<tr id="ansTr%s">
<td>
<input type="checkbox" name="rmcheck%s" value="rm" title="Select this answer to be deleted">
</td>
<td>
<textarea name="answer%s"></textarea>
</td>
''' % (answernumber, answernumber, answernumber)

    #<td class="rexp"><input type="checkbox" name="cSens%s" value="true" title="Answer is case sensitive"></td>
    #<td class="rexp"><input type="checkbox" name="rexp%s"value="true" title="Answer is regular expression" ></td>

            html += '''
<td>
<input type="radio" id="value%s" name="value%s" value="true" onClick="hide(this);" checked >
</td>
<td>
<input type="radio" name="value%s" value="false" onClick="show(this);">
</td>
<td>
<span class="tip"><textarea name="tip%s"></textarea></span>
</td>
</tr>
''' % (answernumber, answernumber, answernumber, answernumber)

    html += u'''
</table>
<hr>
<input type="submit" name="save" value="Save" onclick="return submitCheck(this);">
<input type="submit" name="cancel" value="Cancel" onclick="return submitCheck(this);">
</form>
'''

    return html

def save_question(request, questiondata, questionpage=None):
    #TODO: delete attachment
    _ = request.getText

    backup = dict()
    newpages = list()
    failures = list()

    if questionpage:
        if not pageexists(request, questionpage):
            return u'The page %s does not exist.' % questionpage
        else:
            backup[questionpage] = Page(request, questionpage).get_real_rev()

        oldanswers = Question(request, questionpage).getanswers()
    else:
        questionpage = randompage(request, "Question")
        newpages.append(questionpage)
        oldanswers = dict()

    questiontext = questiondata.get("question", None)
    if not questiontext:
        return u'Missing question.'

    types = questiondata.get("types", list())
    answertype = questiondata.get("answertype", "text")
    note = questiondata.get("note", None)
    answers = questiondata.get("answers", dict())
    filename = questiondata.get("filename", None)
    filecontent = questiondata.get("filecontent", None)


    data = {"question": [questiontext],
            "answertype": [answertype],
            "type": types}

    #save note
    notepage = questionpage + "/note"
    if note:
        data["note"] = [addlink(notepage)]
        if pageexists(request, notepage):
            backup[notepage] = Page(request, notepage).get_real_rev()

        success = False
        page = PageEditor(request, notepage)
        try:
            msg = page.saveText(note, page.get_real_rev())
            if msg == _("Thank you for your changes. Your attention to detail is appreciated."):
                success = True 
            else:
                success = False
        except page.Unchanged:
            success = True
        except:
            success = False

        if not success: 
            for page, rev in backup.iteritems():
                revert(request, page, rev)
            return u'Question was not saved. Failed to save the note (%s).' % notepage

    elif not note and pageexists(request, notepage):
        #delete unused notepage
        backup[notepage] = Page(request, notepage).get_real_rev()

        success = False
        try:
            success, msg = PageEditor(request, notepage, do_editor_backup=0).deletePage()
        except:
            success = False

        if not success:
           failures.append(notepage)

    #save questionpage
    if questionpage not in newpages:
        oldkeys = get_keys(request, questionpage)
        remove = {questionpage: oldkeys}
    else:
        remove = dict()

    data = {questionpage: data}
    result, msg = set_metas(request, remove, dict(), data)

    if not result:
        for page, rev in backup.iteritems():
            revert(request, page, rev)
        return u'Failed to save the question (%s).' % questionpage

    text = u'''
----
<<MetaInclude(%s,question=%s,,,,editlink)>>''' %(raippacategories["answercategory"], questionpage)

    oldcontent = Page(request, questionpage).get_raw_body()
    if text not in oldcontent:
        content = oldcontent + text
        #it's not that bad is this fails so we just pass
        try:
            page = PageEditor(request, questionpage)
            msg = page.saveText(content, page.get_real_rev())
        except:
            pass

    data = {questionpage: {"gwikicategory": [raippacategories["questioncategory"]]}}
    result, msg = set_metas(request, dict(), dict(), data)
    if not result:
        for page, rev in backup.iteritems():
            revert(request, page, rev)
        return u'Failed to save category for %s.' % questionpage

    if filename and filecontent:
        if not do_upload(request, questionpage, filename, filecontent):
            for page, rev in backup.iteritems():
                revert(request, page, rev)
            return u'Question was not saved. Failed to save the attachment.'
    
    #collect reusable pages
    reusable_answers = list()
    reusable_tips = list()
    for answer in oldanswers.copy():
        if not answers.has_key(answer):
            answerpage = oldanswers.get(answer, [None, None, None, None])[3]
            if pageexists(request, answerpage):
                reusable_answers.append(answerpage)

            tippage = oldanswers.get(answer, [None, None, None, None])[1]
            if tippage and pageexists(request, tippage):
                backup[tippage] = Page(request, tippage).get_real_rev()
                reusable_tips.append(tippage)
            del oldanswers[answer]

    #answers & tips
    for answer in answers:
        value = answers[answer][0]
        tip = answers[answer][1]

        if answer in oldanswers:
            answerpage = oldanswers.get(answer, [None, None, None, None])[3]
            backup[answerpage] = Page(request, answerpage).get_real_rev() 

            tippage = oldanswers.get(answer, [None, None, None, None])[1]
            if tip:
                if tippage:
                    backup[tippage] = Page(request, tippage).get_real_rev()
                else:
                    if len(reusable_tips) > 0:
                        tippage = reusable_tips.pop()
                    else:
                        tippage = randompage(request, "Tip")
                        newpages.append(tippage)
            else:
                if tippage:
                    backup[tippage] = Page(request, tippage).get_real_rev()
                    reusable_tips.append(tippage)

            del oldanswers[answer]
        else:
            if len(reusable_answers) > 0:
                answerpage = reusable_answers.pop()
            else:
                answerpage = randompage(request, "Answer")
                newpages.append(answerpage)
            if tip:
                if len(reusable_tips) > 0:
                    tippage = reusable_tips.pop()
                else:
                    tippage = randompage(request, "Tip")
                    newpages.append(tippage)

        data = {"question": [addlink(questionpage)],
                "true": list(),
                "false": list()}
        
        docpage = answerpage + "/doctests"
        if answertype == "file":
            #save doctest
            content = "#FORMAT plain\n" + answer
            if pageexists(request, docpage):
                backup[docpage] = Page(request, docpage).get_real_rev()

            success = False
            page = PageEditor(request, docpage)
            try:
                msg = page.saveText(content, page.get_real_rev())
                if msg == _("Thank you for your changes. Your attention to detail is appreciated."):
                    success = True 
                else:
                    success = False
            except page.Unchanged:
                success = True
            except:
                success = False

            if not success:
                for page, rev in backup.iteritems():
                    revert(request, page, rev)
                return u'Question was not saved. Failed to save the doctest (%s).' % docpage
            data["true"] = [addlink(docpage)]
        else:
            #delete unused doctest page
            if pageexists(request, docpage):
                backup[docpage] = Page(request, docpage).get_real_rev()
                success = False
                try:
                    success, msg = PageEditor(request, docpage, do_editor_backup=0).deletePage()
                except:                                                            
                    success = False

                if not success:
                    failures.append(docpage)

            data[value] = [answer]
        
        #save answer
        if answerpage not in newpages:
            oldkeys = get_keys(request, answerpage)
            remove = {answerpage: oldkeys}
        else:
            remove = dict()

        data = {answerpage: data}
        result, msg = set_metas(request, remove, dict(), data)

        if not result:
            for page, rev in backup.iteritems():
                revert(request, page, rev)
            return u'Question was not saved. Failed to save the answer (%s).' % answerpage

        text = u'''
----
<<MetaInclude(%s,answer=%s,,,,editlink)>>''' % (raippacategories["tipcategory"], answerpage)

        oldcontent = Page(request, answerpage).get_raw_body()
        if text not in oldcontent:
            content = oldcontent + text
            #it's not that bad is this fails so we just pass
            try:
                page = PageEditor(request, answerpage)
                msg = page.saveText(content, page.get_real_rev())
            except:
                pass

        data = {answerpage: {"gwikicategory": [raippacategories["answercategory"]]}}
        result, msg = set_metas(request, dict(), dict(), data)
        if not result:
            for page, rev in backup.iteritems():
                revert(request, page, rev)
            return u'Failed to save category for %s.' % answerpage

        #save tip
        if tip:
            if tippage not in newpages:
                oldkeys = get_keys(request, tippage)
                remove = {tippage: oldkeys}
            else:
                remove = dict()

            data = {tippage: {"answer":[addlink(answerpage)], 
                              "tip": [tip],
                              "gwikicategory": [raippacategories["tipcategory"]]}}

            result, msg = set_metas(request, remove, dict(), data)
            if not result:
                for page, rev in backup.iteritems():
                    revert(request, page, rev)
                return u'Question was not saved. Failed to save the tip (%s).' % tippage

    #delete old, unused pages
    reusable_answers.extend(reusable_tips)
    for page in reusable_answers:
        if pageexists(request, page):
            success = False
            try:
                success, msg = PageEditor(request, page, do_editor_backup=0).deletePage()
            except:
                success = False

            if not success:
                failures.append(page)

    for answer in oldanswers:
        page = oldanswers.get(answer, [None, None, None, None])[3]
        tip = oldanswers.get(answer, [None, None, None, None])[1]
        success = False
        try:
            success, msg = PageEditor(request, page, do_editor_backup=0).deletePage()         
        except:
            success = False
        if not success:
            failures.append(page)

        success = False
        try:
            success, msg = PageEditor(request, tip, do_editor_backup=0).deletePage()
        except:
            success = False
        if not success:
            failures.append(tip)

    if failures:
        return u'Failed to delete unused page(s) %s.' % u', '.join(failures)
    else:
        return u'Thank you for your changes. Your attention to detail is appreciated.'

def delete_question(request, pagename):
    #TODO: delete attachments
    failures = list()

    if pageexists(request, pagename):
        categorymeta = get_metas(request, pagename, ["gwikicategory"])
        categories =  categorymeta["gwikicategory"]

        if raippacategories["questioncategory"] in categories:
            linking_in = request.graphdata.getpage(pagename).get('in', {})
            #copy of list, otherwise for loop goes crazy when deleting pages
            linkinglist = linking_in.get("question", [])[:]

            #let's check if some task uses this question
            for page in linkinglist:
                categories = get_metas(request, page, ["gwikicategory"])
                if raippacategories["taskpointcategory"] in categories["gwikicategory"]:
                    return u'Sorry, can not delete this question because %s uses it.' % page

            #delete question
            success = False
            try:
               success, msg = PageEditor(request, pagename, do_editor_backup=0).deletePage()
            except:
               success = False

            if not success:
                return u'Failed to delete the question (%s).' % pagename

            #delete note
            notepage = pagename + "/note"
            if pageexists(request, notepage):
                success = False
                try:
                    success, msg = PageEditor(request, notepage, do_editor_backup=0).deletePage()
                except:
                    success = False

                if not success:
                    faiures.append(notepage)

            #delete answers
            for page in linkinglist:
                if pageexists(request, page):
                    categories = get_metas(request, page, ["gwikicategory"])
                    if raippacategories["answercategory"] in categories["gwikicategory"]:
                        linking = request.graphdata.getpage(page).get('in', {})
                        pagelist = linking.get("answer", [])[:]

                        #delete tips
                        for tippage in pagelist:
                            if pageexists(request, tippage):
                                tipmeta = get_metas(request, tippage, ["gwikicategory"])
                                if raippacategories["tipcategory"] in tipmeta["gwikicategory"]:
                                    success = False
                                    try:
                                        success, msg = PageEditor(request, tippage, do_editor_backup=0).deletePage()
                                    except:
                                        success = False

                                    if not success:
                                        failures.append(tippage)

                        success = False
                        try:
                            success, msg = PageEditor(request, page, do_editor_backup=0).deletePage()
                        except:
                            success = False
                        
                        if not success:
                            failures.append(page)

            if failures:
                message = u'Failed to delete page(s) %s.' % u', '.join(failures)
            else:
                message = u'Question was successfully deleted!'

            return message
        else:
            return u'Page is not in question category.'
    else:
        return u'The page %s does not exist.' % pagename

def _enter_page(request, pagename):
    request.http_headers()
    
    request.theme.send_title('Teacher Tools', formatted=False,
	html_head='<script type="text/javascript" src="%s/raippajs/mootools-1.2-core-yc.js"></script>' % request.cfg.url_prefix_static)
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
    ruser = RaippaUser(request)
    if not ruser.isTeacher():
        action = {"action_name": action_name}
        message = u'You are not allowed to do %(action_name)s on this page.' % action
        Page(request, pagename).send_page(msg=message)

    if request.form.has_key('cancel'):
        message = u'Edit was cancelled.'
        Page(request, pagename).send_page(msg=message)

    elif request.form.has_key("save"):
        questionpage = request.form.get("questionpage", list())
        if len(questionpage) > 0:
            questionpage = questionpage.pop()
        else:
            questionpage = None

        questiondata = {"types": request.form.get("type", list()),
                        "answers": dict(),
                        "filename": request.form.get("file__filename__", None)}

        question = request.form.get("question", list())
        if len(question) > 0:
            q_temp = question.pop()
            q_temp = q_temp.strip().replace("\n"," ").replace("\r"," ")
            questiondata["question"] = q_temp
        else:
            Page(request, pagename).send_page(msg=u'Missing question.')
            return None

        answertype = request.form.get("answertype", list())
        if len(answertype) > 0:
            questiondata["answertype"] = answertype.pop()
        else:
            questiondata["answertype"] = u'text'

        note = request.form.get("note", list())
        if len(note) > 0:
            n_temp = note.pop()
            n_temp = n_temp.strip().replace("\n"," ").replace("\r"," ")
            questiondata["note"] = n_temp
        else:
            questiondata["note"] = unicode()

        filecontent = request.form.get("file", list())
        if len(filecontent) > 0:
            questiondata["filecontent"] =  filecontent.pop()
        else:
            questiondata["filecontent"] = None

        for key in request.form:
            if key != "answertype" and key.startswith("answer"):
                a_temp = request.form.get(key, [unicode()])[0]
                answer = a_temp.strip().replace("\n"," ").replace("\r"," ")

                if not answer:
                    continue

                answernumber = key[6:]
                if questiondata["answertype"] == "file":
                    value = u'true'
                    tip = None
                else:
                    value = request.form.get("value"+answernumber, [None])[0]
                    if not value:
                        continue
                    tip = request.form.get("tip"+answernumber, [None])[0]

                questiondata["answers"][answer] = [value, tip]

        message = save_question(request, questiondata, questionpage)
        Page(request, pagename).send_page(msg=message)
        
    elif request.form.has_key("delete") and request.form.has_key("question"):
        questionpage = request.form.get("question", [""])[0]
        message = delete_question(request, questionpage)
        Page(request, pagename).send_page(msg=message)

    else:
        if request.form.has_key("new"):
            questionpage = None
        else: 
            questionpage = request.form.get("question", [None])[0]
            if not questionpage:
                questionpage = pagename
                
        html = show_questioneditor(request, questionpage)

        if not html:
            message = u'The page %s does not exist.' % questionpage
            Page(request, pagename).send_page(msg=message)
        else:
            _enter_page(request, pagename)
            request.write(html)
            _exit_page(request, pagename)

