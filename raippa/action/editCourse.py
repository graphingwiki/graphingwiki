# -*- coding: utf-8 -*-"
action_name = 'editCourse'

from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import getmetas
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import GraphData, encode
from graphingwiki.patterns import getgraphdata
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input

from raippa import addlink, randompage
from raippa import FlowPage

taskcategory = u'CategoryTask'
coursecategory = u'CategoryCourse'
coursepointcategory = u'CategoryCoursepoint'
statuscategory = 'CategoryStatus'
historycategory = 'CategoryHistory'

def taskform(request, course=None):
    if course:
        metas = getmetas(request, request.globaldata, course, ["id", "name", "description"])
        id = metas[u'id'][0][0]
        name = metas[u'name'][0][0]
        try:
            coursedescription = metas[u'description'][0][0]
        except:
            coursedescription = u''
        coursepage = FlowPage(request, course)
        flow = coursepage.getflow() 
        tasks = dict()
        for cp in flow:
            if cp != "start":
                metas = getmetas(request, request.globaldata, encode(cp), ["task"])
                if metas["task"]:
                    task = metas["task"][0][0]
                    tasks[cp] = task
    else:
        id = u''
        name = u''
        coursedescription = u''
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
src="%s/common/js/dragui.js"></script>\n''' % (request.cfg.url_prefix_static, request.cfg.url_prefix_static, request.cfg.url_prefix_static,request.cfg.url_prefix_static)
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
            metas = getmetas(request, request.globaldata, encode(page), ["description"])
            description = metas["description"][0][0]
            pagehtml += u'''
    <div class="dragItem"><input type="hidden" name="%s" value="%s">%s</div>\n''' % (description, page, description)
        except:
            pass
    pagehtml += u'''
</div>
<div id="start">Start by dragging here!<br></div>
<form method="post" id="submitform" name="courseForm" onsubmit="return submitTree()">
<input type="hidden" name="action" value="editCourse">\n'''
    if course:
        pagehtml += u'<input type="hidden" name="course" value="%s">\n' % course
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
                    metas = getmetas(request, request.globaldata, encode(tasks[next]), ["description"])
                    if metas["description"]:
                        description = metas["description"][0][0]
                    else:
                        description = tasks[next]
                    metas = getmetas(request, request.globaldata, encode(next), ["prerequisite", "split"])
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
                        prerequisites = unicode()

                    html += u'newBox("%s","%s","%s","%s"%s);\n' % (tasks[point], tasks[next], description, split, prerequisites)
                    #html += u'newBox("%s","%s","%s");\n' % (task, tasks[next], description)
                    donelist.append(point)
                    if next not in donelist:
                        html += addNode(next)
        return html

    startlist = flow.get("start", None)
    if startlist:
        for point in startlist:
            metas = getmetas(request, request.globaldata, encode(tasks[point]), ["description"])
            if metas["description"]:
                description = metas["description"][0][0]
            else:
                description = tasks[next]
            metas = getmetas(request, request.globaldata, encode(point), ["prerequisite", "split"])
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
                prerequisites = unicode()

            pagehtml += u'newBox("start","%s","%s","%s"%s);\n' % (tasks[point], description, split, prerequisites)
            #pagehtml += u'newBox("start","%s","%s");\n' % (task, description)
            pagehtml += addNode(point)

    pagehtml += '''
	}//loadData
    </script>\n'''
    if id:
        pagehtml += '<input id="courseid" type="hidden" name="courseid" value="%s">' % id 
    else:
        pagehtml += 'id: <input id="courseid" type="text" name="courseid"><br>'
    pagehtml += '''
