# -*- coding: utf-8 -*-"
import random
from operator import itemgetter

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
        for name, type in meta["name"]:
            self.name = name
            break
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
        for category, type in metas[u'WikiCategory']:
            self.categories.append(category)

        self.flow = self.getflow()

    def getflow(self):
        if coursecategory in self.categories:
            metakey = "task"
            flow = list()
        else:
            metakey = "question"
            flow = [("start", self.pagename)]

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
                        pagelist = linking_in.get("answer", [])
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
    <input type='submit' name='selectcourse' value='CourseStats'>
</form>'''
    html += u'''
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editCourse">
    <select size="1" name="course">''' % request.request_uri.split("?")[0]
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, coursecategory)
    for page in pagelist:
        html += u'<option name="course" value="%s">%s\n' % (page, page)
    html += '''
    </select>
    <input type='submit' name='edit' value='EditCourse'>
    <input type='submit' name='new' value='NewCourse'>
</form>
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editTask">
    <select size="1" name="task">''' % request.request_uri.split("?")[0]
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
    <input type='submit' name='selectuser' value='SelectUser'><br>
</form>
High level flow:'''
    graphhtml = unicode()
    for point, coursepoint in courseobj.flow:
        if isinstance(point, FlowPage):
            bars = str()
            groups = "&groups="
            for index, point_tuple in enumerate(point.flow):
                question = point_tuple[0]
                taskpoint = point_tuple[1]
                usercount = 0
                taskusercount = 0
                for user in courseobj.users:
                    if user.status == taskpoint:
                        usercount += 1
                    if user.status.startswith(taskpoint):
                        taskusercount += 1
                if question == "start":
                    graphhtml += u'<br>%s:<br>' % taskpoint
                    bars += "&start=%i,0,0" % usercount
                    groups += "start,"
                    html += u'<br>%s %i\n' % (taskpoint, taskusercount)
                else:
                    average, alltimeaverage = question.getaverage(courseobj.pagename, taskpoint)
                    bars += "&Q%i=%i,%i,%i" % (index, usercount, average, alltimeaverage)

                    groups += "Q%i," % (index)
            labels = "&labels=users,average,alltime"
            graphhtml += "<img src='%s/%s?action=drawchart%s%s%s'><br>\n" % (request.getBaseURL(), request.page.page_name, labels, bars, groups.rstrip(","))
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
        html = unicode()
        #?action=drawchart&labels=users,average&start=0,1&Q1=2,3&Q2=3,5&groups=start,Q1,Q2
        barhtml = u'%s/%s?action=drawchart&labels=right,wrong' % (request.getBaseURL(), pagename)
        bars = list()
        questionlisthtml = unicode()
        areahtml = unicode()
        course = FlowPage(request, encode(request.form["course"][0]))
        user = User(request, encode(request.form["user"][0]), course.pagename)
        for point, coursepoint in course.flow:
            if isinstance(point, FlowPage):
                task = list()
                successdict = dict()
                for question, taskpoint in point.flow:
                    if question != "start":
                        successdict[question.pagename] = [0,0]
                        if question.pagename not in task:
                            task.append(question.pagename)
                        for useranswer in question.histories:
                            if useranswer[3] == course.pagename and useranswer[0] == user.id:
                                if useranswer[1] == "True":
                                    successdict[question.pagename][0] += 1
                                else:
                                    successdict[question.pagename][1] += 1
                for question in task:
                    bars.append(question)
                    barhtml += "&Q%s=%i,%i" % (question.split("/")[1], successdict[question][0], successdict[question][1])
                    questionlisthtml += u'<option value="%s">%s\n' % (question, question)

        html += u"name: %s<br>studentid: %s<br>\n" % (user.name, user.id)
        bargroups = "&groups="
        barsize = 750/len(bars)
        start = 22
        maphtml = '<map id="studentchart" name="studentchart">'
        for bar in bars:
            maphtml += '<area shape="rect" coords="%i,266,%i,289" href="%s?action=TeacherTools&question=%s&user=%s&course=%s&selectquestion"/>' % (start, start+barsize, pagename, bar, user.id, course.pagename)
            bargroups += "Q%s," % bar.split("/")[1]
            start += barsize
        maphtml += '</map>'
        html += '<img src="%s%s" usemap="#studentchart">' % (barhtml, bargroups.rstrip(","))
        html += maphtml
        request.write(html)
    elif request.form.has_key('selectquestion') and request.form.has_key('question') \
         and request.form.has_key('course'):
        course = FlowPage(request, encode(request.form["course"][0]))
        question = Question(request, encode(request.form["question"][0]))
        html = unicode()
        if request.form.has_key('user'):
            user = User(request, encode(request.form["user"][0]), course.pagename)
            html += "%s: %s<br>" % (question.pagename, question.question)
            for answer in question.answers:
                html += "%s: %s tip: %s<br>" % (question.answers[answer][0], answer, question.answers[answer][1])
            html += "<br>%s's(%s) answer history:" % (user.name, user.id)
            for useranswer in question.histories:
                if useranswer[3] == course.pagename and useranswer[0] == user.id:
                    html += "<br>overal: %s, " % useranswer[1]
                    for answer in useranswer[2]:
                        html += "%s: %s, " % (useranswer[2][answer], answer)
        else:
            html += "%s: %s<br>\n" % (question.pagename, question.question)
            for answer in question.answers:
                html += "%s: %s " % (question.answers[answer][0], answer)
                if question.answers[answer][1]:
                    html += "tip %s<br>\n" % question.answers[answer][1]
                else:
                    html += "<br>\n"
            html += "<br>TOP 10 failures:<br>\n"
            top5dict = dict()
            for user, overalvalue, valuedict, course, task in question.histories:
                if overalvalue == "False":
                    for answer, value in valuedict.iteritems():
                        if value == "false":
                            if not top5dict.has_key(answer):
                                top5dict[answer] = 1
                            else:
                                top5dict[answer] += 1

            html += "<form>"
            for index, answer in enumerate(sorted(top5dict.items(), key=itemgetter(1), reverse=True)):
                if index > 9:
                    break
                html += u'%s: %i<input type="text"><input type="submit" value="SaveTip"><br>' % (answer[0], answer[1])
            html += "</form>"
        request.write(html)
    else:
        coursesform(request)
    _exit_page(request, pagename)
