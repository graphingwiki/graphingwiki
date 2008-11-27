# -*- coding: utf-8 -*-"
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import get_metas
from graphingwiki.editing import getkeys
from graphingwiki.editing import set_metas
from graphingwiki.editing import metatable_parseargs

from raippa import addlink, pageexists, revert, randompage, getflow
from raippa import raippacategories
from raippa import RaippaUser

action_name = 'EditCourse'

def courseform(request, course=None):
    if course:
        metas = get_metas(request, course, ["id", "name", "description", "option"])
        if metas["id"]:
            id = metas["id"].pop()
        else:
            id = unicode()

        if metas["name"]:
            name = metas["name"].pop()
        else:
            name = unicode()

        if metas["description"]:
            coursedescription = metas["description"].pop()
        else:
            coursedescription = unicode()

        options = metas["option"]

        flow = getflow(request, course)
        tasks = dict()
        for cp in flow:
            if cp != "start":
                metas = get_metas(request, cp, ["task"], display=True)
                if metas["task"]:
                    task = metas["task"].pop()
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
src="%s/raippajs/mootools-1.2-core-yc.js"></script>
<script type="text/javascript"
src="%s/raippajs/mootools-1.2-more.js"></script>
<script type="text/javascript"
src="%s/raippajs/moocanvas.js"></script>
<script type="text/javascript"
src="%s/raippajs/calendar.js"></script>
<script type="text/javascript"
src="%s/raippajs/dragui.js"></script>\n''' % (request.cfg.url_prefix_static,
request.cfg.url_prefix_static, request.cfg.url_prefix_static,request.cfg.url_prefix_static,request.cfg.url_prefix_static)
    pagehtml += u'''
<form method="POST" action="%s">
    <input type="hidden" name="action" value="EditTask">
    <input type='submit' name='new' value='NewTask'>
</form><br>\n''' % request.request_uri.split("?")[0]
    pagehtml += u'''
