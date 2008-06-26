# -*- coding: utf-8 -*-"
action_name = 'editCourse'

import random

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import getmetas
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import GraphData, encode
from graphingwiki.patterns import getgraphdata
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input

taskcategory = u'CategoryTask'
coursecategory = u'CategoryCourse'
coursepointcategory = u'CategoryCoursepoint'
statuscategory = 'CategoryStatus'
historycategory = 'CategoryHistory'

def randompage(request, type):
    pagename = "%s/%i" % (type, random.randint(10000,99999))
    page = Page(request, pagename)
    while page.exists():
        pagename = "%s/%i" % (type, random.randint(10000,99999))
        page = Page(request, pagename)

    return pagename

def addlink(pagename):
    return '[['+pagename+']]'

def taskform(request, course=None):
    if course:
        metas = getmetas(request, request.globaldata, course, [u'id', u'name', u'description'])
        id = metas[u'id'][0][0]
        name = metas[u'name'][0][0]
        try:
            coursedescription = metas[u'description'][0][0]
        except:
            coursedescription = u''
        tasks, coursepoints = getflow(request, course)
    else:
        id = u''
        name = u''
        coursedescription = u''
        tasks = list()
        coursepoints = list()

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

select tasks:
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editTask">
    <input type='submit' name='new' value='NewTask'>
</form>
<table border="0">
<form>
    <tr>
    <td>
        <select size="10" name="taskList" multiple="multiple">\n''' % request.request_uri.split("?")[0]
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, taskcategory)
    for page in pagelist:
        if page not in tasks:
            try:
                metas = getmetas(request, request.globaldata, encode(page), ["description"])
                description = metas["description"][0][0]
                pagehtml += u'<option name="description" value="%s">%s\n' % (page, description)
            except:
                pass
    pagehtml += '''
        </select>
    </td>
    <td align="center" valign="middle">
        <input type="button" value="--&gt;"
         onclick="moveOptions(this.form.taskList, courseForm.flowlist);"><br>
        <input type="button" value="&lt;--"
         onclick="moveOptions(courseForm.flowlist, this.form.taskList);">
    </td>
</form>
<form method="POST" name="courseForm" onsubmit="selectAllOptions('flist');">
    <input type="hidden" name="action" value="%s">\n''' % action_name
    if course:
        pagehtml += u'<input type="hidden" name="course" value="%s">\n' % course
    pagehtml += '''
    <td>
        <select name="flowlist" id="flist" size="10" multiple="multiple">\n'''
    for page in tasks:
        try:
            metas = getmetas(request, request.globaldata, encode(page), ["description"])
            description = metas["description"][0][0]
            pagehtml += u'<option name="description" value="%s">%s\n' % (page, description)
        except:
            pass
    pagehtml += '''
        </select>
    </td>
    </tr>
</table>\n'''
    if id:
        pagehtml += '<input type="hidden" name="courseid" value="%s">' % id 
    else:
        pagehtml += 'id: <input type="text" name="courseid"><br>'
    pagehtml += '''
