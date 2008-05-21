# -*- coding: utf-8 -*-"
import random

from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import edit_meta, getkeys, getmetas
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import GraphData, encode

coursecategory = u'CategoryCourse'
taskcategory = u'CategoryTask'
usercategory = u'CategoryUser'
historycategory = u'CategoryHistory'
answercategory = u'CategoryAnswer'
tipcategory = u'CategoryTip'

class User:
    def __init__(self, request, userid, course):
        self.request = request
        self.id = userid
        self.status = unicode()
        statuspage = encode(self.id + "/status")
        globaldata = GraphData(request)
        metakeys = getkeys(globaldata, statuspage)
        if metakeys.has_key(course):
            self.incourse = True
            meta = getmetas(request, globaldata, statuspage, [course])
            coursepoint = meta[course][0][0]
            if coursepoint == u'end':
                self.status = u'end'
            else:
                meta = getmetas(request, globaldata, statuspage, [coursepoint])
                self.status = meta[coursepoint][0][0]
        else:
            self.incourse = False

        self.name = unicode()
        meta = getmetas(request, globaldata, encode(self.id), ["name"])
        if meta["name"]:
            self.name = meta["name"][0][0]
        globaldata.closedb()

class FlowPage:
    def __init__(self, request, course, pagename=""):
        self.request = request
        self.course = encode(course)

        self.users = list()
        if not pagename:
            self.pagename = self.course
            globaldata, allusers, metakeys, styles = metatable_parseargs(self.request, usercategory)
            for user in allusers: 
                user = User(self.request, user, self.course)
                if user.incourse:
                    self.users.append(user)
            globaldata.closedb()
        else:
            self.pagename = encode(pagename)

        self.categories = list()
        globaldata = GraphData(request)
        metas = getmetas(request, globaldata, self.pagename, [u'WikiCategory'])
        globaldata.closedb()
        for metatuple in metas[u'WikiCategory']:
            self.categories.append(metatuple[0])

        self.flow = self.getflow()

    def getflow(self):
        if coursecategory in self.categories:
            metakey = "task"
        else:
            metakey = "question"

        globaldata = GraphData(self.request)
        meta = getmetas(self.request, globaldata, self.pagename, ["start"])
        flowpoint = encode(meta["start"][0][0])
        if metakey == "question":
            flow = [("start", self.pagename)]
        else:
            flow = list()

        while flowpoint != "end":
            meta = getmetas(self.request, globaldata, encode(flowpoint), [metakey, "next"])
            if metakey == "task":
                metakeypage = FlowPage(self.request, self.course, meta[metakey][0][0])
            else:
                metakeypage = Question(self.request, meta[metakey][0][0])
            flow.append((metakeypage, flowpoint))
            flowpoint = encode(meta["next"][0][0])
        globaldata.closedb()
        if metakey == "task":
            flow.append(("end", self.pagename))

        return flow

class Question:
    def __init__(self, request, questionpage):
        self.pagename = encode(questionpage)

        self.question = unicode()
        self.asnwertype = unicode()
        self.note = unicode()
        globaldata = GraphData(request)
        metas = getmetas(request, globaldata, self.pagename, [u'question', u'answertype', u'note'])
        globaldata.closedb()
        if metas[u'question']:
            self.question = metas[u'question'][0][0]
        if metas[u'answertype']:
            self.answertype = metas[u'answertype'][0][0]
        if metas[u'note']:
            self.note = metas[u'note'][0][0]

        self.histories = list()
        self.answers = dict()
        globaldata = GraphData(request)
        page = globaldata.getpage(self.pagename)
        linking_in = page.get('in', {})
        pagelist = linking_in["question"]
        for page in pagelist:
            metas = getmetas(request, globaldata, page, [u'WikiCategory', u'user', u'overalvalue', u'false', u'true', u'course', u'task'])
            for metatuple in metas[u'WikiCategory']:
                if metatuple[0] == historycategory:
                    if metas[u'user'] and metas[u'overalvalue'] and metas[u'course']:
                        user = metas[u'user'][0][0]
                        overalvalue = metas[u'overalvalue'][0][0]
                        course = metas[u'course'][0][0]
                        if metas[u'task']:
                            task = metas[u'task'][0][0]
                        else:
                            task = u''
                        useranswers = dict()
                        for true in metas["true"]:
                            useranswers[metas["true"][0][0]] = "true"
                        for false in metas["false"]:
                            useranswers[metas["false"][0][0]] = "false"
                        else:
                            self.histories.append([user, overalvalue, useranswers, course, task])
                    break
                elif metatuple[0] == answercategory:
                    for true in metas["true"]:
                        self.answers[metas["true"][0][0]] = ["true", ""]
                    for false in metas["false"]:
                        answerpage = globaldata.getpage(page)
                        linking_in = answerpage.get('in', {}) 
                        pagelist = linking_in["answer"]
                        tip = str()
                        for tippage in pagelist:
                            tipmetas = getmetas(request, globaldata, tippage, [u'WikiCategory', u'tip'])
                            for metatuple in tipmetas[u'WikiCategory']:
                                if metatuple[0] == tipcategory:
                                    tip = tipmetas[u'tip'][0][0]
                                    break
                            if tip != "":
                                break
                        self.answers[metas["false"][0][0]] = ["false", tip]
                    break
        globaldata.closedb()

    def getaverage(self, coursename=None, taskpoint=None):
        userlist = list()
        answercount = int()
        average = 0
        alltimeuserlist = list()
        alltimeanswercount = len(self.histories)
        alltimeaverage = 0

        for answer in self.histories:
            user = answer[0]
            if answer[3] == coursename and answer[4] == taskpoint:
                userlist.append(user)
                answercount += 1
            alltimeuserlist.append(user)

        usercount = len(set(userlist))
        if answercount > 0 and usercount > 0:
            average = answercount / usercount

        alltimeusercount = len(set(alltimeuserlist))
        if alltimeanswercount > 0 and alltimeusercount > 0:
            alltimeaverage = alltimeanswercount / alltimeusercount

        return average, alltimeaverage