<form method="post" id="submitform" name="courseForm">
<input type="hidden" name="action" value="%s">\n''' % action_name
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


    pagelist, metakeys, styles = metatable_parseargs(request, raippacategories["taskcategory"])
    subjectdict = {None:list()}
    for page in pagelist:
        metas = get_metas(request, page, ["title", "subject"])
        if metas["title"]:
            description = metas["title"].pop()
        else:
            description = page+" (missing title)"

        if metas["subject"]:
            for subject in metas["subject"]:
                if not subjectdict.has_key(subject):
                    subjectdict[subject] = list()
                subjectdict[subject].append((page, description))
        else:
            subjectdict[None].append((page, description))

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
                    metas = get_metas(request, tasks[next], ["title"])
                    if metas["title"]:
                        description = metas["title"].pop()
                    else:
                        description = tasks[next]+" (missing title)"

                    keys = ["deadline", "prerequisite", "split"] 
                    metas = get_metas(request, next, keys, display=True)
                    if metas["split"]:
                        split = metas["split"].pop()
                    else:
                        split = u'select'

                    if metas["prerequisite"]:
                        prerequisites = u',"'
                        temp = metas["prerequisite"]
                        prerequisites += ",".join(temp)
                        prerequisites += u'"'
                    else:
                        prerequisites = u',""' 

                    if metas["deadline"]:
                        deadline = metas["deadline"].pop()
                    else:
                        deadline = unicode()

                    html += u'newBox("%s","%s","%s","%s"%s,"%s");\n' % (tasks[point].replace('"', '&quot;'), tasks[next], description.replace('"', '&quot;'), split, prerequisites, deadline)
                    #html += u'newBox("%s","%s","%s");\n' % (task, tasks[next], description)
                    donelist.append(point)
                    if next not in donelist:
                        html += addNode(next)
        return html

    startlist = flow.get("start", None)
    if startlist:
        for point in startlist:
            metas = get_metas(request, tasks[point], ["title"])
            if metas["title"]:
                description = metas["title"].pop()
            else:
                description = tasks[point]+" (missing title)"

            metas = get_metas(request, point, ["prerequisite", "split", "deadline"], display=True)

            if metas["split"]:
                split = metas["split"].pop()
            else:
                split = u'select'

            if metas["prerequisite"]:
                prerequisites = u',"'
                temp = metas["prerequisite"] 
                prerequisites += ",".join(temp)
                prerequisites += u'"'
            else:
                prerequisites = u',""'

            if metas["deadline"]:
                deadline = metas["deadline"].pop()
            else:
                deadline = unicode()

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
        elif key == "option":
            for key in request.form.get("option", []):
                options.append(key)
        elif key != "save" and key != "action":
            if key.endswith("_next"):
                values = request.form.get(key, [unicode()])[0]
                key = key.split("_")[0]
                if not nodedict.get(key, None):
                    nodedict[key] = list()
                nodedict[key].extend(values.split(","))
            elif key.endswith("_value"):
                if not taskdict.has_key(key.split("_")[0]):
                    taskdict[key.split("_")[0]] = [unicode(), unicode()]
                taskdict[key.split("_")[0]][0] = request.form.get(key, [unicode()])[0]
            elif key.endswith("_require"):
                values = request.form.get(key, [unicode()])[0].split(",")
                if values:
                    prerequisites[key.split("_")[0]] = values
            elif key.endswith("_type"):
                splittypes[key.split("_")[0]] = [request.form.get(key, [u'select'])[0]]
            elif key.endswith("_deadline"):
                if not taskdict.has_key(key.split("_")[0]):
                    taskdict[key.split("_")[0]] = [unicode(), unicode()]
                taskdict[key.split("_")[0]][1] = [request.form.get(key, [unicode()])[0]]

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

            pointdata = {"task": [addlink(taskpage)],
                         "prerequisite": prerequisites.get(number, [unicode()]),
                         "split": splittypes.get(number, [u'select']),
                         "deadline": deadline,
                         "gwikicategory": [raippacategories["coursepointcategory"]]}

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

            pointdata = {coursepoint: pointdata}
            result, msg = set_metas(request, dict(), dict(), pointdata)
            if not result:
                for page in newlist:
                    if pageexists(request, page):
                        msg = PageEditor(request, page, do_editor_backup=0).deletePage()
                return False

        coursedata = {"id": [courseid],
                      "author": [addlink(request.user.name)],
                      "name": [coursename],
                      "description": [coursedescription],
                      "start": list(),
                      "option": options,
                      "gwikicategory": [raippacategories["coursecategory"]]}

        startlist = nodedict["start"]
        for node in startlist:
            cp = coursepointdict[node]
            coursedata[u'start'].append(addlink(cp))

        coursedata[u'split'] = splittypes.get("start", [unicode()])
        coursedata = {coursepage: coursedata}
        result, msg = set_metas(request, dict(), dict(), coursedata)
        if result:
            return True
        else:
            for page in newlist:
                if pageexists(request, page):
                    msg = PageEditor(request, page, do_editor_backup=0).deletePage()
            return False
    else:
        deletelist = list()
        newlist = list()
        oldtasks = dict()
        backupdict = {coursepage: Page(request, coursepage).get_real_rev()}
        
        tasks = list()
        for valuelist in taskdict.values():
            tasks.extend(valuelist)

        flow = getflow(request, coursepage)
        for cp in flow:
            if cp != "start":
                backupdict[cp] = Page(request, cp).get_real_rev() 
                metas = get_metas(request, cp, ["task"], display=True)
                if metas["task"]:
                    task = metas["task"].pop()
                    if task not in tasks:
                        deletelist.append(cp)
                    else:
                        oldtasks[task] = cp
                else:
                    pass
                    #TODO: report missing task

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

            pointdata = {"task": [addlink(taskpage)],
                         "prerequisite": prerequisites.get(number, list()),
                         "split": splittypes.get(number, [u'select']),
                         "deadline": deadline,
                         "next": list(),
                         "gwikicategory": [raippacategories["coursepointcategory"]]}

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
                pointdata["next"].append(addlink(nextcp))

            if pageexists(request, coursepoint):
                oldkeys = getkeys(request, coursepoint)
                remove = {coursepoint: oldkeys}
            else:
                remove = dict()

            pointdata = {coursepoint: pointdata}
            result, msg = set_metas(request, remove, dict(), pointdata)
            if not result:
                for page, rev in backupdict.iteritems():
                    revert(request, page, rev)

                for page in newlist:
                    if pageexists(request, page):
                        msg = PageEditor(request, page, do_editor_backup=0).deletePage()
                #TODO: maybe return little info here?
                return False

        coursedata = {"id": [courseid],
                      "author": [addlink(request.user.name)],
                      "name": [coursename],
                      "description": [coursedescription],
                      "start": list(),
                      "option": options,
                      "split": splittypes.get("start", [unicode()]),
                      "gwikicategory": [raippacategories["coursecategory"]]}

        startlist = nodedict["start"]
        for node in startlist:
            cp = coursepointdict[node]
            coursedata[u'start'].append(addlink(cp))

        if pageexists(request, coursepage):
            oldkeys = getkeys(request, coursepage)
            remove = {coursepage: oldkeys}
        else:
            remove = dict()

        coursedata = {coursepage: coursedata}
        result, msg = set_metas(request, remove, dict(), coursedata)
        if result:
            for page in deletelist:
                if pageexists(request, page):
                    msg = PageEditor(request, page, do_editor_backup=0).deletePage()
            return True
        else:
            for page, rev in backupdict.iteritems():
                revert(request, page, rev)

            for page in newlist:
                if pageexists(request, page):
                    msg = PageEditor(request, page, do_editor_backup=0).deletePage()
            return False

def delete(request, pagename):
    #TODO: handle failed delete
    if pageexists(request, pagename):
        categories = list()
        metas = get_metas(request, pagename, ["gwikicategory"])
        if raippacategories["coursecategory"] in metas["gwikicategory"]:
            courseflow = getflow(request, pagename)
            for coursepoint in courseflow:
                if coursepoint != "start":
                    if pageexists(request, coursepoint):
                        msg = PageEditor(request, coursepoint, do_editor_backup=0).deletePage()
            msg = PageEditor(request, pagename, do_editor_backup=0).deletePage()
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
    ruser = RaippaUser(request)
    _enter_page(request, pagename)

    if not ruser.isTeacher():
        action = {"action_name": action_name}
        message = u'You are not allowed to do %(action_name)s on this page.' % action
        Page(request, pagename).send_page(msg=message)

    if request.form.has_key('cancel'):
        message = u'Edit was cancelled.'
        Page(request, pagename).send_page(msg=message)
    elif request.form.has_key('save'):
        coursepage = request.form.get("course", [None]).pop()
        if not editcourse(request, coursepage):
            if coursepage:
                message = u'Edit failed. Reverted back to original.'
            else:
                message = u'Edit failed.'
        else:
            message = u'Thank you for your changes. Your attention to detail is appreciated.'

        Page(request, pagename).send_page(msg=message)
    elif request.form.has_key("delete") and request.form.has_key("course"):
        coursepage = request.form.get("course", [None]).pop()
        message = delete(request, coursepage)
        Page(request, pagename).send_page(msg=message)
    elif request.form.has_key('edit') and request.form.has_key('course'):
        coursepage = request.form.get("course", [None]).pop()
        courseform(request, coursepage)
    else:
        if request.form.has_key("new"):
            coursepage = None
        else:
            coursepage = request.form.get("course", [None])[0]
            if not coursepage:
                coursepage = pagename

        courseform(request, coursepage)
    _exit_page(request, pagename)
