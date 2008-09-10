# -*- coding: utf-8 -*-"
action_name = 'editTask'

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import getmetas, getvalues
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import GraphData, encode
from graphingwiki.patterns import getgraphdata
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input

from raippa import addlink, randompage
from raippa import FlowPage

questioncategory = u'CategoryQuestion'
taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
statuscategory = u'CategoryStatus'
historycategory = u'CategoryHistory'

def taskform(request, task=None):
    if task:
        title = unicode()
        description = unicode()
        type = u'basic'
        subjects = list()
        metas = getmetas(request, request.graphdata, task, ["title","description", "type", "subject"])
        if metas["title"]:
            title = metas["title"][0][0]
        if metas["description"]:
            description = metas["description"][0][0]
        if metas["type"]:
            type = metas["type"][0][0]
        for subject, type in metas["subject"]:
            subjects.append(subject)
        questions, taskpoints = getflow(request, task)
        recapdict = dict()
        for taskpoint in taskpoints:
            metas = getmetas(request, request.graphdata, taskpoint, ["question","recap"])
            if metas["recap"] and metas["question"]:
                recapdict[metas["question"][0][0]] = metas["recap"][0][0]
    else:
        title = unicode()
        subjects = list()
        description = unicode()
        type = u'basic'
        questions = list()
        taskpoints = list()
        recapdict = dict()

    _ = request.getText
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
  var tips = new Tips(links);
  });

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
    globaldata, tasklist, metakeys, styles = metatable_parseargs(request, taskcategory)
    for ti in tasklist:
        try:
            data = getmetas(request, request.graphdata, encode(ti),["title","description"])
            if data["title"]:
                desc = data["title"][0][0]
            else:
                desc = data["description"][0][0]
            pagehtml += u'''
  select.grab(new Element('option', {
	  'value' : '%s',
	  'text' : '%s'
	}));
  if(defVal == '%s'){
	select.getLast('option').set('selected','selected');
	}
  \n''' % (ti, desc,ti)
        except:
            pass
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

</script>

select questions:<br>
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editQuestion">
    <input type='submit' name='new' value='NewQuestion'>
