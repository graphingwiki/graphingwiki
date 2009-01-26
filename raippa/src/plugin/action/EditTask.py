# -*- coding: utf-8 -*-"
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import get_metas
from graphingwiki.editing import set_metas
from graphingwiki.editing import get_keys
from graphingwiki.editing import metatable_parseargs

from raippa import addlink, randompage, revert, getflow, pageexists
from raippa import raippacategories
from raippa import RaippaUser

action_name = 'EditTask'

def taskform(request, task=None):
    if task:
        metas = get_metas(request, task, ["title","description", "type", "subject"])

        if metas["title"]:
            title = metas["title"].pop()
        else:
            title = unicode() 

        if metas["description"]:
            description = metas["description"].pop()
        else:
            description = unicode()

        if metas["type"]:
            type = metas["type"].pop()
        else:
            type = "basic"

        subjects = metas["subject"]

        try:
            flow = getflow(request, task)
        except:
            flow = dict()
        recapdict = dict()
        questions = list()
        for taskpoint, questionpage in flow:
            questions.append(questionpage)
            metas = get_metas(request, taskpoint, ["recap"])
            if metas["recap"]:
                recapdict[questionpage] = metas["recap"].pop()
    else:
        title = unicode()
        subjects = list()
        description = unicode()
        type = "basic"
        flow = list()
        questions = list()
        recapdict = dict()

    pagehtml = '''
<script type="text/javascript">
window.addEvent('domready', function(){

    //loading previously selected questions
    addOpts();

    //hiding all source questions except the default one
    $$('select[id^=type_]').setStyle('display' , 'none');
    var val = $($('typeSelect').value) ? $('typeSelect').value : 'type_None';
    $(val).setStyle('display','');

    //showing Q list selected in type selector
    $('typeSelect').addEvent('change',function(){
        var val = this.value;
        if($(val)){
            $$('select[id^=type_]').setStyle('display' , 'none');
            $(val).setStyle('display','');
        }
    });

    //selecting all options with definition title
    var links = $$('option').filter(function(el){
        return el.title.match("::") ? true : false;
    });
    //var tips = new Tips(links);

    //draw info box for source Q's on click
    var sels = $('selstr').getElements('select');
    sels.addEvent('change',function(){
        var opt = $$('option[value='+this.value+']');
        if(opt && opt[0].title){
            drawInfo(opt[0]);
        }
      });

    links.addEvent('mouseenter', function(){
      //drawInfo(this);
      });
   });

/*Draw infobox for el*/
function drawInfo(el){
       var div = $('infodiv');
      if(div){
        div.destroy();
      }
      $('info').setStyle('background-color','#caffee');
      var div = new Element('div', {
        'id' : 'infodiv',
        'styles' : {
            'width' : '100%'
          }
        });

      var desc = new Element('p', {
        'text' : el.title,
        'styles' : {
              'font-weight':'bold',
              'margin-right' : '50px',
              'float' :'left'
          }
        });
      div.grab(desc);

     desc.adopt(new Element('br'), 
        new Element('input', {
        'type' : 'button',
        'value' : 'Edit',
        'events' : {
            'click' : function(){
              saveTaskData(el);
            }
          }
        }));
    var rec = $(el.value +'_recap');
    var redo = $(el.value + '_redo');
    if(rec && redo){

    var recsel = createPenaltySel(el, rec.value).setStyles({
        'display':'',
        'position' : '',
        'float':'right'
    }).addEvent('change',function(){
        rec.set('value', this.value);
         rec.fireEvent('change');
    });
    var menu = new Element('div', {
         'styles' : {
            'float' : 'right',
            'clear' : 'right'
          }
          });

    menu.adopt(new Element('input', {
        'type':'checkbox',
        'id':'doMany',
        'checked' : redo.value,
        'events':{
            'change' : function(){
                redo.value = this.checked;
                }
            }
        }),new Element('label',{
            'for' : 'doMany',
            'text': 'Do multiple times'
        }), new Element('br'));

    menu.adopt(recsel);
    div.grab(menu);
    }
    $('info').adopt(div);
  }


/* Save task form using ajax and redirect to Q editor*/
function saveTaskData(el){
 
 $('info').addClass('ajax_loading');
 selectAllOptions('flist');
 var form = $('taskForm');
 var cancel = form.getElement('input[name=cancel]');
 if(cancel){
 cancel.destroy();
 }
 form.set('send',{
    method : 'post',
    onSuccess : function(response){
      if(el){
        toQuestionEditor(el.value);
      }
    $('info').removeClass('ajax_loading');
  }
 });
 url = location.href;
 form.send(url);
}

/* Creating form which redirects to Q editor*/
function toQuestionEditor(question){
  var form = new Element('form', {
    'method' : 'post'
    });
  form.grab(new Element('input', {
    'type' : 'hidden',
    'name' : 'action',
    'value' : 'EditQuestion'
    }));
if(question){
form.grab(new Element('input', {
    'type' : 'hidden',
    'name' : 'question',
    'value' : question
    }));

form.grab(new Element('input', {
    'type' : 'hidden',
    'name' : 'edit',
    'value' : 'edit'
    }));
}else{
  form.grab(new Element('input', {
    'type' : 'hidden',
    'name' : 'new',
    'value' : 'new'
    }));
  }
 form.inject(document.body);
 form.submit();
}


/* Return a select including all posible values */
function createPenaltySel(el, defVal, pos){
    var opt = $(el);
    var sel = opt.getParent('select');
    var noPenalty = 'selected';
    if(defVal){
	    noPenalty = '';
	}
    var form = $('taskForm');
    var select = $(opt.value+'_recap_sel');

    if(select != null){
	    select.value = defVal;
    }else{
	var select = new Element('select', {
	'id' : opt.value+'_recap_sel',
	'name' : opt.value+'_recap_sel',
	'size' : 1,
	'events' : {
		'change' : function(){
            $(opt.value + '_recap').value = this.value;
		  if(this.value == ''){
			  opt.setStyle('background-color', '');
			}else{
			  opt.setStyle('background-color', 'red');
			}
			if(window.opera){
			  document.body.style += ""; // Force Opera redraw.
			}

		  }
	  }
	});

  select.grab(new Element('option',{
	  'value' : '',
	  'text' : 'no recap',
	  'selected': noPenalty
	}));\n'''
    tasklist, metakeys, styles = metatable_parseargs(request, raippacategories["taskcategory"])
    for ti in tasklist:
        data = get_metas(request, ti, ["title"])
        if data["title"]:
            desc = data["title"].pop()
        else:
            desc = ti+" (missing title)"
        pagehtml += u'''
  select.grab(new Element('option', {
	  'value' : '%s',
	  'text' : '%s'
	}));
  if(defVal == '%s'){
	select.getLast('option').set('selected','selected');
	}\n''' % (ti, desc,ti)

    pagehtml += u'''
  return select;
  }
}

function moveSel(theSel, dir){
  var opts = theSel.getChildren('option');
  if(dir == '+') opts.reverse();
  opts.each(function(el){
	if(el.selected){
	  if(dir == '-' && el.getPrevious('option')){
		el.inject(el.getPrevious('option'), 'before');
	  }else if(dir == '+' && el.getNext('option')){
		el.inject(el.getNext('option'), 'after');
	  }
	  }
	});

}

function addOption(theSel, theText, theValue, recap, redo)
{
	var newOpt = new Element('option', {
	  'text' : theText,
	  'title' : theText +'::',
	  'value' : theValue
});
    var sel = $(theSel);
    sel.grab(newOpt);

	if(recap){
	  newOpt.setStyle('background-color', 'red');
	}

    $('taskForm').grab(new Element('input', {
        'type': 'hidden',
        'id': theValue +'_recap',
        'name': theValue +'_recap',
        'value': recap
        }));

    $('taskForm').grab(new Element('input', {
        'type': 'hidden',
        'id': theValue +'_redo',
        'name': theValue +'_redo',
        'value': redo
        }));


	  newOpt.setStyle('width', 'auto');

sel.addEvent('click', function(event){
		    if(theSel.id == 'flist'){
			    sel = $(theSel).getChildren('option').filter(function(el){
				    return el.selected == true
				});
				if(sel){
				    createPenaltySel(sel[0]);
				}
			}
		});

sel.addEvent('keyup', function(event){
	    $(theSel).fireEvent('click');
    });
}


/* Deletes select option and recap/redo if exits*/
function deleteOption(theSel, theIndex)
{
    var selLength = theSel.length;
    if(selLength > 0)
    {
		var recap = $(theSel.options[theIndex].value +'_recap');
		if(recap != null){
			recap.destroy();
		  }
        var redo = $(theSel.options[theIndex].value +'_redo');
        if(redo){
            redo.destroy();
        }
        theSel.options[theIndex] = null;
    }
}


/* Move one or more selected options from select to other */
function moveOptions(theSelFrom, theSelTo)
{
    var selLength = theSelFrom.length;
    var selectedText = new Array();
    var selectedValues = new Array();
    var selectedCount = 0;

    var i;
    for(i=selLength-1; i>=0; i--)
    {
        if(theSelFrom.options[i].selected)
        {
            selectedText[selectedCount] = theSelFrom.options[i].text;
            selectedValues[selectedCount] = theSelFrom.options[i].value;
            deleteOption(theSelFrom, i);
            selectedCount++;
        }
    }

    for(i=selectedCount-1; i>=0; i--)
    {
        addOption(theSelTo, selectedText[i], selectedValues[i]);
    }

}


/* Select all options and insert recap data to form */
function selectAllOptions(selStr)
{
    $(selStr).getChildren('option').each(function(el){
	  el.selected = true;
	});

    var infodiv = $('infodiv');
    if(infodiv){
        infodiv.destroy();
    }
}


/* Checks if form is filled correctly*/
function submitCheck(button){
  if(button.value == "Cancel"){
    return true;
    }

 if($('title').value == ''){
    alert('Missing title!');
    return false;
    }

 if($('description').value == ''){
    alert('Missing description!');
    return false;
    }

  selectAllOptions('flist');
  return true;
}

</script>
'''
    if task:
        pagehtml += u'Page: <a href="%s/%s">%s</a><br>\n' % (request.getBaseURL(), task, task)

    pagehtml += u'''
select questions:<br>
<form method="POST" action="%s" onsubmit="saveTaskData();">
    <input type="hidden" name="action" value="EditQuestion">
    <input type='submit' name='new' value='NewQuestion'>
</form>
<form id="taskForm" method="post" name="taskForm" action="">
<table border="0">
<tr><td colspan="4" id="info">
</td></tr>
''' % request.request_uri.split("?")[0]
    pagelist, keys, styles = metatable_parseargs(request, raippacategories["questioncategory"])
    typedict = {None:list()}
    for page in pagelist:
        if page not in questions:
            metas = get_metas(request, page, ["type", "question"])
            if metas["question"]:
                question = metas["question"].pop()
            else:
                #TODO: report missing question
                question = page

            if metas["type"]:
                for type in metas["type"]:
                    if not typedict.has_key(type):
                        typedict[type] = list()
                    typedict[type].append((page, question))
            else:
                typedict[None].append((page, question))
    #typelist
    pagehtml += u'question type: <select id="typeSelect" name="question_type">\n'
    for type in typedict:
        pagehtml += '<option value="type_%s">%s\n' % (type, type)
    pagehtml += u'</select><tr id="selstr"><td id="qlist_td">'

    #questionlists
    for type, questionlist in typedict.iteritems():
        pagehtml += u'''<select size="10" style="width:200px;" id="type_%s" name="questionList"
        multiple="multiple">\n''' % type
        for questionpagename, questiontext in questionlist:
            pagehtml += u'<option name="question" title="%s:: " value="%s">%s</option>\n' % (questiontext.replace('"','&quot;'), questionpagename, questiontext)
        pagehtml += u'</select>\n'
    pagehtml += u'''
    </td>
    <td align="center" valign="middle">
        <input type="button" value="--&gt;"
         onclick="moveOptions($($('typeSelect').value), taskForm.flowlist);"><br>
        <input type="button" value="&lt;--"
         onclick="moveOptions(taskForm.flowlist, $($('typeSelect').value));">
    </td>
    <input id="action" type="hidden" name="action" value="%s">\n''' % action_name
    if task:
        pagehtml += u'<input type="hidden" name="task" value="%s">\n' % task
    pagehtml += '''
    <td id="flowtd">
        <select name="flowlist" style="width:200px;" id="flist" size="10"
		multiple="multiple"></select><script type="text/javascript">
		function addOpts(){
		\n'''
    for page in questions:
        metas = get_metas(request, page, ["question"])
        if metas["question"]:
            question = metas["question"].pop()
        else:
            #TODO: report missing question
            question = page
        pagehtml +=u'addOption(document.getElementById("flist"),"%s","%s","%s");\n' %(question.replace('"','&quot;'),page,recapdict.get(page,""))
    pagehtml += '''
		}
        </script>
    </td><td style="width: 15px">
	<input type="button" value="&uarr;" onclick="moveSel($('flist'), '-');"><br>
	<input type="button" value="&darr;" onclick="moveSel($('flist'), '+');"></td>
    </tr>
</table>
select task type: <select name="type">\n'''
    typelist = ['basic', 'exam', 'questionary']
    for item in typelist:
        if item == type:
            pagehtml += '<option selected value="%s">%s\n' % (item, item)
        else:
            pagehtml += '<option value="%s">%s\n' % (item, item)
    pagehtml += '''
</select>
<br>
subject:
<select name="subject">
<option value=""> </option>\n'''
    tasklist, metakeys, styles = metatable_parseargs(request, raippacategories["taskcategory"])
    tasktypes = list()
    for task_in_list in tasklist:
        metas = get_metas(request, task_in_list, ["subject"])
        tasktypes.extend(metas["subject"])

    for type in list(set(tasktypes)):
        if task:
            if type in subjects:
                pagehtml += u'<option value="%s" selected="selected">%s</option>\n' % (type, type)
            else:
                pagehtml += u'<option value="%s">%s</option>\n' % (type, type)
        else:
            pagehtml += u'<option value="%s">%s</option>\n' % (type, type)
    pagehtml += u'''
</select> &nbsp;
<input size="30" type="text" name="subject">
<br>title:
<br>
<input type="text" id="title" size="40" name="title" value="%s">
<br>description:
<br>
<textarea id="description" name="description" rows="10" cols="40">%s</textarea><br>
''' % (title, description)
    pagehtml += '''
<input type="submit" name="save" value="Save" onclick="return submitCheck(this);">
<input type="submit" name="cancel" value="Cancel" onclick="return submitCheck(this);">
</form>
'''
    request.write(u'%s' % pagehtml)

