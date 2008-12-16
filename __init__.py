import random
import time

from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import get_metas
from graphingwiki.editing import set_metas
from graphingwiki.editing import get_keys
from graphingwiki.editing import metatable_parseargs

raippacategories = {"statuscategory": "CategoryStatus",
                    "coursecategory": "CategoryCourse",
                    "coursepointcategory": "CategoryCoursepoint",
                    "taskcategory": "CategoryTask",
                    "taskpointcategory": "CategoryTaskpoint",
                    "historycategory": "CategoryHistory",
                    "questioncategory": "CategoryQuestion",
                    "answercategory": "CategoryAnswer",
                    "tipcategory": "CategoryTip",
                    "timetrackcategory": "CategoryTimetrack",
                    "usercategory": "CategoryUser"}

raippagroups = {"teachergroup": "TeacherGroup",
                "quarantinegroup": "QuarantineGroup"}

class RaippaException(Exception):
    def __init__(self, args=str()):
        self.args = args
    def __str__(self):
        return self.args

class RaippaUser:
    def __init__(self, request, user=None):
        self.request = request

        if user:
            self.user = user
            meta = get_metas(request, user, ["name"])
            if meta["name"]:
                self.name = meta["name"]
            else:
                self.name = unicode() 
        else:
            self.user = self.request.user.name
            self.name = self.request.user.aliasname
            if not pageexists(self.request, self.user) and self.name:
                data = {self.user: {"name": [self.name]}}
                result, msg = set_metas(request, dict(), dict(), data)
                if not result:
                    reporterror(request, "failed to write %s to page %s" % (self.name, self.user))

    def isTeacher(self):
        teachergroup = Page(self.request, raippagroups["teachergroup"])
        raw = teachergroup.get_raw_body()

        for line in raw.split("\n"):
            if line.startswith(" * ") and removelink(line[3:].rstrip()) == self.user:
                return True 

        return False

    def isQuarantined(self):
        quarantinegroup = Page(self.request, raippagroups["quarantinegroup"])
        raw = quarantinegroup.get_raw_body()          

        for line in raw.split("\n"):
            if line.startswith(" * ") and removelink(line[3:].rstrip()) == self.user:
                return True 

        return False

    def getcourses(self):
        courselist, keys, s = metatable_parseargs(self.request, raippacategories["coursecategory"], checkAccess=False)

        userscourses = list()
        for coursepage in courselist:
            course = self.request.graphdata.getpage(coursepage)
            linking_in = course.get('in', dict())
            pagelist = linking_in.get("course", list())
            for page in pagelist:
                metas = get_metas(self.request, page, ["gwikicategory", "user"], display=True, checkAccess=False)
                if raippacategories["historycategory"] in metas["gwikicategory"] and self.user in metas["user"]:
                    userscourses.append(coursepage)
                    break
 
        return userscourses

    def canDo(self, page, course):
        _ = self.request.getText

        if not pageexists(self.request, page):
            raise RaippaException(u'The page %s does not exist.' % page)

        categories = get_metas(self.request, page, ["gwikicategory"], checkAccess=False)

        if raippacategories["coursepointcategory"] in categories["gwikicategory"]:
            #can't do if already done except if there is redo taskpoint
            done, reason = self.hasDone(page, course)
            if done:
                if reason == "redo":
                    return True, reason
                else:
                    return False, reason

            keys = ["deadline", "prerequisite"]
            metas = get_metas(self.request, page, keys, display=True, checkAccess=False)
            #can't do if deadline is gone
            if metas["deadline"]:
                try:
                    deadline = time.strptime(metas["deadline"].pop(), "%Y-%m-%d")
                    currentdate = time.gmtime()
                    if (deadline[0] < currentdate[0]) or \
                       (deadline[0] <= currentdate[0] and deadline[1] < currentdate[1]) or \
                       (deadline[0] <= currentdate[0] and deadline[1] <= currentdate[1] and \
                        deadline[2] < currentdate[2]):
                        return False, "deadline"
                except ValueError:
                    reporterror(self.request, "%s has invalid deadline format." % page)

            #can't do if prerequisites are not done
            for prerequisite in metas["prerequisite"]:
                if not pageexists(self.request, prerequisite):
                    raise RaippaException(u"%s linked in %s doesn't exist." % (prerequisite, page))

                done, reason = self.hasDone(prerequisite, course)
                if not done:
                    return False, "prerequisite"

            #if no prerequisites return True
            return True, "noprerequisite"

        elif raippacategories["taskcategory"] in categories["gwikicategory"]:
            #can't do if allready done
            done, reason = self.hasDone(page, course)
            if done:
                if reason == "redo":
                    return True, reason
                else:
                    return False, reason

            #try to find tasks coursepoint
            task = self.request.graphdata.getpage(page)
            linking_in = task.get('in', {})
            pagelist = linking_in.get("task", [])

            for linking_page in pagelist:
                meta = get_metas(self.request, linking_page, ["gwikicategory"], checkAccess=False)
                if raippacategories["coursepointcategory"] in meta["gwikicategory"]:
                    #if we find coursepoint, return coursepoints canDo
                    if linking_page.startswith(course):
                        return self.canDo(linking_page, course)

            raise RaippaException("No coursepoints linking into %s" % page)

        elif raippacategories["taskpointcategory"] in categories["gwikicategory"]:
            #can't do if allready done
            done, reason = self.hasDone(page, course)
            if done:
                if reason == "redo":
                    return True, reason
                else:
                    return False, reason
            else:
                if reason == "recap":
                    return False, reason 
                elif reason == "pending":
                    return True, reason 
                elif reason == "picked": #in ["pending", "picked"]:
                    return False, "picked"

            #find task and tasktype 
            #TODO: parents are evil
            temp = page.split("/")
            temp.pop()
            taskpage = "/".join(temp)

            types = get_metas(self.request, taskpage, ["type"], display=True, checkAccess=False)
            if types["type"]:
                tasktype = types["type"].pop()
            else:
                reporterror(self.request, u"%s doesn't have tasktype." % taskpage)
                tasktype = "basic"

            if tasktype in ["exam", "questionary"] and not done and reason == "False":
                return False, "done"

            if tasktype not in  ["exam", "questionary"]:
                #can do if previous point is done
                taskpoint = self.request.graphdata.getpage(page)
                linking_in = taskpoint.get('in', dict())
                nextlist = linking_in.get("next", list())
                for next in nextlist:
                    meta = get_metas(self.request, next, ["gwikicategory"], checkAccess=False)
                    if raippacategories["taskpointcategory"] in meta["gwikicategory"]:
                        done, reason = self.hasDone(next, course)
                        if done:
                            return True, "previousdone" 
                        else:
                            return False, "previousnot"

            #if no previous taskpoints, return parents canDo
            return self.canDo(taskpage, course)

        raise RaippaException("Invalid category %s" % page)

    def hasDone(self, page, course):
        _ = self.request.getText

        if not pageexists(self.request, page):
            raise RaippaException(u'The page %s does not exist.' % page)

        keys = ["gwikicategory", "task", "start", "option", "question", "type"]
        metas = get_metas(self.request, page, keys, display=True, checkAccess=False)

        categories = metas["gwikicategory"]
        if raippacategories["coursepointcategory"] in categories:
            #find coursepoints task and return tasks hasDone
            if metas["task"]:
                task = metas["task"].pop()
                if not pageexists(self.request, task):
                    raise RaippaException(u"%s linked in %s doesn't exist." % (task, page))
                return self.hasDone(task, course)
            else:
                raise RaippaException(u"%s doesn't have task link." % page)

        elif raippacategories["taskcategory"] in categories:
            #get task type
            if metas["type"]:
                tasktype = metas["type"].pop()
            else:
                tasktype = "basic"
                reporterror(self.request, u"%s doesn't have tasktype.")

            #task is done only if all taskpoints in task are done
            redo = False
            if metas["start"]:
                taskpoint = metas["start"].pop()
            else:
                raise RaippaException(u"%s doesn't have start link." % page)

            while taskpoint != "end":
                if not pageexists(self.request, taskpoint):
                    raise RaippaException(u"%s linked in %s doesn't exist." % (taskpoint, page))

                done, reason = self.hasDone(taskpoint, course)
                if not done:
                    if tasktype in ["exam", "questionary"]:
                        if reason == "nohistory":
                            return False, reason
                    else:
                        return False, reason
                else:
                    if reason == "redo":
                        redo = True

                tpmeta = get_metas(self.request, taskpoint, ["next"], display=True, checkAccess=False)
                if tpmeta["next"]:
                    taskpoint = tpmeta["next"].pop()
                else:
                    raise RaippaException(u"%s doesn't have next link." % taskpoint)

            if redo:
                return True, "redo"
            else:
                return True, "done"

        elif raippacategories["taskpointcategory"] in categories:
            #see if taskpoints question is done
            if metas["question"]:
                questionpage = metas["question"].pop()
                if not pageexists(self.request, questionpage):
                    raise RaippaException(u"%s linked in %s doesn't exist." % (questionpage, page))
            else:
                raise RaippaException(u"%s doesn't have question link." % page)

            history = Question(self.request, questionpage).gethistory(self.user, course)

            if history:
                overallvalue = history[0]
                if overallvalue in ["False", "pending", "picked", "recap"]:
                    return False, overallvalue
                else:
                    if "redo" in metas["option"]:
                        return True, "redo"
                    else:
                        return True, "done"
            return False, "nohistory"

        raise RaippaException("Invalid category %s." % page)


