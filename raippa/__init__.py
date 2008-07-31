import random
import time
import os

from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin.Page import Page
from MoinMoin.action.AttachFile import getAttachDir

from graphingwiki.editing import getmetas
from graphingwiki.editing import edit_meta
from graphingwiki.editing import getkeys
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input
from graphingwiki.patterns import GraphData
from graphingwiki.patterns import getgraphdata
from graphingwiki.patterns import encode

statuscategory = u'CategoryStatus'
coursecategory = u'CategoryCourse'
coursepointcategory = u'CategoryCoursepoint'
taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
historycategory = u'CategoryHistory'
answercategory = u'CategoryAnswer'
tipcategory = u'CategoryTip'
timetrackcategory = u'CategoryTimetrack'

class RaippaUser:
    def __init__(self, request, id=None):
        self.request = request

        if id:
            self.id = encode(id)
        else:
            self.id = encode(self.request.user.name)

        self.name = unicode()
        globaldata = GraphData(self.request)
        namemeta = getmetas(request, globaldata, encode(self.id), ["name"])
        for name, type in namemeta["name"]:
            self.name = name
            break
            
        self.statuspage = encode("%s/status" % self.id)
                
        self.statusdict = globaldata.getpage(self.statuspage).get('lit', {})
        self.currentcourse = removelink(self.statusdict.get("current", [""])[0])
        self.currentcoursepoint = removelink(self.statusdict.get(self.currentcourse, [""])[0])
        self.currenttask = removelink(self.statusdict.get(self.currentcoursepoint, [""])[0])
        globaldata.closedb()

    def getcourselist(self):
        courselist = list()
        globaldata = GraphData(self.request)
        metakeys = getkeys(globaldata, self.statuspage)
        for key in metakeys:
            categorymetas = getmetas(self.request, globaldata, key, ["WikiCategory"])
            for category, type in categorymetas["WikiCategory"]:
                if category == coursecategory:
                    courselist.append(key)
                    break
        globaldata.closedb()
        return courselist

    def gettimetrack(self, course):
        globaldata = GraphData(self.request)
        page = globaldata.getpage(self.id)
        linking_in = page.get('in', {}) 
        pagelist = linking_in.get("user", [])
        timetracklist = dict()
        for page in pagelist:
            metas = getmetas(self.request, globaldata, page, ["course", "WikiCategory", "hours", "description", "time"], checkAccess=False)
            if metas["course"]:
                if course == metas["course"][0][0]:
                    for category, type in metas["WikiCategory"]:
                        if category == timetrackcategory:
                            if metas["time"] and metas["hours"]:
                                time = metas["time"][0][0]
                                hours = metas["hours"][0][0]
                                if metas["description"]:
                                    description = metas["description"][0][0]
                                else:
                                    description = unicode()
                    
                                timetracklist[time] = [hours, description]
                            break
        return timetracklist

    def canDo(self, pagename, course):
        page = FlowPage(self.request, pagename)
        may = False
        if "[[end]]" in self.statusdict.get(page.pagename, []):
            return False
        elif coursepointcategory in page.categories:
            prerequisites = page.getprerequisite()
            for prequisite in prerequisites:
                 if not self.hasDone(prequisite, course):
                     return False
            course = FlowPage(self.request, course)
            flow = course.getflow()
            prelist = list()
            for point, nextlist in flow.iteritems():
                if page.pagename in nextlist:
                    prelist.append(point)
                    if point == "start":
                        may = True
                        continue
                    statuslist = self.statusdict.get(point, [])
                    if "[[end]]" in statuslist:
                        may = True
        return may

    def hasDone(self, pagename, course=None):
        page = FlowPage(self.request, pagename)
        globaldata = GraphData(self.request)
        lasttaskpoint = encode(page.getflow().pop()[0])
        lasttaskpoint = globaldata.getpage(lasttaskpoint)
        linking_in = lasttaskpoint.get('in', {})
        pagelist = linking_in.get("task", [])
        for page in pagelist:
            globaldata = GraphData(self.request)
            metas = getmetas(self.request, globaldata, encode(page), ["WikiCategory", "user", "overallvalue"], checkAccess=False)
            globaldata.closedb()
            if metas["user"] and metas["overallvalue"]:
                for category, type in metas["WikiCategory"]:
                    if category == historycategory and metas["user"][0][0] == self.id:
                        return True
        return False

    def updatestatus(self, newstatusdict=None):
        if newstatusdict:
            for key in newstatusdict:
                self.statusdict[key] = newstatusdict[key]
        else:
            globaldata = GraphData(self.request)
            statuspage = self.request.globaldata.getpage(self.statuspage)
            globaldata.closedb()
            self.statusdict = statuspage.get('lit', {})

        self.currentcourse = removelink(self.statusdict.get("current", [""])[0])
        self.currentcoursepoint = removelink(self.statusdict.get(self.currentcourse, [""])[0])
        self.currenttask = removelink(self.statusdict.get(self.currentcoursepoint, [""])[0])

    def editstatus(self, flowpoint, task, debug=None):
        #print debug, flowpoint, task
        flowpoint = encode(flowpoint)
        task = encode(task)

        globaldata = GraphData(self.request)
        metakeys = getkeys(globaldata, self.statuspage)

        oldmetas = dict()
        newmetas = dict()

        newmetas[self.currentcourse] = [addlink(flowpoint)]
        if metakeys.has_key(self.currentcourse):
            oldmetas[self.currentcourse] = [addlink(self.currentcoursepoint)]
        else:
            oldmetas[u''] = [u'']


        if flowpoint != u'end' and task != u'end':
            newmetas[flowpoint] = [addlink(task)]
            if metakeys.has_key(flowpoint):
                meta = getmetas(self.request, globaldata, self.statuspage, [flowpoint], checkAccess=False)
                oldtask = encode(meta[flowpoint][0][0])
                oldmetas[flowpoint] = [addlink(oldtask)]
            else:
                oldmetas[u''] = [u'']
        else:
            newmetas[self.currentcoursepoint] = [addlink(task)]
            if metakeys.has_key(self.currentcoursepoint):
                meta = getmetas(self.request, globaldata, self.statuspage, [self.currentcoursepoint], checkAccess=False)
                oldtask = encode(meta[self.currentcoursepoint][0][0])
                oldmetas[self.currentcoursepoint] = [addlink(oldtask)]
            else:
                oldmetas[u''] = [u'']
        msg = edit_meta(self.request, self.statuspage, oldmetas, newmetas, True, [statuscategory])
        self.updatestatus(newmetas)