def addlink(pagename):
    return '[['+pagename+']]'

def coursesform(request):
    html = str()
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, coursecategory)
    globaldata.closedb()
    if pagelist:
        html += u'''
<form method="POST">
    <input type="hidden" name="action" value="TeacherTools">
    <select name="course">'''

        for page in pagelist:
            html += u'<option value="%s">%s\n' % (page, page)

        html += u'''</select>
    <input type='submit' name='selectcourse' value='SelectCourse'>
</form>'''
    html += u'''
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editCourse">
    <input type='submit' name='new' value='NewCourse'>
</form>
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editTask">
    <select size="1" name="task">''' % (request.request_uri.split("?")[0], request.request_uri.split("?")[0])
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, taskcategory)
    for page in pagelist:
        html += u'<option name="task" value="%s">%s\n' % (page, page)
    html += '''
    </select>
    <input type='submit' name='edit' value='EditTask'>
    <input type='submit' name='new' value='NewTask'>
</form>
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editQuestion">
    <input type='submit' name='new' value='NewQuestion'>
</form>''' % request.request_uri.split("?")[0]

    request.write(html)

def getcoursegraph(request, courseobj):
    html = u'''
<form method="POST">
    <input type="hidden" name="action" value="TeacherTools">
    <input type="hidden" name="course" value="%s">
    <select name="user">''' % courseobj.pagename
    
    for user in courseobj.users:
        html += u'''
        <option value="%s">%s''' % (user.id, user.id)
    html += u'''
    </select>
    <br><input type='submit' name='selectuser' value='SelectUser'><br>
</form>
High level flow:'''
    graphhtml = unicode()
    for point, coursepoint in courseobj.flow:
        if isinstance(point, FlowPage):
            bars = str()
            for question, taskpoint in point.flow:
                usercount = 0
                taskusercount = 0
                for user in courseobj.users:
                    if user.status == taskpoint:
                        usercount += 1
                    if user.status.startswith(taskpoint):
                        taskusercount += 1
                if question == "start":
                    graphhtml += u'<br>%s:<br>' % taskpoint
                    bars += "&users=%i!%s" % (usercount, question)
                    bars += "&average=0!" + question
                    bars += "&alltime=0!" + question
                    html += u'<br>%s %i\n' % (taskpoint, taskusercount)
                else:
                    average, alltimeaverage = question.getaverage(courseobj.pagename, taskpoint)
                    bars += "&users=%i!%s" % (usercount, question.pagename)
                    bars += "&average=" + str(average) + "!" + question.pagename
                    bars += "&alltime=" + str(alltimeaverage) + "!" + question.pagename
            #TODO
            #graphhtml += "<img src='http://172.16.253.131/raippa/RAIPPA?action=drawgraph%s'><br>\n" % bars
        else:
            html += u'<br>%s' % point
            usercount = int()
            for user in courseobj.users:
                if user.status.startswith(point):
                    usercount += 1
            html += u' %i<br>' % usercount
            html += graphhtml
    return html

def _enter_page(request, pagename):
    _ = request.getText
    
    request.theme.send_title(_('Teacher Tools'), formatted=False)
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
    request.http_headers()

    _enter_page(request, pagename)
    if request.form.has_key('selectcourse'):
        coursesform(request)
        course = FlowPage(request, encode(request.form["course"][0]))
        request.write(getcoursegraph(request, course))
    elif request.form.has_key('selectuser') and request.form.has_key('course'):
        course = FlowPage(request, encode(request.form["course"][0]))
        user = User(request, encode(request.form["user"][0]), course.pagename)
        request.write("name: %s<br>studentid: %s<br>" % (user.name, user.id))
        for point, coursepoint in course.flow:
            if isinstance(point, FlowPage):
                for question, taskpoint in point.flow:
                    if question != "start":
                        for useranswer in question.histories:
                            request.write(useranswer)
    elif request.form.has_key('raw') and request.form.has_key('course'):
        course = FlowPage(request, encode(request.form["course"][0]))
        request.write(course.pagename)
        for point, coursepoint in course.flow:
            if isinstance(point, FlowPage):
                for point, taskpoint in point.flow:
                    userhtml = unicode()
                    for user in course.users:
                        if user.status == taskpoint:
                            userhtml += u", <b>%s</b>" % user.id
                        else:
                            userhtml += u''
                    if point == "start":
                        request.write("<br>---> %s: %s%s" % (taskpoint, point, userhtml))
                    else:
                        request.write("<br>------>%s: %s%s" % (taskpoint, point.pagename, userhtml))
                        for answer, value in point.answers.iteritems():
                            request.write("<br>---------> %s: %s" % (value[0], answer))
                            if value[1] != "":
                                request.write(", tip: %s" % value[1])
                        average, alltimeaverage = point.getaverage(course.pagename, taskpoint)
                        request.write("<br>average: %i, all time average: %i" % (average, alltimeaverage))
                        for useranswer in point.histories:
                            if useranswer[3] == course.pagename and useranswer[4] == taskpoint:
                                request.write("<br>---------> %s: %s" % (useranswer[0], useranswer[1]))
                                for answer in useranswer[2]:
                                    request.write("<br>------------> %s" % answer) 
            else:
                request.write("<br>%s: %s" % (course.pagename, point))
                for user in course.users:
                    if point == user.status:
                        request.write(", <b>%s</b>" % user.id)
    else:
        coursesform(request)
    _exit_page(request, pagename)
