import random

from MoinMoin import wikiutil
from MoinMoin.Page import Page

from graphingwiki.editing import getmetas
from graphingwiki.editing import edit_meta
from graphingwiki.editing import getkeys
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input
from graphingwiki.patterns import GraphData
from graphingwiki.patterns import encode

coursecategory = u'CategoryCourse'
coursepointcategory = u'CategoryCoursepoint'
taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
failurecategory = u'CategoryFailure'
answercategory = u'CategoryAnswer'
tipcategory = u'CategoryTip'
historycategory = u'CategoryHistory'
statuscategory = u'CategoryStatus'

class FlowPage:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = encode(pagename)
        self.course, self.coursepoint, self.task = self.readstatus()

        globaldata = GraphData(request)
        metas = getmetas(request, globaldata, self.pagename, [u'WikiCategory', u'type'], checkAccess=False)
        globaldata.closedb()
        self.categories = list()
        for metatuple in metas[u'WikiCategory']:
            self.categories.append(metatuple[0])

        if metas[u'type']:
            self.type = metas[u'type'][0][0]
        else:
            self.type = None

    def setnextpage(self):
        if coursecategory in self.categories:
            if self.task and self.task != "end":
                return self.coursepoint, self.task
            elif self.coursepoint and self.coursepoint != "end":
                courseflowpoint = FlowPage(self.request, self.coursepoint)
                nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                return nextcoursepoint, nexttask
            else:
                globaldata = GraphData(self.request)
                metas = getmetas(self.request, globaldata, self.pagename, ["start"], checkAccess=False)
                globaldata.closedb()
                if metas["start"]:
                    courseflowpoint = FlowPage(self.request, metas["start"][0][0])
                    nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                    return nextcoursepoint, nexttask
                else:
                    return False, False
        elif coursepointcategory in self.categories:
            globaldata = GraphData(self.request)
            metas = getmetas(self.request, globaldata, self.pagename, ["task", "next"], checkAccess=False)
            globaldata.closedb()
            if metas["task"]:
                task = metas["task"][0][0]
                page = Page(self.request, self.task)
                taskparent = page.getParentPage()
                if taskparent:
                    taskparent = taskparent.page_name
                if task == self.task or task == taskparent:
                    if metas["next"]:
                        nextcoursepoint = metas["next"][0][0]
                        if nextcoursepoint != "end":
                            courseflowpoint = FlowPage(self.request, nextcoursepoint)
                            nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                            return nextcoursepoint, nexttask
                        else:
                            self.writestatus("end", "end")
                            return "end", "end"
                else:
                    self.writestatus(self.pagename, task)
                    return self.pagename, task
            return False, False
        elif taskcategory in self.categories:
            globaldata = GraphData(self.request)
            metas = getmetas(self.request, globaldata, self.pagename, ["start"], checkAccess=False)
            globaldata.closedb()
            if metas["start"]:
                self.writestatus(self.coursepoint, metas["start"][0][0])
                return self.coursepoint, metas["start"][0][0]
            else:
                return False, False
        elif taskpointcategory in self.categories:
            globaldata = GraphData(self.request)
            metas = getmetas(self.request, globaldata, self.pagename, ["next"], checkAccess=False)
            globaldata.closedb()
            if metas["next"]:
                nextpage = metas["next"][0][0]
                if nextpage != "end":
                    self.writestatus(self.coursepoint, nextpage)
                    return self.coursepoint, nextpage
                else:
                    if self.coursepoint.endswith("failure"):
                        statuspage = self.request.user.name + "/status"
                        input = order_meta_input(self.request, statuspage, {self.coursepoint: [" "]}, "repl")
                        process_edit(self.request, input, True, {statuspage:[statuscategory]})
                        coursepage = FlowPage(self.request, self.course)
                        return coursepage.coursepoint, coursepage.task
                    else:
                        courseflowpoint  = FlowPage(self.request, self.coursepoint)
                        nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                        self.writestatus(self.coursepoint, "end")
                        return nextcoursepoint, nexttask
                return False, False
        else:
            self.request.write(u'%s has no category.' % self.pagename)
            return False, False

    def writestatus(self, flowpoint, task):
        flowpoint = encode(flowpoint)
        task = encode(task)
        statuspage = encode(self.request.user.name + "/status")

        #can't use process_edit repl here because no read rights
        globaldata = GraphData(self.request)
        metakeys = getkeys(globaldata, statuspage)
        globaldata.closedb()

        oldmetas = dict()
        newmetas = dict()

        newmetas[self.course] = [addlink(flowpoint)]
        if metakeys.has_key(self.course):
            oldmetas[self.course] = [addlink(self.coursepoint)]
        else:
            oldmetas[u''] = [u'']

        if flowpoint != u'end' and task != u'end':
            newmetas[flowpoint] = [addlink(task)]
            if metakeys.has_key(flowpoint):
                globaldata = GraphData(self.request)
                meta = getmetas(self.request, globaldata, statuspage, [flowpoint], checkAccess=False)
                oldtask = encode(meta[flowpoint][0][0])
                globaldata.closedb()
                oldmetas[flowpoint] = [addlink(oldtask)]
            else:
                oldmetas[u''] = [u'']
        else:
            newmetas[self.coursepoint] = [addlink(task)]
            if metakeys.has_key(self.coursepoint):
                globaldata = GraphData(self.request)
                meta = getmetas(self.request, globaldata, statuspage, [self.coursepoint], checkAccess=False)
                oldtask = encode(meta[self.coursepoint][0][0])
                globaldata.closedb()
                oldmetas[self.coursepoint] = [addlink(oldtask)]
            else:
                oldmetas[u''] = [u'']
        edit_meta(self.request, statuspage, oldmetas, newmetas, True, [statuscategory])

    def readstatus(self):
        course = str()
        flowpoint = str()
        task = str()
        statuspage = encode(self.request.user.name + "/status")

        globaldata = GraphData(self.request)
        try:
            metas = getmetas(self.request, globaldata, statuspage, ["current"], checkAccess=False)
            course = encode(metas["current"][0][0])
            failure = course + "failure"

            metas = getmetas(self.request, globaldata, statuspage, [course, failure], checkAccess=False)
            if metas[failure]:
                flowpoint = failure
            else:
                flowpoint = encode(metas[course][0][0])

            if flowpoint == "end":
                task = "end"
            else:
                metas = getmetas(self.request, globaldata, statuspage, [flowpoint], checkAccess=False)
                task = encode(metas[flowpoint][0][0])

            globaldata.closedb()
        except:
            globaldata.closedb()
    
        return course, flowpoint, task

    def getquestionpage(self):
        globaldata = GraphData(self.request)
        meta = getmetas(self.request, globaldata, self.pagename, [u'question'], checkAccess=False)
        globaldata.closedb()
        if meta[u'question']:
            return encode(meta[u'question'][0][0])
        else:
            return None

    def gettaskflow(self):
        if taskcategory in self.categories:
            globaldata = GraphData(self.request)
            meta = getmetas(self.request, globaldata, self.pagename, [u'start'], checkAccess=False)
            taskpoint = encode(meta[u'start'][0][0])
            flow = list()

            while taskpoint != u'end':
                meta = getmetas(self.request, globaldata, taskpoint, [u'question', u'next'], checkAccess=False)
                questionpage = encode(meta[u'question'][0][0])
                flow.append((questionpage, taskpoint))
                taskpoint = encode(meta[u'next'][0][0])
            globaldata.closedb()
            return flow
        else:
            return False