class Question:         
    def __init__(self, request, pagename, init_all=True):
        self.request = request
        self.pagename = pagename

        if not pageexists(self.request, self.pagename):
            raise RaippaException(u'The page %s does not exist.' % self.pagename)

        if init_all:
            keys = ["answertype", "note", "question", "type"]
            metas = get_metas(request, self.pagename, keys, display=True, checkAccess=False)

            if metas["question"]:
                self.question = metas["question"].pop() 
            else:
                self.question = None
                raise RaippaException(u"%s doesn't have question meta." % self.pagename)

            if metas["answertype"]:
                self.answertype = metas["answertype"].pop() 
            else:
                reporterror(request, "%s doesn't have answertype." % self.pagename)
                self.answertype = "text"

            if metas["note"]:
                self. note = metas["note"].pop()
            else:
                self.note = str()

            self.types = metas["type"]

    def gethistory(self, user, course):
        page = self.request.graphdata.getpage(self.pagename)
        linking_in = page.get('in', {})
        pagelist = linking_in.get("question", [])

        for temp in pagelist:
            categories = get_metas(self.request, temp, ["gwikicategory"], checkAccess=False)

            if raippacategories["historycategory"] in categories["gwikicategory"]:
                keys = ["user", "course", "overallvalue", "task", "true", "false"]
                metas = get_metas(self.request, temp, keys, display=True, checkAccess=False)

                if not metas["user"]:
                    reporterror(self.request, "%s doesn't have user meta." % temp)
                    continue

                if not metas["overallvalue"]:
                    continue
                    reporterror(self.request, "%s doesn't have overallvalue meta." % temp)

                if user in metas["user"] and course in metas["course"]:
                    overallvalue = metas["overallvalue"].pop()

                    if metas["task"]:
                        task = metas["task"].pop()
                    else:
                        task = unicode()

                    useranswers = dict()
                    for true in metas["true"]:
                        useranswers[true] = "true"
                    for false in metas["false"]:
                        useranswers[false] = "false"

                    return [overallvalue, useranswers, task, temp]

        return False

    def gethistories(self, coursefilter=None, taskfilter=None, userfilter=None):
        histories = list()

        page = self.request.graphdata.getpage(self.pagename)
        linking_in = page.get('in', {})
        pagelist = linking_in.get("question", [])

        for page in pagelist:
            keys = ["gwikicategory", "task", "user", "course", "overallvalue", "true", "false"]
            metas = get_metas(request, node, keys, display=True, checkAccess=False)

            categories = metas["gwikicategory"]

            if raippacategories["historycategory"] in categories:
                tasks = metas["task"] 
                if not tasks or (taskfilter and taskfilter not in tasks):
                    continue

                users = metas["user"]
                if not users or (userfilter and userfilter not in users):
                    continue

                courses = metas["course"]
                if not courses or (coursefilter and coursefilter not in courses):
                    continue

                if metas["overallvalue"]:
                    overallvalue = metas["overallvalue"].pop()
                else:
                    reporterror(self.request, "%s doesn't have overallvalue." % node)
                    overallvalue = "False"

                if metas["task"]:
                    task = metas["task"].pop()
                else:
                    task = unicode()
                
                useranswers = dict()
                for true in metas["true"]:
                    useranswers[true] = "true"
                for false in metas["false"]:
                    useranswers[false] = "false"
                
                course = courses.pop()
                user = users.pop()
                histories.append([user, overallvalue, useranswers, course, task, page])

        return histories

    def getanswers(self):
        #NOTE: this might get slow when lot of links to question
        questionpage = self.request.graphdata.getpage(self.pagename)
        linking_in_question = questionpage.get('in', {})
        pagelist = linking_in_question.get("question", [])
        answerdict = dict()
        for page in pagelist:
            keys = ["gwikicategory", "true", "false", "option"]
            metas = get_metas(self.request, page, keys, display=True, checkAccess=False)
            if raippacategories["answercategory"] in metas["gwikicategory"]:
                if metas["true"]:
                    value = u'true'
                    answer = metas["true"].pop()
                    if answer.startswith("mailto:"):
                        answer = answer[7:]
                elif metas["false"]:
                    value = u'false'
                    answer = metas["false"].pop()
                    if answer.startswith("mailto:"):
                        answer = answer[7:]

                answerpage = self.request.graphdata.getpage(page)
                tip = None
                try:
                    linking_in_answer = answerpage.get('in', {})
                    tiplist = linking_in_answer["answer"]
                    for tippage in tiplist:
                        meta = get_metas(self.request, tippage, ["gwikicategory"], checkAccess=False)
                        if raippacategories["tipcategory"] in meta["gwikicategory"]:
                            tip = tippage
                            break
                except:
                    pass

                answerdict[answer] = [value, tip, metas["option"], page]
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
                if answerdict.get(answer, [u'', u''])[1]:        
                    tips.append(answerdict[answer][1])
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

    def writehistory(self, users, course, task, overallvalue, successdict, file=False):
        _ = self.request.getText

        for user in users:
            history = self.gethistory(user, course)
            if history:
                historypage = history[3]
                oldkeys = get_keys(self.request, historypage).keys()
                remove = {historypage: oldkeys}
                break
        else:
            historypage = randompage(self.request, "History")
            remove = dict()

        linked_users = list()
        for user in users:
            linked_users.append(addlink(user))

        historydata = {"user": linked_users,
                       "course": [addlink(course)],
                       "task": [addlink(task)],
                       "question": [addlink(self.pagename)],
                       "overallvalue": [unicode(overallvalue)],
                       "useragent": [self.request.getUserAgent()],
                       "time": [time.strftime("%Y-%m-%d %H:%M:%S")],
                       "gwikicategory": [raippacategories["historycategory"]]}

        if overallvalue == "recap":
            meta = get_metas(self.request, task, ["recap"], checkAccess=False)
            if meta["recap"]:
                historydata["recap"] = meta["recap"]

        if file:
            filename = unicode()
            if self.request.form.has_key('answer__filename__'):
                filename = self.request.form.get('answer__filename__', unicode())
            filecontent = self.request.form.get("answer", [str()]).pop()

            from mod_python import util
            if isinstance(filecontent, util.Field):
                content = filecontent.value
                filecontent = content
            elif not isinstance(filecontent, str):
                temp = filecontent.read()
                filecontent = temp
            filecontent = unicode(filecontent, 'iso-8859-15')
            
            if filename.endswith(".py"):
                filecontent = "#FORMAT python\n"+filecontent
            elif filename.endswith(".c") or filename.endswith(".cpp"):
                filecontent = "#FORMAT cplusplus\n"+filecontent
            else:
                filecontent = "#FORMAT plain\n"+filecontent

            filepage = PageEditor(self.request, historypage+"/file")
            try:
                msg = filepage.saveText(filecontent, filepage.get_real_rev())
                if msg != _("Thank you for your changes. Your attention to detail is appreciated."):
                    return False
            except filepage.Unchanged:
                pass
            except:
                return False
            historydata[u'file'] = [addlink(historypage+"/file")]
            historydata[u'filename'] = [filename]

        for useranswer, value in successdict.iteritems():
            if not historydata.has_key(value):
                historydata[value] = list()
            historydata[value].append(useranswer)

        historydata = {historypage: historydata}

        result, msg = set_metas(self.request, remove, dict(), historydata)
        if result:
            return historypage
        else:
            return False

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
    return pagename

