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
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editTask">
    <input type='submit' name='new' value='NewTask'>
</form><br>\n''' % request.request_uri.split("?")[0]
    pagehtml += u'''<form method="post" id="submitform" name="courseForm">
<input type="hidden" name="action" value="editCourse">\n'''
    if course:
        pagehtml += u'<input type="hidden" name="course" value="%s">\n' % course.replace('"', '&quot;')
    pagehtml += '''
    <div id="coursemenu">
    <div style="width:200px">
    <b>id:</b><br>
    <input class="maxwidth" id="courseid" type="text" name="courseid" value="%s"><br>
    <b>name:</b><br>
    <input class="maxwidth" type="text" id="coursename" name="coursename" value="%s"><br>
<input type="submit" name="save" value="Save" onclick="return submitTree(this);">
<input type="submit" name="cancel" value="Cancel" onclick="return submitTree(this);">
</div>
</div>
</form>
''' % (id, name)


    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, taskcategory)
    subjectdict = {None:list()}
    for page in pagelist:
        try:
            metas = getmetas(request, request.graphdata, encode(page), ["title", "description", "subject"])
            if metas["title"]:
                for description, type in metas["title"]:
                    break
            else:
                for description, type in metas["description"]:
                    break
            if metas["subject"]:
                for subject, metatype in metas["subject"]:
                    if not subjectdict.has_key(subject):
                        subjectdict[subject] = list()
                    subjectdict[subject].append((page, description))
            else:
                subjectdict[None].append((page, description))
        except:
            pass
    #subjectlist
    pagehtml += u'''<div id="tasklist_cont"> Tasks subjects: <br>
    <select style="width:190px"
    id="ttypesel" name="tasksubject">\n'''
    for subject in subjectdict:
        pagehtml+=u'<option value="t_type_%s">%s</option>\n' % (subject, subject)
    pagehtml += u'''</select>
<br>
<br>
Tasks:
'''
    #tasklists
    for subject, tasklist in subjectdict.iteritems():
		pagehtml +=  u'''<div class="tasklist" id="t_type_%s">\n''' % unicode(subject).replace('"','&quot;')
		for taskpagename, taskdescription in tasklist:
			pagehtml += u'''<div class="dragItem"><input type="hidden" name="%s"
	value="%s">%s</div>\n''' % (taskdescription.replace('"', '&quot;'), taskpagename, taskdescription)
		pagehtml += u'</div></div>\n'

    pagehtml += u'''