class FlowPage:
    def __init__(self, request, pagename, user=None):
        self.request = request
        self.pagename = encode(pagename)
        if user:
            self.user = user
        
        globaldata = GraphData(self.request)
        metas = getmetas(request, globaldata, self.pagename, ["WikiCategory", "type", "next", "start"], checkAccess=False)
        globaldata.closedb()
        self.categories = list()
        for category, type in metas[u'WikiCategory']:
            self.categories.append(category)
            
        self.startlist = list()
        for start, type in metas["start"]:
            self.startlist.append(start)
            
        self.nextlist = list()
        for next, type in metas["next"]:
            self.nextlist.append(next)

        if metas[u'type']:
            self.type = metas[u'type'][0][0]
        else:
            self.type = None

    def setnextpage(self, userselection=None):
        if coursecategory in self.categories:
            if userselection in self.startlist:
                courseflowpoint = FlowPage(self.request, userselection, self.user)
                nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                return nextcoursepoint, nexttask
            elif self.user.currenttask and self.user.currenttask != "end":
                return self.user.currentcoursepoint, self.user.currenttask
            elif self.user.currentcoursepoint and self.user.currentcoursepoint != "end":
                courseflowpoint = FlowPage(self.request, self.user.currentcoursepoint, self.user)
                nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                return nextcoursepoint, nexttask
            else:
                globaldata = GraphData(self.request)
                metas = getmetas(self.request, globaldata, self.pagename, ["start"], checkAccess=False)
                globaldata.closedb()

                if metas["start"]:
                    courseflowpoint = FlowPage(self.request, metas["start"][0][0], self.user)
                    nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                    return nextcoursepoint, nexttask
                else:
                    return False, False
        elif coursepointcategory in self.categories:
            temp = removelink(self.user.statusdict.get(self.pagename, [""])[0])
            if temp:
                if temp == "end":
                    if not "end" in self.nextlist:
                        next = random.choice(self.nextlist)
                        for key in self.user.statusdict:
                            if key in self.nextlist:
                                next = key
                                break
                        courseflowpoint = FlowPage(self.request, next, self.user)
                        nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                        return nextcoursepoint, nexttask
                    else:
                        return "end", "end"
                else:
                    self.user.editstatus(self.pagename, temp, 2)
                    return self.pagename, temp
            else:
                globaldata = GraphData(self.request)
                metas = getmetas(self.request, globaldata, self.pagename, ["task"], checkAccess=False)
                globaldata.closedb()
                self.user.editstatus(self.pagename, metas["task"][0][0], 3)
                return self.pagename, metas["task"][0][0]
        elif taskcategory in self.categories:
            globaldata = GraphData(self.request)
            metas = getmetas(self.request, globaldata, self.pagename, ["start"], checkAccess=False)
            globaldata.closedb()
            if metas["start"]:
                start = random.choice(metas["start"])[0]
                self.user.editstatus(self.user.currentcoursepoint, start, 4)
                return self.user.currentcoursepoint, start
            else:
                return False, False
        elif taskpointcategory in self.categories:
            globaldata = GraphData(self.request)
            metas = getmetas(self.request, globaldata, self.pagename, ["next"], checkAccess=False)
            globaldata.closedb()
            if metas["next"]:
                nextpage = random.choice(metas["next"])[0]
                if nextpage != "end":
                    self.user.editstatus(self.user.currentcoursepoint, nextpage, 5)
                    return self.user.currentcoursepoint, nextpage
                else:
                    if self.user.currentcoursepoint.endswith("failure"):
                        #TODO change to penalty
                        statuspage = self.request.user.name + "/status"
                        input = order_meta_input(self.request, statuspage, {self.user.currentcoursepoint: [" "]}, "repl")
                        process_edit(self.request, input, True, {statuspage:[statuscategory]})
                        coursepage = FlowPage(self.request, self.course, self.user)
                        return coursepage.coursepoint, coursepage.task
                    else:
                        self.user.editstatus(self.user.currentcoursepoint, "end", 6)
                        courseflowpoint  = FlowPage(self.request, self.user.currentcoursepoint, self.user)
                        nextcoursepoint, nexttask = courseflowpoint.setnextpage()
                        return nextcoursepoint, nexttask
                return False, False
        else:
            self.request.write(u'%s has no category.' % self.pagename)
            return False, False

    def getprerequisite(self):
        if not coursepointcategory in self.categories:
            return []
        else:
            globaldata = GraphData(self.request)
            meta = getmetas(self.request, globaldata, self.pagename, ["prerequisite"], checkAccess=False)
            globaldata.closedb()
            prerequisites = list()
            for prerequisite, type in meta["prerequisite"]:
                prerequisites.append(prerequisite)
            return prerequisites

    def getquestionpage(self):
        globaldata = GraphData(self.request)
        meta = getmetas(self.request, globaldata, self.pagename, [u'question'], checkAccess=False)
        globaldata.closedb()
        if meta[u'question']:
            return encode(meta[u'question'][0][0])
        else:
            return None

    def getflow(self):
        globaldata = GraphData(self.request)
        if coursecategory in self.categories:
            flow = dict()
            def subflow(page):
                meta = getmetas(self.request, globaldata, page, ["next"], checkAccess=False)
                for next, type in meta["next"]:
                    next = encode(next)
                    if page not in flow.keys():
                        flow[page] = list()
                    if next not in flow[page]:
                        flow[page].append(next)
                    if next != "end":
                        subflow(next)
                    
            meta = getmetas(self.request, globaldata, self.pagename, ["start"], checkAccess=False)
            for start, type in meta["start"]:
                start = encode(start)
                if "start" not in flow.keys():
                    flow["start"] = []
                if start not in flow["start"]:
                    flow["start"].append(start)
                subflow(start)
        elif taskcategory in self.categories:
            #if self.type == "exam" or self.type == "questionary":
            meta = getmetas(self.request, globaldata, self.pagename, ["start"], checkAccess=False)
            taskpoint = encode(meta["start"][0][0])
            flow = list()
            while taskpoint != "end":
                meta = getmetas(self.request, globaldata, taskpoint, ["question", "next"], checkAccess=False)
                taskpage = encode(meta["question"][0][0])
                flow.append((taskpoint, taskpage))
                if meta["next"]:
                    taskpoint = encode(meta["next"][0][0])
                else:
                    taskpoint = "end"
        else:
            return False
        globaldata.closedb()
        return flow

