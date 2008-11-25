# -*- coding: utf-8 -*-"
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import get_metas
from graphingwiki.editing import set_metas
from graphingwiki.editing import getkeys
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

        flow = getflow(request, task)
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
  addOpts();
  $$('select[id^=type_]').setStyle('display' , 'none');
  var val = $($('typeSelect').value) ? $('typeSelect').value : 'type_None';
  
  $(val).setStyle('display','');
  
  $('typeSelect').addEvent('change',function(){
    var val = this.value;
    if($(val)){
      $$('select[id^=type_]').setStyle('display' , 'none');
      $(val).setStyle('display','');
      }
    });
  var links = $$('option').filter(function(el){
    return el.title.match("::") ? true : false;
    });
   //var tips = new Tips(links);
   
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
      
      div.grab(new Element('b', {
        'text' : el.title,
        'styles' : {
              'margin-right' : '50px',
              'float' :'left'
          }
        }));
      div.grab(new Element('input', {
        'type' : 'button',
        'value' : 'Edit',
        'styles' : {
            'float' : 'right'
          },
        'events' : {
            'click' : function(){
              saveTaskData(el);
            }
          }
        }));
    $('info').grab(div);
  }
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


function toQuestionEditor(question){
  var form = new Element('form', {
    'method' : 'post'
    });
  form.grab(new Element('input', {
    'type' : 'hidden',
    'name' : 'action',
    'value' : 'editQuestion'
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

function createPenaltySel(el, defVal){
  var opt = $(el);
  var sel = opt.getParent('select');
  var posx = sel.getCoordinates().width + sel.getCoordinates().left + 55;
  var posy = sel.getCoordinates().top + 15 *
  opt.getAllPrevious('option').length;
	var noPenalty = 'selected';
  if(defVal){
	noPenalty = '';
	}
  var form = $('taskForm');
  document.getElements('select[id$=_recap]').setStyle('display', 'none');
  var select = $(opt.value+'_recap');

  if(select != null){
	select.setStyles({
	  'display': '',
	  'top' : posy,
	  'left' : posx
	});
  }else{
	var select = new Element('select', {
	'id' : opt.value+'_recap',
	'name' : opt.value+'_recap',
	'size' : 1,
	'styles': {
		'position' : 'absolute',
		'display' : '',
		'top' : posy,
		'left' : posx
		},
	'events' : {
		'change' : function(){
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
            #TODO: report missing title
            desc = ti
        pagehtml += u'''
  select.grab(new Element('option', {
	  'value' : '%s',
	  'text' : '%s'
	}));
  if(defVal == '%s'){
	select.getLast('option').set('selected','selected');
	}\n''' % (ti, desc,ti)

    pagehtml += u'''
  select.inject(document.body);
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

function addOption(theSel, theText, theValue, recap)
{
	var newOpt = new Element('option', {
	  'text' : theText,
	  'title' : theText +'::',
	  'value' : theValue
});
    $(theSel).grab(newOpt);
	
	if(recap){
	  newOpt.setStyle('background-color', 'red');
	  createPenaltySel(newOpt, recap);
	}else{
	  createPenaltySel(newOpt, '');
	}
	  newOpt.setStyle('width', 'auto');
  document.getElements('select[id$=_recap]').setStyle('display', 'none');
	$(theSel).addEvent('keyup', function(event){
			  if(theSel.id == 'flist'){
				sel = $(theSel).getChildren('option').filter(function(el){
				  return el.selected == true
				  });
				  if(sel){
					createPenaltySel(sel[0]);
				  }
			  }
			});
$(theSel).addEvent('click', function(event){
			  if(theSel.id == 'flist'){
				sel = $(theSel).getChildren('option').filter(function(el){
				  return el.selected == true
				  });
				  if(sel){
					createPenaltySel(sel[0]);
				  }
			  }
			});
}

function deleteOption(theSel, theIndex)
{
    var selLength = theSel.length;
    if(selLength > 0)
    {
		var penSel = $(theSel.options[theIndex].value +'_recap');
		if(penSel != null){
			penSel.destroy();
		  }
        theSel.options[theIndex] = null;
    }
  document.getElements('select[id$=_recap]').setStyle('display', 'none');
}

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

function selectAllOptions(selStr)
{
    $(selStr).getChildren('option').each(function(el){
	  el.selected = true;
	  var sel = $(el.value +'_recap');
	  var val = sel != null ? sel.value : false;
	  if(val != ""){
		$('taskForm').grab(new Element('input', {
		  'type' : 'hidden',
		  'name' : el.value +'_recap',
		  'value' : val
		  }));
		}
	  });
}

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

select questions:<br>
<form method="POST" action="%s" onsubmit="saveTaskData();">
    <input type="hidden" name="action" value="editQuestion">
    <input type='submit' name='new' value='NewQuestion'>
</form>
<form id="taskForm" method="post" name="taskForm" action="">
<table border="0">
<tr><td colspan="4" id="info">
</td></tr>
\n''' % request.request_uri.split("?")[0]
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
                "start": [addlink(taskpoint)],
                "subject": subjects,
                "gwikicategory": [raippacategories["taskcategory"]]}

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
        oldflow = getflow(request, taskpage)
        oldquestions = list()
        for taskpoint, questionpage in oldflow:
            oldquestions.append(questionpage)

        #save just taskpage if flow haven't changed
        if oldquestions == flowlist or not recapdict:
            data = {"title": [title],
                    "description": [description],
                    "type": [tasktype],
                    "subject": subjects,
                    "gwikicategory": [raippacategories["taskcategory"]]}
            data = {taskpage: data}
            
            oldkeys = getkeys(request, taskpage)
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
                    oldkeys = getkeys(request, taskpoint)
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
                    "type": [type],
                    "subject": subjects,
                    "start": [addlink(newflow[0][1])],
                    "gwikicategory": [raippacategories["taskcategory"]]}
            data = {taskpage: data}

            oldkeys = getkeys(request, taskpage)
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
        taskpage = request.form.get("task", None).pop()
        taskdata = {"title": request.form.get("title", [None])[0],
                    "description": request.form.get("description", [unicode()])[0].rstrip(),
                    "type": request.form.get('type', [None])[0],
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
    elif request.form.has_key('edit') and request.form.has_key('task'):
        _enter_page(request, pagename)
        try:
            task = request.form["task"][0]
        except:
            request.write("Missing task.")
            return None
        taskform(request, task)
        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        taskform(request)
        _exit_page(request, pagename)
