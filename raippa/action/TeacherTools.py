from operator import itemgetter

from graphingwiki.editing import edit_meta, getkeys, getmetas
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import GraphData, encode
from graphingwiki.patterns import getgraphdata

from raippa import Question
from raippa import RaippaUser
from raippa import addlink

coursecategory = u'CategoryCourse'
taskcategory = u'CategoryTask'
usercategory = u'CategoryUser'
questioncategory = u'CategoryQuestion'

class FlowPage:
    def __init__(self, request, course, pagename=""):
        self.request = request
        self.course = encode(course)

        self.users = list()
        if not pagename:
            self.pagename = self.course
            globaldata, allusers, metakeys, styles = metatable_parseargs(self.request, usercategory)
            for user in allusers: 
                user = RaippaUser(self.request, user)
                if self.course in user.getcourselist():
                    self.users.append(user)
        else:
            self.pagename = encode(pagename)

        self.categories = list()
        metas = getmetas(request, self.request.globaldata, self.pagename, [u'WikiCategory'])
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

        meta = getmetas(self.request, self.request.globaldata, self.pagename, ["start"])
        flowpoint = encode(meta["start"][0][0])
        if metakey == "question":
            flow = [("start", self.pagename)]
        else:
            flow = list()

        while flowpoint != "end":
            meta = getmetas(self.request, self.request.globaldata, encode(flowpoint), [metakey, "next"])
            if metakey == "task":
                metakeypage = FlowPage(self.request, self.course, meta[metakey][0][0])
            else:
                metakeypage = Question(self.request, meta[metakey][0][0])
            flow.append((metakeypage, flowpoint))
            flowpoint = encode(meta["next"][0][0])
        if metakey == "task":
            flow.append(("end", self.pagename))

        return flow

def coursesform(request):
    html = str()
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, coursecategory)
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
</form>'''
    html += '''
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editQuestion">
    ''' % request.request_uri.split("?")[0]
    #<select size="1" name="question">
    #globaldata, pagelist, metakeys, styles = metatable_parseargs(request, questioncategory)
    #for page in pagelist:
    #    html += u'<option name="question" value="%s">%s\n' % (page, page)
    #</select>
    #<input type='submit' name='edit' value='EditQuestion'>
    html += '''
    <input type='submit' name='new' value='NewQuestion'>
</form>'''

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
                    if user.currenttask == taskpoint:
                        usercount += 1
                    if user.currenttask.startswith(taskpoint):
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
                if user.currenttask.startswith(point):
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
    request.globaldata = getgraphdata(request)

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
        user = RaippaUser(request, encode(request.form["user"][0]))
        for point, coursepoint in course.flow:
            if isinstance(point, FlowPage):
                task = list()
                successdict = dict()
                for question, taskpoint in point.flow:
                    if question != "start":
                        successdict[question.pagename] = [0,0]
                        if question.pagename not in task:
                            task.append(question.pagename)
                        for useranswer in question.gethistories():
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
        question.answers = question.getanswers()
        html = unicode()
        if request.form.has_key('user'):
            user = RaippaUser(request, encode(request.form["user"][0]))
            html += "%s: %s<br>" % (question.pagename, question.question)
            for answer in question.answers:
                html += "%s: %s tip: %s<br>" % (question.answers[answer][0], answer, question.answers[answer][1])
            html += "<br>%s's(%s) answer history:" % (user.name, user.id)
            for useranswer in question.gethistories():
                if useranswer[3] == course.pagename and useranswer[0] == user.id:
                    html += "<br>overal: %s, " % useranswer[1]
                    print useranswer
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
            for user, overallvalue, valuedict, course, task in question.gethistories():
                if overallvalue == "False":
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
