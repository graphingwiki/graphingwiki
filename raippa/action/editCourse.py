# -*- coding: utf-8 -*-"
action_name = 'editCourse'

from MoinMoin.Page import Page
from MoinMoin import wikiutil
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import getmetas
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import encode
from graphingwiki.patterns import getgraphdata
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input

from raippa import addlink, randompage
from raippa import FlowPage

taskcategory = u'CategoryTask'
coursecategory = u'CategoryCourse'
coursepointcategory = u'CategoryCoursepoint'
statuscategory = u'CategoryStatus'
historycategory = u'CategoryHistory'



def courseform(request, course=None):
    if course:
        metas = getmetas(request, request.graphdata, course, ["id", "name", "description", "option"])
        id = metas[u'id'][0][0]
        name = metas[u'name'][0][0]
        try:
            coursedescription = metas[u'description'][0][0]
        except:
            coursedescription = u''
        options = list()
        for option, type in metas["option"]:
            options.append(option)
        coursepage = FlowPage(request, course)
        flow = coursepage.getflow() 
        tasks = dict()
        for cp in flow:
            if cp != "start":
                metas = getmetas(request, request.graphdata, encode(cp), ["task"])
                if metas["task"]:
                    task = metas["task"][0][0]
                    tasks[cp] = task
    else:
        id = u''
        name = u''
        coursedescription = u''
        options = list()
        flow = dict()
        tasks = dict()
    pagehtml = '''
<script type="text/javascript"
src="%s/common/js/mootools-1.2-core-yc.js"></script>
<script type="text/javascript"
src="%s/common/js/mootools-1.2-more.js"></script>
<script type="text/javascript"
src="%s/common/js/moocanvas.js"></script>
<script type="text/javascript"
src="%s/common/js/calendar.js"></script>
<script type="text/javascript"
src="%s/common/js/dragui.js"></script>\n''' % (request.cfg.url_prefix_static,
request.cfg.url_prefix_static, request.cfg.url_prefix_static,request.cfg.url_prefix_static,request.cfg.url_prefix_static)
    pagehtml += u'''
select tasks:
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editTask">
    <input type='submit' name='new' value='NewTask'>
</form><br>
<div style="width:200px;height:250px;overflow:scroll;">\n''' % request.request_uri.split("?")[0]
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, taskcategory)
    for page in pagelist:
        try:
            metas = getmetas(request, request.graphdata, encode(page), ["title","description"])
            if metas["title"]:
                description = metas["title"][0][0]
            else:
                description = metas["description"][0][0]
            pagehtml += u'''
    <div class="dragItem"><input type="hidden" name="%s" value="%s">%s</div>\n''' % (description, page.replace('"', '&quot;'), description.replace('"', '&quot;'))
        except:
            pass
    pagehtml += u'''
</div>
<div id="start">Start by dragging here!<br></div>
<form method="post" id="submitform" name="courseForm">
<input type="hidden" name="action" value="editCourse">\n'''
    if course:
        pagehtml += u'<input type="hidden" name="course" value="%s">\n' % course.replace('"', '&quot;')
    pagehtml += u'''
    <script type="text/javascript">
	function loadData(){\n'''
    donelist = list()
    def addNode(point):
        html = unicode()
        if point != "end":
            nextlist = flow.get(point, [])
            for next in nextlist:
                if next != "end":
                    metas = getmetas(request, request.graphdata, encode(tasks[next]), ["title","description"])
                    if metas["title"]:
                        description = metas["title"][0][0]
                    elif metas["description"]:
                        description = metas["description"][0][0]
                    else:
                        description = tasks[next]
                    metas = getmetas(request, request.graphdata, encode(next), ["deadline", "prerequisite", "split"])
                    if metas["split"]:
                        split = metas["split"][0][0]
                    else:
                        split = u'select'

                    if metas["prerequisite"]:
                        prerequisites = u',"'
                        temp = list()
                        for task, type in metas["prerequisite"]:
                            temp.append(task)
                        prerequisites += ",".join(temp)
                        prerequisites += u'"'
                    else:
                        prerequisites = u',""' 

                    deadline = unicode()
                    if metas.has_key("deadline"):
                        for deadline, type in metas["deadline"]:
                            break

                    html += u'newBox("%s","%s","%s","%s"%s,"%s");\n' % (tasks[point].replace('"', '&quot;'), tasks[next], description.replace('"', '&quot;'), split, prerequisites, deadline)
                    #html += u'newBox("%s","%s","%s");\n' % (task, tasks[next], description)
                    donelist.append(point)
                    if next not in donelist:
                        html += addNode(next)
        return html

    startlist = flow.get("start", None)
    if startlist:
        for point in startlist:
            metas = getmetas(request, request.graphdata, encode(tasks[point]), ["title", "description"])
            if metas["title"]:
                description = metas["title"][0][0]
            elif metas["description"]:
                description = metas["description"][0][0]
            else:
                description = tasks[next]
            metas = getmetas(request, request.graphdata, encode(point), ["prerequisite", "split", "deadline"])
            if metas["split"]:
                split = metas["split"][0][0]
            else:
                split = u'select'

            if metas["prerequisite"]:
                prerequisites = u',"'
                temp = list()
                for task, type in metas["prerequisite"]:
                    temp.append(task)
                prerequisites += ",".join(temp)
                prerequisites += u'"'
            else:
                prerequisites = u',""'

            deadline = unicode()
            if metas.has_key("deadline"):
                for deadline, type in metas["deadline"]:
                    break

            pagehtml += u'newBox("start","%s","%s","%s"%s,"%s");\n' % (tasks[point], description.replace('"', '&quot;'), split, prerequisites, deadline)
            #pagehtml += u'newBox("start","%s","%s");\n' % (task, description)
            pagehtml += addNode(point)

    pagehtml += '''
	}//loadData
    </script>\n'''
    if id:
        #pagehtml += '<input id="courseid" type="hidden" name="courseid" value="%s">' % id 
        pagehtml += 'id: <input id="courseid" type="text" name="courseid" value="%s"><br>' % id
    else:
        pagehtml += 'id: <input id="courseid" type="text" name="courseid"><br>'
    if "timetrack" in options:
        timetrack = 'checked'
    else:
        timetrack = ''
    pagehtml += '''
name: <input type="text" id="coursename" name="coursename" value="%s"><br> 
timetrack: <input type="checkbox" name="option" value="timetrack" %s><br>
description:<br> 
<textarea name="coursedescription" rows="10" cols="40">%s</textarea><br>
<input type="submit" name="save" value="Save" onclick="return submitTree(this);">
<input type="submit" name="cancel" value="Cancel" onclick="return submitTree(this);">
</form>
''' % (name, timetrack, coursedescription)

    request.write(u'%s' % pagehtml)