def save_task(request, taskdata, taskpage=None):
    _ = request.getText
    newpages = list()
    backup = dict()

    title = taskdata.get("title", None)
    description = taskdata.get("description", None)
    tasktype = taskdata.get("type", "basic")
    flowlist = taskdata.get("flowlist", list())
    subjects = taskdata.get("subject", list())
    recapdict = taskdata.get("recap", dict())

    if not title:
        return "Missing task title."
    if not description:
        return "Missing task description."

    #handle new tasks
    if not taskpage:
        taskpage = randompage(request, "Task")
        taskpoint = randompage(request, taskpage)

        data = {"title": [title],
                "description": [description],
                "type": [tasktype],
                "subject": subjects,
                "gwikicategory": [raippacategories["taskcategory"]]}

        if len(flowlist) > 0:
            data["start"] = [addlink(taskpoint)]

        data = {taskpage: data}
        newpages.append(taskpage)
        result, msg = set_metas(request, dict(), dict(), data)
        if not result:
            #TODO: delete newpages
            return u'Failed to save the task (%s).' % taskpage

        for index, questionpage in enumerate(flowlist):
            pointdata = {"question": [addlink(questionpage)],
                         "gwikicategory": [raippacategories["taskpointcategory"]]}

            recaptask = recapdict.get(questionpage, None)
            if recaptask:
                pointdata["recap"] = addlink(recaptask)

            if index >= len(flowlist)-1:
                nexttaskpoint = unicode()
                pointdata["next"] = ["end"]
            else:
                nexttaskpoint = randompage(request, taskpage)
                pointdata["next"] = [addlink(nexttaskpoint)]

            pointdata = {taskpoint: pointdata}
            newpages.append(taskpoint)
            result, msg = set_metas(request, dict(), dict(), pointdata)
            if not request:
                #TODO: delete newpages
                return u'Failed to save the taskpoint (%s).' % taskpoint

            taskpoint = nexttaskpoint

        return u'Thank you for your changes. Your attention to detail is appreciated.'

    else:
        try:
            oldflow = getflow(request, taskpage)
        except:
            oldflow = dict()
        oldquestions = list()
        for taskpoint, questionpage in oldflow:
            oldquestions.append(questionpage)

        #save just taskpage if flow haven't changed
        if oldquestions == flowlist and not recapdict:
            startmeta = get_metas(request, taskpage, ["start"])
            data = {"title": [title],
                    "description": [description],
                    "type": [tasktype],
                    "subject": subjects,
                    "gwikicategory": [raippacategories["taskcategory"]]}

            if startmeta["start"]:
                data["start"] = startmeta["start"]
            data = {taskpage: data}
            
            oldkeys = get_keys(request, taskpage)
            remove = {taskpage: oldkeys}

            backup[taskpage] = Page(request, taskpage).get_real_rev()
            result, msg = set_metas(request, remove, dict(), data)
            if not result:
                for page, rev in backup.iteritems():
                    revert(request, page, rev)
                return u'Failed to save the task (%s).' % taskpage

            return u'Thank you for your changes. Your attention to detail is appreciated.'

        #save handle new flow
        else:
            newflow = list()
            reusable = list()
            #find out which taskpoint can be reused
            for taskpoint, questionpage in oldflow:
                if questionpage not in flowlist:
                    reusable.append(taskpoint)
                    backup[taskpoint] = Page(request, taskpoint).get_real_rev()

            for question in flowlist:
                #if question allready has taskpoint, use it
                for oldtaskpoint, oldquestion in oldflow:
                    if question == oldquestion:
                        taskpoint = oldtaskpoint
                        backup[oldtaskpoint] = Page(request, oldtaskpoint).get_real_rev()
                        break
                else:
                    if len(reusable) > 0:
                        taskpoint = reusable.pop()
                    else:
                        taskpoint = randompage(request, taskpage)
                newflow.append((taskpoint, question))

            #create data dict for taskpoint
            for index, tasktuple in enumerate(newflow):
                taskpoint = tasktuple[0]
                question = tasktuple[1]

                if index >= len(newflow)-1:
                    nexttaskpoint = "end"
                else:
                    nexttaskpoint = newflow[index+1][0]

                data  = {"question": [addlink(question)],
                         "next": [nexttaskpoint],
                         "gwikicategory": [raippacategories["taskpointcategory"]]}

                recaptask = recapdict.get(question, None)
                if recaptask:
                    data["recap"] = addlink(recaptask)

                if pageexists(request, taskpoint):
                    oldkeys = get_keys(request, taskpoint)
                    remove = {taskpoint: oldkeys}
                    backup[taskpoint] = Page(request, taskpoint).get_real_rev()
                else:
                    newpages.append(taskpoint)
                    remove = dict()

                data = {taskpoint: data}
                #save datas and handle errors
                result, msg = set_metas(request, remove, dict(), data)
                if not result:
                    for page, rev in backup.iteritems():
                        revert(request, page, rev)
                    #TODO: delete newpages
                    return u'Failed to save the task (%s).' % taskpage

            #handle taskpage datas
            data = {"title": [title],
                    "description": [description],
                    "type": [tasktype],
                    "subject": subjects,
                    "gwikicategory": [raippacategories["taskcategory"]]}
            if len(newflow) > 0:
                data["start"] = [addlink(newflow[0][0])]
            data = {taskpage: data}

            oldkeys = get_keys(request, taskpage)
            remove = {taskpage: oldkeys}

            backup[taskpage] = Page(request, taskpage).get_real_rev()
            result, msg = set_metas(request, remove, dict(), data)
            if not result:
                for page, rev in backup.iteritems():
                    revert(request, page, rev)
                #TODO: delete newpages
                return u'Failed to save the task (%s).' % taskpage

            #TODO: delete unused pages from reusable list
            return u'Thank you for your changes. Your attention to detail is appreciated.'