def randompage(request, type):
    while True:
        pagename = "%s/%i" % (type, random.randint(10000,99999))
        if not pageexists(request, pagename):
            return pagename

def revert(request, pagename, rev):
    _ = request.getText
    try:
        current = PageEditor(request, pagename)
        if current.get_real_rev() > rev:
            old = Page(request, pagename, rev=rev)
            revstr = '%08d' % rev
            msg = current.saveText(old.get_raw_body(), 0, extra=revstr, action="SAVE/REVERT")
            if msg == _("Thank you for your changes. Your attention to detail is appreciated."):
                return True
        return False
    except page.Unchanged:
        return True
    except:
        return False

def reporterror(request, note, priority=None):
    page = PageEditor(request, "ErrorPage")
    note = " * %s" % note
    body = page.get_raw_body()
    if note not in body:
        page.saveText(body + "\n%s" % note, page.get_real_rev())

def pageexists(request, pagename):
    pagename = removelink(pagename)
    content = Page(request, pagename).get_raw_body()
    if not content:
        return False
    else:
        return True

def getflow(request, pagename):
    keys = ["gwikicategory", "start", "task"]
    metas = get_metas(request, pagename, keys, display=True, checkAccess=False)

    categories = metas["gwikicategory"]

    if raippacategories["coursecategory"] in categories:
        flow = {"start":list()}

        def subflow(current):
            if current not in flow.keys():
                if not pageexists(request, current):
                    raise RaippaException(u'The page %s does not exist.' % current) 
                flow[current] = list()

            metanext = get_metas(request, current, ["next"], display=True, checkAccess=False)
            if not metanext["next"]:
                raise RaippaException(u"%s doesn't have next link." % current)
                
            for next in metanext["next"]:
                if next not in flow[current]:
                    flow[current].append(next)
                if next != "end":
                    subflow(next)
        
        if not metas["start"]:
            raise RaippaException(u"%s doesn't have start link." % pagename)

        for start in metas["start"]:
            if start not in flow["start"]:
                flow["start"].append(start)
            subflow(start)

        return flow

    elif raippacategories["coursepointcategory"] in categories:
        if metas["task"]:
            taskpage = metas["task"].pop()
            if not pageexists(request, taskpage):
                raise RaippaException(u"%s linked in %s doesn't exist." % (taskpage, pagename))
        else:
            raise RaippaException(u"%s doesn't have task link." % pagename)

        return getflow(request, taskpage)

    elif raippacategories["taskcategory"] in categories:
        flow = list()
        if metas["start"]:
            taskpoint = metas["start"].pop()
            if not pageexists(request, taskpoint):
                raise RaippaException(u"%s linked in %s doesn't exist." % (taskpoint, pagename))
        else:
            raise RaippaException(u"%s doesn't have start link." % pagename)

        while taskpoint != "end":
            keys = ["question", "next"]
            pointmeta = get_metas(request, taskpoint, keys, display=True, checkAccess=False)
            if pointmeta["question"]:
                questionpage = pointmeta["question"].pop()
                #TODO: handle missing page
            else:
                raise RaippaException(u"%s doesn't have question link." % taskpoint)
            flow.append((taskpoint, questionpage))

            if pointmeta["next"]:
                taskpoint = pointmeta["next"].pop()
                #TODO: handle missing page
            else:
                raise MissingMetakException(u"%s doesn't have next link." % taskpoint)

        return flow

    raise RaippaException("Invalid category %s" % pagename)