def editcourse(request, coursepage=None):
    courseid = unicode()
    coursename = unicode()
    coursedescription = unicode()
    options = list()

    nodedict = dict()
    taskdict = dict()
    prerequisites = dict()
    splittypes = dict()
 
    for key in request.form:
        if key == "courseid":
            courseid = request.form.get("courseid", [None])[0]
        elif key == "coursename":
            coursename = request.form.get("coursename", [None])[0]
        elif key == "coursedescription":
            coursedescription = request.form.get("coursedescription", [u''])[0]
        elif key == "option":
            for key in request.form.get("option", []):
                options.append(key)
        elif key != "save" and key != "action":
            if key.endswith("_next"):
                values = request.form.get(key, [u''])[0]
                key = key.split("_")[0]
                if not nodedict.get(key, None):
                    nodedict[key] = list()
                nodedict[key].extend(values.split(","))
            elif key.endswith("_value"):
                if not taskdict.has_key(key.split("_")[0]):
                    taskdict[key.split("_")[0]] = [unicode(), unicode()]
                taskdict[key.split("_")[0]][0] = request.form.get(key, [u''])[0]
            elif key.endswith("_require"):
                values = request.form.get(key, [u''])[0].split(",")
                if values:
                    prerequisites[key.split("_")[0]] = values
            elif key.endswith("_type"):
                splittypes[key.split("_")[0]] = [request.form.get(key, u'')[0]]
            elif key.endswith("_deadline"):
                if not taskdict.has_key(key.split("_")[0]):
                    taskdict[key.split("_")[0]] = [unicode(), unicode()]
                taskdict[key.split("_")[0]][1] = request.form.get(key, [u''])[0]

    if not courseid:
        return "Missing course id."
    if not coursename:
        return "Missing course name."
    if not taskdict:
        return "Missing task list."

    if not coursepage:
        coursepage = u'Course/' + courseid
        page = Page(request, coursepage)
        if page.exists():
            return "Course already exists."

        coursepointdict = dict()
        for number, taskdata in taskdict.iteritems():
            taskpage = taskdata[0]
            deadline = taskdata[1]
            coursepoint = coursepointdict.get(number, None)
            if not coursepoint:
                coursepoint = randompage(request, coursepage)
                coursepointdict[number] = coursepoint
            pointdata = {u'task':[addlink(taskpage)]}
            nextlist = nodedict.get(number, [u'end'])
            for next in nextlist:
                if next != u'end':
                    nextcp = coursepointdict.get(next, None)
                    if not nextcp:
                        nextcp = randompage(request, coursepage)
                        coursepointdict[next] = nextcp
                else:
                    nextcp = next
                if not pointdata.get(u'next', None):
                    pointdata[u'next'] = [addlink(nextcp)]
                else:
                    pointdata[u'next'].append(addlink(nextcp))

            pointdata[u'prerequisite'] = prerequisites.get(number, [])
            pointdata[u'split'] = splittypes.get(number, [u''])
            pointdata[u'deadline'] = [deadline]
            input = order_meta_input(request, coursepoint, pointdata, "add")
            process_edit(request, input, True, {coursepoint:[coursepointcategory]})             

        page = PageEditor(request, coursepage)
        page.saveText("<<Raippa>>", page.get_real_rev())

        coursedata = {u'id':[courseid],
                      u'author':[addlink(request.user.name)],
                      u'name':[coursename],
                      u'description':[coursedescription],
                      u'start':[],
                      u'option':options}
        startlist = nodedict["start"]
        for node in startlist:
            cp = coursepointdict[node]
            coursedata[u'start'].append(addlink(cp))

        coursedata[u'split'] = splittypes.get("start", [u''])
        input = order_meta_input(request, coursepage, coursedata, "add")
        process_edit(request, input, True, {coursepage:[coursecategory]})
    else:
        course = FlowPage(request, coursepage)
        oldflow = course.getflow()
        oldtasks = dict()
        for cp in oldflow:
            if cp != "start":
                metas = getmetas(request, request.graphdata, encode(cp), ["task"])
                if metas["task"]:
                    task = metas["task"][0][0]
                    if task not in taskdict.values():
                        deletablepage = PageEditor(request, cp, do_editor_backup=0)
                        if deletablepage.exists():
                            deletablepage.deletePage()
                    oldtasks[task] = cp
        coursepointdict = dict()
        for number, taskdata in taskdict.iteritems():
            taskpage = taskdata[0]
            deadline = taskdata[1]
            coursepoint = coursepointdict.get(number, None)
            if not coursepoint:
                if taskpage in oldtasks:
                    coursepoint = oldtasks[taskpage]
                else: 
                    coursepoint = randompage(request, coursepage)
                coursepointdict[number] = coursepoint
            pointdata = {u'task':[addlink(taskpage)]}
            nextlist = nodedict.get(number, [u'end'])
            for next in nextlist:
                if next != u'end':
                    nextcp = coursepointdict.get(next, None)
                    if not nextcp:
                        if next in oldtasks:
                            nextcp = oldtasks[next]
                        else:
                            nextcp = randompage(request, coursepage)
                        coursepointdict[next] = nextcp
                else:
                    nextcp = next
                if nextcp != "end" and nextcp.split("/")[1] != courseid:
                    nextcp = nextcp.split("/")[0] +"/"+ courseid +"/"+ nextcp.split("/")[2]
                if not pointdata.get(u'next', None):
                    pointdata[u'next'] = [addlink(nextcp)]
                else:
                    pointdata[u'next'].append(addlink(nextcp))

            pointdata[u'prerequisite'] = prerequisites.get(number, [u''])
            pointdata[u'split'] = splittypes.get(number, [u''])
            pointdata[u'deadline'] = [deadline]
            input = order_meta_input(request, coursepoint, pointdata, "repl")
            process_edit(request, input, True, {coursepoint:[coursepointcategory]})
            if coursepoint.split("/")[1] != courseid:
                savegraphdata = wikiutil.importPlugin(request.cfg,
                                                      'action',
                                                      'savegraphdata')
                editpage = PageEditor(request, coursepoint)
                path = editpage.getPagePath()
                savegraphdata(coursepoint, request, "", path, editpage)

                newname = coursepoint.split("/")[0] +"/"+ courseid +"/"+ coursepoint.split("/")[2]
                success, msgs = editpage.renamePage(newname)
        coursedata = {u'id':[courseid],
                      u'author':[addlink(request.user.name)],
                      u'name':[coursename],
                      u'description':[coursedescription],
                      u'start':[],
                      u'option':options}
        startlist = nodedict["start"]
        for node in startlist:
            cp = coursepointdict[node]
            if cp.split("/")[1] != courseid:
                cp = cp.split("/")[0] +"/"+ courseid +"/"+ cp.split("/")[2]
            coursedata[u'start'].append(addlink(cp))

        coursedata[u'split'] = splittypes.get("start", [u''])
        input = order_meta_input(request, coursepage, coursedata, "repl")
        process_edit(request, input, True, {coursepage:[coursecategory]})
        if coursepage.split("/")[1] != courseid:
            savegraphdata = wikiutil.importPlugin(request.cfg,
                                                  'action',
                                                  'savegraphdata')
            editpage = PageEditor(request, coursepage)
            path = editpage.getPagePath()
            savegraphdata(coursepage, request, "", path, editpage)

            newcoursename = coursepage.split("/")[0] +"/"+ courseid
            success, msgs = editpage.renamePage(newcoursename)

    return None 