</form>
<table border="0">
<form id="taskForm" method="POST" name="taskForm" onsubmit="selectAllOptions('flist');">\n''' % request.request_uri.split("?")[0]
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, questioncategory)
    typedict = {None:list()}
    for page in pagelist:
        if page not in questions:
            try:
                metas = getmetas(request, request.graphdata, encode(page), ["type", "question"])
                question = metas["question"][0][0]
                if metas["type"]:
                    for type, metatype in metas["type"]:
                        if not typedict.has_key(type):
                            typedict[type] = list()
                        typedict[type].append((page, question))
                else:
                    typedict[None].append((page, question))
            except:
                pass
    #typelist
    pagehtml += u'question type: <select id="typeSelect" name="question_type">\n'
    for type in typedict:
        pagehtml += '<option value="type_%s">%s\n' % (type, type)
    pagehtml += u'</select><tr><td id="qlist_td">'

    #questionlists
    for type, questionlist in typedict.iteritems():
        pagehtml += u'''<select size="10" style="width:200px;" id="type_%s" name="questionList"
        multiple="multiple">\n''' % type
        for questionpagename, questiontext in questionlist:
            pagehtml += u'<option name="question" title="%s:: " value="%s">%s</option>\n' % (questiontext, questionpagename, questiontext)
        pagehtml += u'</select>\n'
    pagehtml += u'''
    </td>
    <td align="center" valign="middle">
        <input type="button" value="--&gt;"
         onclick="moveOptions($($('typeSelect').value), taskForm.flowlist);"><br>
        <input type="button" value="&lt;--"
         onclick="moveOptions(taskForm.flowlist, $($('typeSelect').value));">
    </td>
    <input type="hidden" name="action" value="%s">\n''' % action_name
    if task:
        pagehtml += u'<input type="hidden" name="task" value="%s">\n' % task
    pagehtml += '''
    <td id="flowtd">
        <select name="flowlist" style="width:200px;" id="flist" size="10"
		multiple="multiple"></select><script type="text/javascript">
		function addOpts(){
		\n'''
    for page in questions:
        try:
            metas = getmetas(request, request.graphdata, encode(page), ["question"])
            question = metas["question"][0][0]
            pagehtml +=u'addOption(document.getElementById("flist"),"%s","%s","%s");\n' %(question,page,recapdict.get(page,""))
        except:
            pass
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
    globaldata, tasklist, metakeys, styles = metatable_parseargs(request, taskcategory)
    tasktypes = list()
    for task_in_list in tasklist:
        metas = getmetas(request, request.graphdata, task_in_list, ["subject"])
        for type, metatype in metas["subject"]:
            tasktypes.append(type)
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
<input type="text" size="40" name="title" value="%s">
<br>description:
<br>
<textarea name="description" rows="10" cols="40">%s</textarea><br>
''' % (title, description)
    pagehtml += '''
<input type="submit" name="save" value="Save">
<input type="submit" name="cancel" value="Cancel">
</form>
'''
    request.write(u'%s' % pagehtml)

def writemeta(request, taskpage=None):
    title = unicode()
    description = unicode() 
    subjects = list()
    type = unicode()
    flowlist = list() 
    recapdict = dict()

    for key in request.form:
        if key == "title":
            title = request.form.get(u'title', [u''])[0]
        elif key == "description":
            description = request.form.get(u'description', [u''])[0]
        elif key == "type":
            type = request.form.get('type', [u''])[0]
        elif key == "flowlist":
            flowlist = request.form.get("flowlist", [])
        elif key == "subject":
            subjects = request.form.get("subject", [])
        elif key.endswith("_recap"):
            question = key.split("_")[0]
            recaptask = request.form.get(key, [None])[0]
            if recaptask:
                recapdict[question] = recaptask

    if not title:
        return "Missing task title."
    if not description:
        return "Missing task description."
    if not type:
        return "Missing task type."
    if not flowlist:
        return "Missing question list."

    if not taskpage:
        taskpage = randompage(request, "Task")
        taskpoint = randompage(request, taskpage)

        page = PageEditor(request, taskpage)
        page.saveText("<<Raippa>>", page.get_real_rev())

        taskdata = {"title":[title],
                    "description":[description],
                    "type":[type],
                    "start":[addlink(taskpoint)],
                    "subject":subjects}

        input = order_meta_input(request, taskpage, taskdata, "add")
        process_edit(request, input, True, {taskpage:[taskcategory]})

        for index, questionpage in enumerate(flowlist):
            page = PageEditor(request, taskpoint)
            page.saveText("<<Raippa>>", page.get_real_rev())
            nexttaskpoint = randompage(request, taskpage)
            pointdata = {"question":[addlink(questionpage)]}
            recap = recapdict.get(questionpage, None)
            if recap:
                pointdata["recap"] = addlink(recap)
            if index >= len(flowlist)-1:
                pointdata["next"] = ["end"]
            else:
                pointdata["next"] = [addlink(nexttaskpoint)]
            input = order_meta_input(request, taskpoint, pointdata, "add")
            process_edit(request, input, True, {taskpoint:[taskpointcategory]})
            taskpoint = nexttaskpoint
    else:
        questions, taskpoints = getflow(request, taskpage)
        if questions != flowlist or recapdict:
            newflow = list()
            userstatus = list()
            copyoftaskpoints = taskpoints[:]
            copyoftaskpoints.reverse()
            for index, question in enumerate(reversed(questions)):
                if question not in flowlist:
                    taskpoint = copyoftaskpoints[index]

                    taskpointpage = request.graphdata.getpage(taskpoint)
                    linking_in = taskpointpage.get('in', {})
                    taskpointpage = PageEditor(request, taskpoint, do_editor_backup=0)
                    if taskpointpage.exists():
                        taskpointpage.deletePage()

                    for metakey, valuelist in linking_in.iteritems():
                        for value in valuelist:
                            if value.endswith("/status"):
                                try:
                                    meta = getmetas(request, request.graphdata, value, ["WikiCategory"])
                                    if meta["WikiCategory"][0][0] == statuscategory:
                                        user = value.split("/")[0]
                                        userstatus.append([user, metakey, index]) 
                                except:
                                   pass

            for index, question in enumerate(flowlist):
                try:
                    taskindex = questions.index(question)
                    newflow.append((question, taskpoints[taskindex]))
                except:
                    pointpage = randompage(request, taskpage)
                    page = PageEditor(request, pointpage)
                    page.saveText("<<Raippa>>", page.get_real_rev())
                    newflow.append((question, pointpage))

            for index, questiontuple in enumerate(newflow):
                question = addlink(questiontuple[0])
                taskpoint = questiontuple[1]
                if index >= len(newflow)-1:
                    next = "end"
                else:
                    next = addlink(newflow[index+1][1])
                taskpointdata = {"question":[question],
                                 "next":[next]}
                recap = recapdict.get(questiontuple[0], None)
                if recap:
                    taskpointdata["recap"] = [addlink(recap)]
                input = order_meta_input(request, taskpoint, taskpointdata, "repl")
                process_edit(request, input, True, {taskpoint:[taskpointcategory]})


            for status in userstatus:
                user = status[0]
                coursepoint = status[1]

                if status[2] >= len(newflow):
                    startindex = len(newflow)-1
                else:
                    startindex = status[2]

                reversednewflow = newflow[:]
                reversednewflow.reverse()
                nexttaskpoint = str()
                for index, point in enumerate(reversednewflow):
                    if index > startindex:
                        taskpoint = point[1]

                        taskpointpage = request.graphdata.getpage(taskpoint)
                        linking_in = taskpointpage.get('in', {})
                        pagelist = linking_in.get('task', [])
                        for page in pagelist:
                            try:
                                meta = getmetas(request, request.graphdata, page, ["WikiCategory", "course", "user"])
                                category = meta["WikiCategory"][0][0]
                                answerer = meta["user"][0][0]
                                course = meta["course"][0][0]
                            except:
                                category = str()
                                answerer = str()
                                course = str()

                            if category == historycategory and answerer == user and coursepoint.startswith(course):
                                nexttaskpoint = reversednewflow[index-1][1]
                                break
                        if nexttaskpoint:
                            break
                if not nexttaskpoint:
                    nexttaskpoint = newflow[0][1]

                statuspage = user + "/status"
                process_edit(request, order_meta_input(request, statuspage, {coursepoint: [addlink(nexttaskpoint)]}, "repl"))

            taskdata = {u'title':[title],
                        u'description':[description],
                        u'type':[type],
                        u'subject': subjects,
                        u'start':[addlink(newflow[0][1])]}
            process_edit(request, order_meta_input(request, taskpage, taskdata, "repl"))
        else:
            taskdata = {u'title':[title],
                        u'description':[description],
                        u'type':[type],
                        u'subject': subjects}
            process_edit(request, order_meta_input(request, taskpage, taskdata, "repl"))

    return None

def getflow(request, task):
    meta = getmetas(request, request.graphdata, task, ["start"])
    taskpoint = encode(meta["start"][0][0])
    questions = list()
    taskpoints = list()
                        
    while taskpoint != "end":
        meta = getmetas(request, request.graphdata, taskpoint, ["question", "next"])
        questionpage = meta["question"][0][0]
        questions.append(questionpage)
        taskpoints.append(taskpoint)
        taskpoint = encode(meta["next"][0][0])
    return questions, taskpoints

def delete(request, pagename):
    pagename = encode(pagename)
    page = PageEditor(request, pagename, do_editor_backup=0)
    if page.exists():
        categories = list()
        metas = getmetas(request, request.graphdata, pagename, ["WikiCategory"])
        for category, type in metas["WikiCategory"]:
            if category == taskcategory:
                linkedpage = request.graphdata.getpage(pagename)
                linking_in = linkedpage.get('in', {})
                linkinglist = linking_in.get("task", [])
                if linkinglist:
                    return "Task is in use."
                taskpage = FlowPage(request, pagename)
                taskflow = taskpage.getflow()
                for task, question in taskflow:
                    taskpage = PageEditor(request, task, do_editor_backup=0)
                    #print "delete", taskpage.page_name
                    taskpage.deletePage()
                break
        #print "delete", page.page_name
        page.deletePage()
        return "Success"
    else:
        return "Page doesn't exist!"

def _enter_page(request, pagename):
    request.http_headers()
    _ = request.getText
    
    request.theme.send_title(_('Teacher Tools'), formatted=False,
    html_head='''<script type="text/javascript" src="%s/common/js/mootools-1.2-core-yc.js"></script>
   <script type="text/javascript" src="%s/common/js/mootools-1.2-more.js"></script> ''' %
    (request.cfg.url_prefix_static,request.cfg.url_prefix_static))
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
    if request.form.has_key('save'):
        if request.form.has_key('task'):
            task = encode(request.form["task"][0])
            msg = writemeta(request, task)
        else:
            msg = writemeta(request)

        if msg:
            _enter_page(request, pagename)
            request.write(msg)
            _exit_page(request, pagename)
        else:
            url = u'%s/%s' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
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
            task = encode(request.form["task"][0])
        except:
            request.write("Missing task.")
            return None
        taskform(request, task)
        _exit_page(request, pagename)
    elif request.form.has_key('cancel'):
        url = u'%s/%s' % (request.getBaseURL(), pagename)
        request.http_redirect(url)

    else:
        _enter_page(request, pagename)
        taskform(request)
        _exit_page(request, pagename)
