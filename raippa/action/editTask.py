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

questioncategory = u'CategoryQuestion'
taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
statuscategory = u'CategoryStatus'
historycategory = u'CategoryHistory'

def taskform(request, task=None):
    if task:
        metas = getmetas(request, request.globaldata, task, [u'description', u'type'])
        description = metas[u'description'][0][0]
        type = metas[u'type'][0][0]
        questions, taskpoints = getflow(request, task)
    else:
        description = u''
        type = u'basic'
        questions = list()
        taskpoints = list()

    _ = request.getText
    pagehtml = '''
<script type="text/javascript">
function createPenaltySel(el, defVal){
  var opt = $(el);
	var noPenalty = 'selected';
  if(defVal){
	noPenalty = '';
	}
  var form = $('taskForm');
  document.getElements('select[id^=penalty_]').setStyle('display', 'none');
  var select = $('penalty_'+opt.value);

  if(select != null){
	select.setStyles({
	  'display': '',
	  'top' : opt.getPosition().y,
	  'left' : opt.getPosition().x + opt.getCoordinates().width + 65
	});
  }else{
	var select = new Element('select', {
	'id' : 'penalty_' + opt.value,
	'size' : 1,
	'styles': {
		'position' : 'absolute',
		'display' : '',
		'top' : opt.getPosition().y,
		'left' : opt.getPosition().x + opt.getCoordinates().width + 65
		},
	'events' : {
		'change' : function(){
		  if(this.value == ''){
			opt.setStyle('background-color', '');
			}else{
			opt.setStyle('background-color', 'red');
			  }
		  }
	  }
	});
  select.grab(new Element('option',{
	  'value' : '',
	  'text' : 'no penalty',
	  'selected': noPenalty
	}));\n'''
    globaldata, tasklist, metakeys, styles = metatable_parseargs(request, taskcategory)
    for ti in tasklist:
        try:
            data = getmetas(request, request.globaldata, encode(ti),["description"])
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
  select.inject($('flowtd'));
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

function addOption(theSel, theText, theValue, penalty)
{
	var newOpt = new Element('option', {
	  'text' : theText,
	  'value' : theValue,
	  'events' : {
		  'mousedown' : function(){
			  if(theSel.id == 'flist'){
				createPenaltySel(newOpt);
			  }
			}
		}
  });
	if(penalty){
	  newOpt.setStyle('background-color', 'red');
	  createPenaltySel(newOpt, penalty);
	  }
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

    var selLength = theSel.length;
    theSel.options[selLength] = newOpt;
}

function deleteOption(theSel, theIndex)
{
    var selLength = theSel.length;
    if(selLength > 0)
    {
		var penSel = $('penalty_'+theSel.options[theIndex].value);
		if(penSel != null){
			penSel.destroy();
		  }
        theSel.options[theIndex] = null;
    }
  document.getElements('select[id^=penalty_]').setStyle('display', 'none');
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
    var selObj = document.getElementById(selStr);
    for (var i=0; i<selObj.options.length; i++)
    {
        selObj.options[i].selected = true;
    }
}

</script>

select questions:<br>
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editQuestion">
    <input type='submit' name='new' value='NewQuestion'>
</form>
<table border="0">
<form>
    <tr>
    <td>
        <select size="10" name="questionList" multiple="multiple">\n''' % request.request_uri.split("?")[0]
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, questioncategory)
    for page in pagelist:
        if page not in questions:
            try:
                metas = getmetas(request, request.globaldata, encode(page), ["question"])
                question = metas["question"][0][0]
                pagehtml += u'<option name="question" value="%s">%s</option>\n' % (page, question)
            except:
                pass
    pagehtml += '''
        </select>
    </td>
    <td align="center" valign="middle">
        <input type="button" value="--&gt;"
         onclick="moveOptions(this.form.questionList, taskForm.flowlist);"><br>
        <input type="button" value="&lt;--"
         onclick="moveOptions(taskForm.flowlist, this.form.questionList);">
    </td>