class QuestionPage:

    def __init__(self, request, pagename, coursename, task):
        self.request = request
        self.pagename = pagename
        self.course = coursename
        self.task = task

        globaldata = GraphData(request)
        meta = getmetas(request, globaldata, self.pagename, [u'answertype'], checkAccess=False)
        globaldata.closedb()
        self.answertype = meta[u'answertype'][0][0]

    def getanswerdict(self):
        globaldata = GraphData(self.request)
        questionpage = globaldata.getpage(self.pagename)
        try:
            linking_in_question = questionpage.get('in', {})
            pagelist = linking_in_question['question']
            answerdict = dict()
            for page in pagelist:
                metas = getmetas(self.request, globaldata, page, [u'WikiCategory', u'true', u'false'], checkAccess=False)
                for metatuple in metas[u'WikiCategory']:
                    if metatuple[0] == answercategory:
                        tip = None
                        if metas[u'true']:
                            value = u'true'
                            answer = metas[u'true'][0][0]
                        else:
                            value = u'false'
                            answer = metas[u'false'][0][0]
                            answerpage = globaldata.getpage(page)
                            try:
                                linking_in_answer = answerpage.get('in', {})
                                tiplist = linking_in_answer['answer']
                                for tippage in tiplist:
                                    meta = getmetas(self.request, globaldata, tippage, [u'WikiCategory', u'tip'], checkAccess=False)
                                    for metatuple in meta[u'WikiCategory']:
                                        if metatuple[0] == tipcategory:
                                            tip = meta["tip"][0][0]
                                            break
                            except:
                                pass
                        answerdict[answer] = [value, tip]
                        break
            globaldata.closedb()
            return answerdict
        except:
            globaldata.closedb()
            return {}

    def checkanswers(self, useranswers):
        successdict = dict()
        tips = list()
        truelist = list()
        overalvalue = True
        answerdict = self.getanswerdict()

        for answer in answerdict:
            if answerdict[answer][0] == u'true':
                truelist.append(answer)

        for answer in useranswers:
            if answer in truelist:
                truelist.remove(answer)
                successdict[answer] = u'true'
            else:
                successdict[answer] = u'false'
                if answerdict.get(answer, [u'', u''])[1]:
                    tips.append(answerdict[answer][1])
                else:
                    tips.append(u'This is generic tip. Et vaan osaa!')

        #make sure that all the correct answers are selected
        if self.answertype == u'checkbox' and len(truelist) > 0:
            overalvalue = False

        if u'false' in successdict.values():
            overalvalue = False
        
        return overalvalue, successdict, tips

    def writehistory(self, overalvalue, successdict):
        historypage = randompage(self.request, "History")
        historydata = {u'user':[addlink(self.request.user.name)],
                       u'course':[addlink(self.course)],
                       u'task':[addlink(self.task)],
                       u'question':[addlink(self.pagename)],
                       u'overalvalue':[unicode(overalvalue)]}

        for useranswer, value in successdict.iteritems():
            if not historydata.has_key(value):
                historydata[value] = list()
            historydata[value].append(useranswer)

        input = order_meta_input(self.request, historypage, historydata, "add")
        process_edit(self.request, input, True, {historypage:[historycategory]})