name: <input type="text" name="coursename" value="%s"><br> 
description:<br> 
<textarea name="coursedescription" rows="10" cols="40">%s</textarea><br>
<input type="submit" name="save" value="Save">
</form>
''' % (name, coursedescription)

    request.write(u'%s' % pagehtml)

def writemeta(request, coursepage=None):
    courseid = request.form.get("courseid", [u''])[0]
    if not courseid:
        return "Missing course id."

    coursename = request.form.get("coursename", [u''])[0]
    if not coursename:
        return "Missing course name."

    flowlist = request.form.get("flowlist", [])
    if not flowlist:
        return "Missing task list."

    coursedescription = request.form.get("coursedescription", [u''])[0]

    if not coursepage:
        coursepage = u'Course/' + courseid
        page = Page(request, coursepage)
        if page.exists():
            return "Course already exists."
        coursepoint = randompage(request, coursepage)

        page = PageEditor(request, coursepage)
        page.saveText("<<Raippa>>", page.get_real_rev())

        coursedata = {u'id':[courseid],
                      u'author':[addlink(request.user.name)],
                      u'name':[coursename],
                      u'description':[coursedescription],
                      u'start':[addlink(coursepoint)]}

        input = order_meta_input(request, coursepage, coursedata, "add")
        process_edit(request, input, True, {coursepage:[coursecategory]})

        for index, taskpage in enumerate(flowlist):
            nextcoursepoint = randompage(request, coursepage)
            pointdata = {u'task':[addlink(taskpage)]}
            if index >= len(flowlist)-1:
                pointdata[u'next'] = [u'end']
            else:
                pointdata[u'next'] = [addlink(nextcoursepoint)]
            input = order_meta_input(request, coursepoint, pointdata, "add")
            process_edit(request, input, True, {coursepoint:[coursepointcategory]})
            coursepoint = nextcoursepoint
    else:
        tasks, coursepoints = getflow(request, coursepage)
        if tasks != flowlist:
            newflow = list()
            userstatus = list()

            copyofcoursepoints = coursepoints[:]
            copyofcoursepoints.reverse()
            for index, task in enumerate(reversed(tasks)):
                if task not in flowlist:
                    coursepoint = copyofcoursepoints[index]
                    coursepointpage = request.globaldata.getpage(coursepoint)
                    linking_in = coursepointpage.get('in', {})
                    valuelist = linking_in.get(coursepage,[])
                    coursepointpage = PageEditor(request, coursepoint, do_editor_backup=0)
                    if coursepointpage.exists():
                        coursepointpage.deletePage()

                    for value in valuelist:
                        if value.endswith("/status"):
                            try:
                                meta = getmetas(request, request.globaldata, value, ["WikiCategory", coursepoint])
                                if meta["WikiCategory"][0][0] == statuscategory:
                                    user = value.split("/")[0]
                                    task = meta[coursepoint][0][0]
                                    userstatus.append([user, task, index])
                                    process_edit(request, order_meta_input(request, value, {coursepoint: [" "]}, "repl"))
                            except:
                                pass

            for index, task in enumerate(flowlist):
                try:
                    courseindex = tasks.index(task)
                    newflow.append((task, coursepoints[courseindex]))
                except:
                    pointpage = randompage(request, coursepage)
                    newflow.append((task, pointpage))

            for index, tasktuple in enumerate(newflow):
                task = addlink(tasktuple[0])
                coursepoint = tasktuple[1]
                if index >= len(newflow)-1:
                    next = "end"
                else:
                    next = addlink(newflow[index+1][1])
                coursepointdata = {u'task':[task], u'next':[next]}
                input = order_meta_input(request, coursepoint, coursepointdata, "repl")
                process_edit(request, input, True, {coursepoint:[coursepointcategory]})

            #handle userstatus here
            for status in userstatus:
                user = status[0]
                task = status[1]
                if status[2] >= len(newflow):
                    startindex = len(newflow)-1
                else:
                    startindex = status[2]

                reversednewflow = newflow[:]
                reversednewflow.reverse()
                nextcoursepoint = str()
                for index, point in enumerate(reversednewflow):
                    if index > startindex or startindex == 0:
                        coursepoint = encode(point[1])
                        meta = getmetas(request, request.globaldata, coursepoint, ["task"])
                        taskpoint = meta["task"][0][0]
                        questions, taskpoints = getflow(request, taskpoint)
                        lasttaskpoint = taskpoints[-1]
                        taskpointpage = request.globaldata.getpage(lasttaskpoint)
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

                            if category == historycategory and answerer == user and course == coursepage:
                                nextcoursepoint = reversednewflow[index-1][1]
                                break
                        if nextcoursepoint:
                            break
                if not nextcoursepoint:
                    nextcoursepoint = newflow[0][1]

                statuspage = user + "/status"
                process_edit(request, order_meta_input(request, statuspage, {coursepage: [addlink(coursepoint)], coursepoint: [addlink(taskpoint)]}, "repl"))

            coursedata = {u'description':[coursedescription],
                          u'name':[coursename],
                          u'start':[addlink(newflow[0][1])]}
            process_edit(request, order_meta_input(request, coursepage, coursedata, "repl"))
        else:
            coursedata = {u'name':[coursename],
                          u'description':[coursedescription]}
            process_edit(request, order_meta_input(request, coursepage, coursedata, "repl"))

    return None 

def getflow(request, page):
    meta = getmetas(request, request.globaldata, encode(page), ["start", "WikiCategory"])
    flowpoint = encode(meta["start"][0][0])
    category = encode(meta["WikiCategory"][0][0])
    if category == coursecategory:
        keytype = "task"
    else:
        keytype = "question"
    pointpages = list()
    flowpoints = list()
    
    while flowpoint != "end":
        meta = getmetas(request, request.globaldata, flowpoint, [keytype, "next"])
        pointpage = meta[keytype][0][0]
        pointpages.append(pointpage)
        flowpoints.append(flowpoint)
        flowpoint = encode(meta["next"][0][0])
    return pointpages, flowpoints

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

def execute(pagename, request):
    request.globaldata = getgraphdata(request)
    if request.form.has_key('save'):
        if request.form.has_key('course'):
            course = encode(request.form["course"][0])
            msg = writemeta(request, course)
        else:
            msg = writemeta(request)

        if msg:
            _enter_page(request, pagename)
            request.write(msg)
            _exit_page(request, pagename)
        else:
            url = u'%s/%s?action=TeacherTools' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
    elif request.form.has_key('edit') and request.form.has_key('course'):
        _enter_page(request, pagename)
        course = encode(request.form["course"][0])
        taskform(request, course)
        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        taskform(request)
        _exit_page(request, pagename)