def delete(request, pagename):
    pagename = encode(pagename)
    page = PageEditor(request, pagename, do_editor_backup=0)
    if page.exists():
        categories = list()
        metas = getmetas(request, request.graphdata, pagename, ["WikiCategory"])
        for category, type in metas["WikiCategory"]:
            if category == coursecategory:
                coursepage = FlowPage(request, pagename)
                courseflow = coursepage.getflow()
                for coursepoint in courseflow:
                    if coursepoint != "start":
                        pointpage = PageEditor(request, coursepoint, do_editor_backup=0)
                        if pointpage.exists():
                            pointpage.deletePage()
                page.deletePage()
                break
        return "Success"
    else:
        return "Page doesn't exist!"

def _enter_page(request, pagename):
    request.http_headers()
    request.theme.send_title("Teacher Tools", formatted=False,
    html_head='''<link rel="stylesheet" type="text/css" charset="utf-8"
    media="all" href="%s/raippa/css/calendar.css">
    ''' % (request.cfg.url_prefix_static))
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
    if not hasattr(request, 'graphdata'):
        getgraphdata(request)
    if request.form.has_key('save'):
        if request.form.has_key('course'):
            course = encode(request.form["course"][0])
            msg = editcourse(request, course)
        else:
            msg = editcourse(request)

        if msg:
            _enter_page(request, pagename)
            request.write(msg)
            _exit_page(request, pagename)
        else:
            url = u'%s/%s' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
    elif request.form.has_key("delete") and request.form.has_key("course"):
        try:
            page = request.form["course"][0]
            msg = delete(request, page)
        except:
            msg = "Failed to delete page."
        if msg == "Success":
            url = u'%s/%s' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
        else:
            _enter_page(request, pagename)
            request.write(msg)
            _exit_page(request, pagename)
    elif request.form.has_key('edit') and request.form.has_key('course'):
        _enter_page(request, pagename)
        course = encode(request.form["course"][0])
        courseform(request, course)
        _exit_page(request, pagename)
    elif request.form.has_key('cancel'):
        url = u'%s/%s' % (request.getBaseURL(), pagename)
        request.http_redirect(url)
    else:
        _enter_page(request, pagename)
        courseform(request)
        _exit_page(request, pagename)