def randompage(request, type):
    pagename = "%s/%i" % (type, random.randint(10000,99999))
    page = Page(request, pagename)
    while page.exists():
        pagename = "%s/%i" % (type, random.randint(10000,99999))
        page = Page(request, pagename)

    return pagename

def addlink(pagename):
    return '[['+pagename+']]'

def redirect(request, pagename, tip=None):
    request.http_redirect(request.getBaseURL() + "/" + pagename)
    if tip:
        pass

def execute(pagename, request):

    if request.form.has_key(u'selectcourse'):
        coursename = request.form.get(u'course', [u''])[0]
        if coursename:
            currentpage = FlowPage(request, pagename)
            statuspage = encode(request.user.name + "/status")
            #can't use process_edit repl here because no read rights
            globaldata = GraphData(request)
            metakeys = getkeys(globaldata, statuspage)
            globaldata.closedb()
            if metakeys.has_key(u'current'):
                edit_meta(request, statuspage, {u'current': [addlink(currentpage.course)]}, {u'current': [addlink(coursename)]})
            else:
                edit_meta(request, statuspage, {u'': [u'']}, {u'current': [addlink(coursename)]})
            redirect(request, coursename)
        else:
            request.write(u'Missing course name.')
    elif request.form.has_key(u'start'):
        currentpage = FlowPage(request, pagename)
        fp, task = currentpage.setnextpage()
        redirect(request, task)
    elif request.form.has_key(u'send'):
        currentpage = FlowPage(request, pagename)
        if taskcategory in currentpage.categories and (currentpage.type == u'exam' or currentpage.type == u'questionary'):
            useranswers = dict()
            taskflow = currentpage.gettaskflow()
            for key in request.form:
                if key.startswith('answer'):
                    useranswers[int(key[6:])] = request.form[key]
            if len(useranswers) != len(taskflow) and currentpage.type == u'questionary':
                redirect(request, currentpage.pagename, "You should answer all the questions.")
            else:
                #let's mark user to the first taskpoint
                taskpage = FlowPage(request, taskflow[0][1])
                nextflowpoint, nexttask = taskpage.setnextpage()
                for index, page_tuple in enumerate(taskflow):
                    if useranswers.get(index, None):
                        questionpage = QuestionPage(request, page_tuple[0], currentpage.course, page_tuple[1])
                        overalvalue, successdict, tips = questionpage.checkanswers(useranswers[index])
                        questionpage.writehistory(overalvalue, successdict)
                    if nextflowpoint != "end" and nexttask != "end" and nextflowpoint == currentpage.coursepoint:
                        taskpage = FlowPage(request, page_tuple[1])
                        nextflowpoint, nexttask = taskpage.setnextpage()
                if nextflowpoint == "end" and nexttask == "end":
                    redirect(request, currentpage.course)
                else:
                    redirect(request, nexttask)
        elif taskpointcategory in currentpage.categories:
            if request.form.has_key(u'answer'):
                useranswers = request.form[u'answer']
                questionpage = currentpage.getquestionpage()
                if questionpage:
                    questionpage = QuestionPage(request, questionpage, currentpage.course, currentpage.task)
                    overalvalue, successdict, tips = questionpage.checkanswers(useranswers)
                    questionpage.writehistory(overalvalue, successdict)
                    if overalvalue:
                        nextflowpoint, nexttask = currentpage.setnextpage()
                        if nextflowpoint == "end" and nexttask == "end":
                            redirect(request, currentpage.course)
                        else:
                            redirect(request, nexttask)
                    else:
                        globaldata = GraphData(request)
                        try:
                            metas = getmetas(request, globaldata, currentpage.pagename, [u'failure'], checkAccess=False)
                            failurepage = metas["failed"][0][0]
                            failurekey = currentpage.course + "failure"
                            statuspage = request.user.name + "/status"
                            input = order_meta_input(request, statuspage, {failurekey: [failurepage]}, "repl")
                            process_edit(request, input, True, {statuspage:[statuscategory]})
                        except:
                            failurepage = currentpage.pagename

                        globaldata.closedb()
                        redirect(request, failurepage, tips[0])
                else:
                    request.write(u'Cannot find questionpage.')
            else:
                redirect(request, currentpage.pagename, "You should answer the question.")
        else:
            request.write(u'Invalid input.')
    else:
        request.write(u'Invalid input.')