name: <input type="text" id="coursename" name="coursename" value="%s"><br> 
description:<br> 
<textarea name="coursedescription" rows="10" cols="40">%s</textarea><br>
<input type="submit" name="save" value="Save">
</form>
''' % (name, coursedescription)

    request.write(u'%s' % pagehtml)

def editcourse(request, coursepage=None):
    courseid = unicode()
    coursename = unicode()
    coursedescription = unicode()

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
        elif key != "save" and key != "action":
            if key.endswith("_next"):
                values = request.form.get(key, [u''])[0]
                key = key.split("_")[0]
                if not nodedict.get(key, None):
                    nodedict[key] = list()
                nodedict[key].extend(values.split(","))
            elif key.endswith("_value"):
                taskdict[key.split("_")[0]] = request.form.get(key, [u''])[0]
            elif key.endswith("_require"):
                values = request.form.get(key, [u''])[0].split(",")
                #QUICK HACK. remove when dragui.js returns tasklist
                temp = list()
                for value in values:
                    temp.append(taskdict[value]) 
                values = temp
                #########
                if values:
                    prerequisites[key.split("_")[0]] = values
            elif key.endswith("_type"):
                splittypes[key.split("_")[0]] = [request.form.get(key, u'')[0]]

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
        for number, taskpage in taskdict.iteritems():
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
            input = order_meta_input(request, coursepoint, pointdata, "add")
            process_edit(request, input, True, {coursepoint:[coursepointcategory]})             

        page = PageEditor(request, coursepage)
        page.saveText("<<Raippa>>", page.get_real_rev())

        coursedata = {u'id':[courseid],
                      u'author':[addlink(request.user.name)],
                      u'name':[coursename],
                      u'description':[coursedescription],
                      u'start':[]}
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
        globaldata = GraphData(request)
        for cp in oldflow:
            if cp != "start":
                metas = getmetas(request, globaldata, encode(cp), ["task"])
                if metas["task"]:
                    task = metas["task"][0][0]
                    if task not in taskdict.values():
                        deletablepage = PageEditor(request, cp, do_editor_backup=0)
                        if deletablepage.exists():
                            deletablepage.deletePage()
                    oldtasks[task] = cp
        coursepointdict = dict()
        for number, taskpage in taskdict.iteritems():
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
                if not pointdata.get(u'next', None):
                    pointdata[u'next'] = [addlink(nextcp)]
                else:
                    pointdata[u'next'].append(addlink(nextcp))

            pointdata[u'prerequisite'] = prerequisites.get(number, [u''])
            pointdata[u'split'] = splittypes.get(number, [u''])
            input = order_meta_input(request, coursepoint, pointdata, "repl")
            process_edit(request, input, True, {coursepoint:[coursepointcategory]})
        coursedata = {u'id':[courseid],
                      u'author':[addlink(request.user.name)],
                      u'name':[coursename],
                      u'description':[coursedescription],
                      u'start':[]}
        startlist = nodedict["start"]
        for node in startlist:
            cp = coursepointdict[node]
            coursedata[u'start'].append(addlink(cp))

        coursedata[u'split'] = splittypes.get("start", [u''])
        input = order_meta_input(request, coursepage, coursedata, "repl")
        process_edit(request, input, True, {coursepage:[coursecategory]})

    return None 

def delete(request, pagename):
    pagename = encode(pagename)
    page = PageEditor(request, pagename, do_editor_backup=0)
    if page.exists():
        categories = list()
        metas = getmetas(request, request.globaldata, pagename, ["WikiCategory"])
        for category, type in metas["WikiCategory"]:
            if category == coursecategory:
                coursepage = FlowPage(request, pagename)
                courseflow = coursepage.getflow()
                for coursepoint in courseflow:
                    if coursepoint != "start":
                        pointpage = PageEditor(request, coursepoint, do_editor_backup=0)
                        if pointpage.exists():
                            #print "delete", pointpage.page_name
                            pointpage.deletePage()
                #print "delete", page.page_name
                page.deletePage()
                break
        return "Success"
    else:
        return "Page doesn't exist!"

def _enter_page(request, pagename):
    request.http_headers()
    request.theme.send_title("Teacher Tools", formatted=False)
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
    request.globaldata = getgraphdata(request)
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
            url = u'%s/%s?action=TeacherTools' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
    elif request.form.has_key("delete") and request.form.has_key("course"):
        try:
            page = request.form["course"][0]
            msg = delete(request, page)
        except:
            msg = "Failed to delete page."
        if msg == "Success":
            url = u'%s/%s?action=TeacherTools' % (request.getBaseURL(), pagename)
            request.http_redirect(url)
        else:
            _enter_page(request, pagename)
            request.write(msg)
            _exit_page(request, pagename)
    elif request.form.has_key('edit') and request.form.has_key('course'):
        _enter_page(request, pagename)
        course = encode(request.form["course"][0])
        taskform(request, course)
        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        taskform(request)
        _exit_page(request, pagename)