def delete(request, pagename):
    if pageexists(request, pagename):
        metas = get_metas(request, pagename, ["gwikicategory"])
        if raippacategories["taskcategory"] in metas["gwikicategory"]:
            linkedpage = request.graphdata.getpage(pagename)
            linking_in = linkedpage.get('in', {})
            linkinglist = linking_in.get("task", [])
            #TODO: historypages link here too 
            if linkinglist:
                return "Task is in use."

            taskflow = getflow(request, pagename)
            for task, question in taskflow:
                taskpage = PageEditor(request, task, do_editor_backup=0)
                taskpage.deletePage()

            page = PageEditor(request, pagename, do_editor_backup=0)
            page.deletePage()
            return "Success"
        else:
            return "Wrong category"
    else:
        return "Page doesn't exist!"

def _enter_page(request, pagename):
    request.http_headers()
    head = u'''
<script type="text/javascript" src="%s/raippajs/mootools-1.2-core-yc.js"></script>
<script type="text/javascript" src="%s/raippajs/mootools-1.2-more.js"></script>
''' % (request.cfg.url_prefix_static,request.cfg.url_prefix_static)

    request.theme.send_title(u'Teacher Tools', formatted=False, html_head=head)
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter

    request.write(request.page.formatter.startContent("content"))