class Question:         
    def __init__(self, request, pagename):
        self.pagename = encode(pagename)
        self.request = request
        
        globaldata = GraphData(self.request)
        metas = getmetas(request, globaldata, self.pagename, ["question", "answertype", "note"])                  
        self.question = unicode()
        self.asnwertype = unicode()
        self.note = unicode()

        if metas["question"]:
            self.question = metas["question"][0][0]
        if metas["answertype"]:
            self.answertype = metas["answertype"][0][0]
        if metas["note"]:
            self.note = metas["note"][0][0]

        globaldata.closedb()

    def gethistories(self):
        histories = list()
        globaldata = GraphData(self.request)
        page = globaldata.getpage(self.pagename)
        linking_in = page.get('in', {})
        pagelist = linking_in.get("question", [])
        for page in pagelist:
            metas = getmetas(self.request, globaldata, page, ["WikiCategory", "user", "overallvalue", "false", "true", "course", "task"])
            for category, type in metas["WikiCategory"]:
                if category == historycategory:
                    if metas["user"] and metas["overallvalue"] and metas["course"]:
                        user = metas["user"][0][0]
                        overallvalue = metas["overallvalue"][0][0]
                        course = metas["course"][0][0]
                        if metas["task"]:
                            task = metas["task"][0][0]
                        else:
                            task = unicode()
                        useranswers = dict()
                        for true in metas["true"]:
                            useranswers[true[0]] = "true"
                        for false in metas["false"]:
                            useranswers[false[0]] = "false"
                        histories.append([user, overallvalue, useranswers, course, task])
                    break
        globaldata.closedb()
        return histories

    def getanswers(self):
        globaldata = GraphData(self.request)
        questionpage = globaldata.getpage(self.pagename)
        linking_in_question = questionpage.get('in', {})
        pagelist = linking_in_question.get("question", [])
        answerdict = dict()
        for page in pagelist:
            metas = getmetas(self.request, globaldata, page, ["WikiCategory", "true", "false", "option"], checkAccess=False)
            for category, type in metas["WikiCategory"]:
                if category == answercategory:
                    tip = None
                    options = list()
                    if metas["true"]:
                        value = u'true'
                        answer = metas["true"][0][0]
                    elif metas["false"]:
                        value = u'false'
                        answer = metas["false"][0][0]
                        answerpage = globaldata.getpage(page)
                        try:
                            linking_in_answer = answerpage.get('in', {})
                            tiplist = linking_in_answer["answer"]
                            for tippage in tiplist:
                                meta = getmetas(self.request, globaldata, tippage, ["WikiCategory"], checkAccess=False)
                                for category, type in meta["WikiCategory"]:
                                    if category == tipcategory:
                                        tip = tippage.split("/")[1]
                                        break
                        except:
                            pass
                    if metas["option"]:
                        for option, type in metas["option"]:
                            options.append(option)
                    answerdict[answer] = [value, tip, options]
                    break
        globaldata.closedb()
        return answerdict

    def checkanswers(self, useranswers):
        successdict = dict()
        tips = list()
        truelist = list()
        overallvalue = True
        answerdict = self.getanswers()

        for answer in answerdict:
            if answerdict[answer][0] == "true":
                truelist.append(answer)

        #TODO: regexp, casesensitivity
        for answer in useranswers:
            if answer in truelist:
                truelist.remove(answer)
                successdict[answer] = "true"
            else:
                successdict[answer] = "false"
                if answerdict.get(answer, [u'', u''])[1]:
                    tips.append(answerdict[answer][1])
                else:
                    tips.append("generic")

        #make sure that all the correct answers are selected
        if self.answertype == "checkbox" and len(truelist) > 0:
            overallvalue = False

        if "false" in successdict.values():
            overallvalue = False

        return overallvalue, successdict, tips

    def writehistory(self, user, course, task, overallvalue, successdict, historypage=None):
        if not historypage:
            historypage = randompage(self.request, "History")
        historydata = {u'user':[addlink(user)],
                       u'course':[addlink(course)],
                       u'task':[addlink(task)],
                       u'question':[addlink(self.pagename)],
                       u'overallvalue':[unicode(overallvalue)],
                       u'time':[time.strftime("%Y-%m-%d %H:%M:%S")]}

        for useranswer, value in successdict.iteritems():
            if not historydata.has_key(value):
                historydata[value] = list()
            historydata[value].append(useranswer)

        globaldata = GraphData(self.request)
        edit_meta(self.request, historypage, {u'': [u'']}, historydata, True, [historycategory])
        globaldata.closedb()

    def writefile(self, historypage=None):
        if not historypage:
            historypage = randompage(self.request, "History")
        filename = self.request.form['answer__filename__']
        target = filename
        filecontent = self.request.form['answer'][0]
        if len(target) > 1 and (target[1] == ':' or target[0] == '\\'):
            bsindex = target.rfind('\\')
            if bsindex >= 0:
                target = target[bsindex+1:]
        target = wikiutil.taintfilename(target)
        attach_dir = getAttachDir(self.request, pagename, create=1)
        fpath = os.path.join(attach_dir, target).encode(config.charset)
        exists = os.path.exists(fpath)
        if exists:
            try:
                os.remove(fpath)
            except:
                pass
        stream = open(fpath, 'wb')
        try:
            stream.write(filecontent)
        finally:
            stream.close()

        return pagename


    def getaverage(self, coursename, taskpoint):
        histories = self.gethistories()
        userlist = list()
        answercount = int()
        average = 0
        alltimeuserlist = list()
        alltimeanswercount = len(histories)
        alltimeaverage = 0

        for answer in histories:
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
    if not pagename.startswith("[[") and not pagename.endswith("]]"):
        pagename = '[['+pagename+']]'
    return pagename

def removelink(pagename):
    if pagename.startswith("[[") and pagename.endswith("]]"):
        pagename = pagename[2:-2]
    return encode(pagename)

def randompage(request, type):
    pagename = "%s/%i" % (type, random.randint(10000,99999))
    page = Page(request, pagename)
    while page.exists():
        pagename = "%s/%i" % (type, random.randint(10000,99999))
        page = Page(request, pagename)

    return pagename