</form>
<form id="taskForm" method="POST" name="taskForm" onsubmit="selectAllOptions('flist');">
    <input type="hidden" name="action" value="%s">\n''' % action_name
    if task:
        pagehtml += u'<input type="hidden" name="task" value="%s">\n' % task
    pagehtml += '''
    <td id="flowtd">
        <select name="flowlist" id="flist" size="10"
		multiple="multiple"></select><script type="text/javascript">\n'''
    for page in questions:
        try:
            metas = getmetas(request, request.globaldata, encode(page), ["question"])
            question = metas["question"][0][0]
            pagehtml +=u'''addOption(document.getElementById("flist"),"%s","%s");\n''' %(question,page)
        except:
            pass
    pagehtml += '''
        </script>
    </td><td>
	<input type="button" value="&uArr;" onclick="moveSel($('flist'), '-');"><br>
	<input type="button" value="&dArr;" onclick="moveSel($('flist'), '+');"></td>
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
</select><br>
description:<br>
<textarea name="description" rows="10" cols="40">%s</textarea><br>
''' % description
    pagehtml += '''
<input type="submit" name="save" value="Save">
</form>
'''
    request.write(u'%s' % pagehtml)

def writemeta(request, taskpage=None):
    description = request.form.get(u'description', [u''])[0]
    if not description:
        return "Missing task description."

    type = request.form.get('type', [u''])[0]
    if not type:
        return "Missing task type."

    flowlist = request.form.get("flowlist", [])
    if not flowlist:
        return "Missing question list."

    if not taskpage:
        taskpage = randompage(request, "Task")
        taskpoint = randompage(request, taskpage)

        page = PageEditor(request, taskpage)
        page.saveText("<<Raippa>>", page.get_real_rev())

        taskdata = {u'description':[description],
                    u'type':[type],
                    u'start':[addlink(taskpoint)]}

        input = order_meta_input(request, taskpage, taskdata, "add")
        process_edit(request, input, True, {taskpage:[taskcategory]})

        for index, questionpage in enumerate(flowlist):
            page = PageEditor(request, taskpoint)
            page.saveText("<<Raippa>>", page.get_real_rev())
            nexttaskpoint = randompage(request, taskpage)
            pointdata = {u'question':[addlink(questionpage)]}
            if index >= len(flowlist)-1:
                pointdata[u'next'] = [u'end']
            else:
                pointdata[u'next'] = [addlink(nexttaskpoint)]
            input = order_meta_input(request, taskpoint, pointdata, "add")
            process_edit(request, input, True, {taskpoint:[taskpointcategory]})
            taskpoint = nexttaskpoint
    else:
        questions, taskpoints = getflow(request, taskpage)
        if questions != flowlist:
            newflow = list()
            userstatus = list()
            copyoftaskpoints = taskpoints[:]
            copyoftaskpoints.reverse()
            for index, question in enumerate(reversed(questions)):
                if question not in flowlist:
                    taskpoint = copyoftaskpoints[index]

                    taskpointpage = request.globaldata.getpage(taskpoint)
                    linking_in = taskpointpage.get('in', {})
                    taskpointpage = PageEditor(request, taskpoint, do_editor_backup=0)
                    if taskpointpage.exists():
                        taskpointpage.deletePage()

                    for metakey, valuelist in linking_in.iteritems():
                        for value in valuelist:
                            if value.endswith("/status"):
                                try:
                                    meta = getmetas(request, request.globaldata, value, ["WikiCategory"])
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
                taskpointdata = {u'question':[question], u'next':[next]}
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

                        taskpointpage = request.globaldata.getpage(taskpoint)
                        linking_in = taskpointpage.get('in', {})
                        pagelist = linking_in.get('task', [])
                        for page in pagelist:
                            try:
                                meta = getmetas(request, request.globaldata, page, ["WikiCategory", "course", "user"])
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

            taskdata = {u'description':[description],
                        u'type':[type],
                        u'start':[addlink(newflow[0][1])]}
            process_edit(request, order_meta_input(request, taskpage, taskdata, "repl"))
        else:
            taskdata = {u'description':[description],
                        u'type':[type]}
            process_edit(request, order_meta_input(request, taskpage, taskdata, "repl"))

    return None

def getflow(request, task):
    meta = getmetas(request, request.globaldata, task, ["start"])
    taskpoint = encode(meta["start"][0][0])
    questions = list()
    taskpoints = list()
                        
    while taskpoint != "end":
        meta = getmetas(request, request.globaldata, taskpoint, ["question", "next"])
        questionpage = meta["question"][0][0]
        questions.append(questionpage)
        taskpoints.append(taskpoint)
        taskpoint = encode(meta["next"][0][0])
    return questions, taskpoints

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
    request.globaldata = getgraphdata(request)
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
            url = u'%s/%s?action=TeacherTools' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
    elif request.form.has_key('edit') and request.form.has_key('task'):
        _enter_page(request, pagename)
        task = encode(request.form["task"][0])
        taskform(request, task)
        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        taskform(request)
        _exit_page(request, pagename)