def _exit_page(request, pagename):
    request.write(request.page.formatter.endContent())
    request.theme.send_footer(pagename)

def execute(pagename, request):
    #TODO: support for "Task/38534?action=EditTask" style edit call
    ruser = RaippaUser(request)
    if not ruser.isTeacher():
        action = {"action_name": action_name}
        message = u'You are not allowed to do %(action_name)s on this page.' % action
        Page(request, pagename).send_page(msg=message)

    if request.form.has_key('cancel'):
        message = u'Edit was cancelled.'
        Page(request, pagename).send_page(msg=message)

    elif request.form.has_key('save'):
        taskpage = request.form.get("task", [None]).pop()
        taskdata = {"title": request.form.get("title", [None])[0],
                    "description": request.form.get("description", [unicode()])[0].rstrip(),
                    "type": request.form.get('type', ["basic"])[0],
                    "subject": request.form.get("subject", list()),
                    "flowlist": request.form.get("flowlist", list())}

        recapdict = dict()
        for key in request.form:
            if key.endswith("_recap"):
                question = key.split("_")[0]
                recaptask = request.form.get(key, [None])[0]
                if recaptask:
                    recapdict[question] = recaptask

        taskdata["recap"] = recapdict

        message = save_task(request, taskdata, taskpage)
        Page(request, pagename).send_page(msg=message)

    elif request.form.has_key("delete") and request.form.has_key("task"):
        try:
            page = request.form["task"][0]
            msg = delete(request, page)
        except:
            msg = "Failed to delete the Task."
        if msg == "Success":
            url = u'%s/%s' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
        else:
            _enter_page(request, pagename)
            request.write(msg)
            _exit_page(request, pagename)
    else:
        if request.form.has_key("new"):
            taskpage = None
        else:
            taskpage = request.form.get("task", [None])[0]
            if not taskpage:
                taskpage = pagename

        _enter_page(request, pagename)
        taskform(request, taskpage)
        _exit_page(request, pagename)