<div id="start">Start by dragging here!<br></div>
'''
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
    request.write(u'%s' % pagehtml)

def editcourse(request, coursepage=None):
    _ = request.getText
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
                splittypes[key.split("_")[0]] = [request.form.get(key, [u'select'])[0]]
            elif key.endswith("_deadline"):
                if not taskdict.has_key(key.split("_")[0]):
                    taskdict[key.split("_")[0]] = [unicode(), unicode()]
                taskdict[key.split("_")[0]][1] = [request.form.get(key, [u''])[0]]

    if not courseid:
        return "Missing course id."
    if not coursename:
        return "Missing course name."
    if not taskdict:
        return "Missing task list."

    if not coursepage:
        newlist = list()
        coursepage = randompage(request, "Course") 
        newlist.append(coursepage)

        coursepointdict = dict()
        for number, taskdata in taskdict.iteritems():
            taskpage = taskdata[0]
            deadline = taskdata[1]
            coursepoint = coursepointdict.get(number, None)
            if not coursepoint:
                coursepoint = randompage(request, coursepage)
                newlist.append(coursepoint)
                coursepointdict[number] = coursepoint

            pointdata = {u'task': [addlink(taskpage)],
                         u'prerequisite': prerequisites.get(number, [u'']),
                         u'split': splittypes.get(number, [u'select']),
                         u'deadline': deadline}

            nextlist = nodedict.get(number, [u'end'])
            for next in nextlist:
                if next != u'end':
                    nextcp = coursepointdict.get(next, None)
                    if not nextcp:
                        nextcp = randompage(request, coursepage)
                        newlist.append(nextcp)
                        coursepointdict[next] = nextcp
                else:
                    nextcp = next
                if not pointdata.get(u'next', None):
                    pointdata[u'next'] = [addlink(nextcp)]
                else:
                    pointdata[u'next'].append(addlink(nextcp))

            input = order_meta_input(request, coursepoint, pointdata, "add")
            msg = process_edit(request, input, True, {coursepoint:[coursepointcategory]})             
            unchanged = _(u'%s: Unchanged') % coursepoint
            changed = _(u'%s: Thank you for your changes. Your attention to detail is appreciated.' % coursepoint)
            if not (changed in msg or unchanged in msg):
                for page in newlist:
                    deletablepage = PageEditor(request, page, do_editor_backup=0)
                    if deletablepage.exists():
                        deletablepage.deletePage()
                return False

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
        msg = process_edit(request, input, True, {coursepage:[coursecategory]})
        unchanged = _(u'%s: Unchanged') % coursepage
        changed = _(u'%s: Thank you for your changes. Your attention to detail is appreciated.' % coursepage)
        if changed in msg or unchanged in msg:
            return True
        else:
            for page in newlist:
                deletablepage = PageEditor(request, page, do_editor_backup=0)
                if deletablepage.exists():
                    deletablepage.deletePage()
            return False
    else:
        course = FlowPage(request, coursepage)
        deletelist = list()
        newlist = list()
        oldtasks = dict()
        backupdict = {coursepage: Page(request, coursepage).get_real_rev()}
        
        tasks = list()
        for valuelist in taskdict.values():
            tasks.extend(valuelist)

        for cp in course.getflow():
            if cp != "start":
                backupdict[cp] = Page(request, cp).get_real_rev() 
                metas = getmetas(request, request.graphdata, encode(cp), ["task"])
                if metas["task"]:
                    task = metas["task"][0][0]
                    if task not in tasks:
                        deletelist.append(cp)
                    else:
                        oldtasks[task] = cp
        coursepointdict = dict()
        for number, taskdata in taskdict.iteritems():
            taskpage = taskdata[0]
            deadline = taskdata[1]

            coursepoint = coursepointdict.get(number, None)
            if not coursepoint:
                if taskpage in oldtasks:
                    coursepoint = oldtasks[taskpage]
                elif len(deletelist) > 0:
                    coursepoint = deletelist.pop()
                else: 
                    coursepoint = randompage(request, coursepage)
                    newlist.append(coursepoint)
                coursepointdict[number] = coursepoint

            pointdata = {u'task': [addlink(taskpage)],
                         u'prerequisite': prerequisites.get(number, [u'']),
                         u'split': splittypes.get(number, [u'select']),
                         u'deadline': deadline,
                         u'next': []}

            nextlist = nodedict.get(number, [u'end'])
            for next in nextlist:
                if next != u'end':
                    nextcp = coursepointdict.get(next, None)
                    if not nextcp:
                        task = taskdict.get(next, [u'', u''])[0]
                        if task and task in oldtasks:
                            nextcp = oldtasks[task]
                        elif len(deletelist) > 0:
                            nextcp = deletelist.pop()
                        else:
                            nextcp = randompage(request, coursepage)
                            newlist.append(nextcp)
                        coursepointdict[next] = nextcp
                else:
                    nextcp = u'end'
                pointdata[u'next'].append(addlink(nextcp))

            input = order_meta_input(request, coursepoint, pointdata, "repl")
            msg = process_edit(request, input, True, {coursepoint:[coursepointcategory]})
            unchanged = _(u'%s: Unchanged') % coursepoint
            changed = _(u'%s: Thank you for your changes. Your attention to detail is appreciated.' % coursepoint)
            if not (changed in msg or unchanged in msg):
                for page, rev in backupdict.iteritems():
                    if Page(request, page).get_real_rev() > rev:
                        old = Page(request, page, rev=rev)
                        reverted = PageEditor(request, page)
                        revstr = '%08d' % rev
                        try:
                            msg = reverted.saveText(old.get_raw_body(), 0, extra=revstr, action="SAVE/REVERT")
                        except:
                            pass
                for page in newlist:
                    deletablepage = PageEditor(request, page, do_editor_backup=0)
                    if deletablepage.exists():
                        deletablepage.deletePage()
                return False

        coursedata = {u'id':[courseid],
                      u'author':[addlink(request.user.name)],
                      u'name':[coursename],
                      u'description':[coursedescription],
                      u'start':[],
                      u'option':options,
                      u'split':splittypes.get("start", [u''])}

        startlist = nodedict["start"]
        for node in startlist:
            cp = coursepointdict[node]
            coursedata[u'start'].append(addlink(cp))

        input = order_meta_input(request, coursepage, coursedata, "repl")
        msg = process_edit(request, input, True, {coursepage:[coursecategory]})
        unchanged = _(u'%s: Unchanged') % coursepage
        changed = _(u'%s: Thank you for your changes. Your attention to detail is appreciated.' % coursepage)
        if changed in msg or unchanged in msg:
            for page in deletelist:
                deletablepage = PageEditor(request, page, do_editor_backup=0)
                if deletablepage.exists():
                    deletablepage.deletePage()
            return True
        else:
            for page, rev in backupdict.iteritems():
                if Page(request, page).get_real_rev() > rev:
                    old = Page(request, page, rev=rev)
                    reverted = PageEditor(request, page)
                    revstr = '%08d' % rev
                    try:
                        msg = reverted.saveText(old.get_raw_body(), 0, extra=revstr, action="SAVE/REVERT")
                    except:
                        pass
            for page in newlist:
                deletablepage = PageEditor(request, page, do_editor_backup=0)
                if deletablepage.exists():
                    deletablepage.deletePage()
            return False

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
        else:
            course = None
        if not editcourse(request, course):
            _enter_page(request, pagename)
            if course:
                request.write(u'Edit failed. Reverted back to original.')
            else:
                request.write(u'Edit failed.')
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
