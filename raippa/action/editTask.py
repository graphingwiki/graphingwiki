# -*- coding: utf-8 -*-"
action_name = 'editTask'

import random

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import getmetas, getvalues
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import GraphData, encode
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input

questioncategory = u'CategoryQuestion'
taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
statuscategory = u'CategoryStatus'
historycategory = u'CategoryHistory'

def randompage(request, type):
    pagename = "%s/%i" % (type, random.randint(10000,99999))
    page = Page(request, pagename)
    while page.exists():
        pagename = "%s/%i" % (type, random.randint(10000,99999))
        page = Page(request, pagename)

    return pagename

def addlink(pagename):
    return '[['+pagename+']]'

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
<script language="JavaScript" type="text/javascript">
<!--
var NS4 = (navigator.appName == "Netscape" && parseInt(navigator.appVersion) < 5);

function addOption(theSel, theText, theValue)
{
    var newOpt = new Option(theText, theValue);
    var selLength = theSel.length;
    theSel.options[selLength] = newOpt;
}

function deleteOption(theSel, theIndex)
{   
    var selLength = theSel.length;
    if(selLength > 0)
    {
        theSel.options[theIndex] = null;
    }
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
    
    if(NS4) history.go(0);
}

function selectAllOptions(selStr)
{
    var selObj = document.getElementById(selStr);
    for (var i=0; i<selObj.options.length; i++) 
    {
        selObj.options[i].selected = true;
    }
}

//-->
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
    request.globaldata.closedb()
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, questioncategory)
    globaldata.closedb()
    request.globaldata = GraphData(request)
    for page in pagelist:
        if page not in questions:
            try:
                metas = getmetas(request, request.globaldata, encode(page), ["question"])
                question = metas["question"][0][0]
                pagehtml += u'<option name="question" value="%s">%s\n' % (page, question)
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
<form method="POST" name="taskForm" onsubmit="selectAllOptions('flist');">
    <input type="hidden" name="action" value="%s">\n''' % action_name
    if task:
        pagehtml += u'<input type="hidden" name="task" value="%s">\n' % task
    pagehtml += '''
    <td>
        <select name="flowlist" id="flist" size="10" multiple="multiple">\n'''
    for page in questions:
        try:
            metas = getmetas(request, request.globaldata, encode(page), ["question"])
            question = metas["question"][0][0]
            pagehtml += u'<option name="question" value="%s">%s\n' % (page, question)
        except:
            pass
    pagehtml += '''
        </select>
    </td>
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

        request.globaldata.closedb()
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
        request.globaldata = GraphData(request)
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
                    taskpointpage = PageEditor(request, taskpoint, do_editor_backup=0)
                    if taskpointpage.exists():
                        taskpointpage.deletePage()

                    taskpointpage = request.globaldata.getpage(taskpoint)
                    linking_in = taskpointpage.get('in', {})
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

            request.globaldata.closedb()
            for index, question in enumerate(flowlist):
                try:
                    taskindex = questions.index(question)
                    newflow.append((question, taskpoints[taskindex]))
                except:
                    pointpage = randompage(request, taskpage)
                    page = PageEditor(request, pointpage)
                    page.saveText("<<Raippa>>", page.get_real_rev())
                    newflow.append((question, pointpage))
            request.globaldata = GraphData(request)

            #TODO: handle userstatus here
            #TODO: check overalvalue on basic tasks
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
                        pagelist = linking_in['task']
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
                request.globaldata.closedb()
                process_edit(request, order_meta_input(request, statuspage, {coursepoint: [addlink(nexttaskpoint)]}, "repl"))
                request.globaldata = GraphData(request)
                #request.write(coursepoint, taskpoint, nexttaskpoint, user, answerer, taskpoints, newflow)

            taskdata = {u'description':[description],
                        u'type':[type],
                        u'start':[addlink(newflow[0][1])]}
            request.globaldata.closedb()
            process_edit(request, order_meta_input(request, taskpage, taskdata, "repl"))

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
            request.globaldata = GraphData(request)
        else:
            taskdata = {u'description':[description],
                        u'type':[type]}
            request.globaldata.closedb()
            process_edit(request, order_meta_input(request, taskpage, taskdata, "repl"))
            request.globaldata = GraphData(request)

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
    
    request.theme.send_title(_('Teacher Tools'), formatted=False)
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
    request.globaldata.closedb()

def execute(pagename, request):
    request.globaldata = GraphData(request)
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
            request.globaldata.closedb()
    elif request.form.has_key('edit') and request.form.has_key('task'):
        _enter_page(request, pagename)
        task = encode(request.form["task"][0])
        taskform(request, task)
        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        taskform(request)
        _exit_page(request, pagename)
