import datetime, time

from MoinMoin.Page import Page
from MoinMoin.action.AttachFile import add_attachment
from graphingwiki.editing import get_keys, get_metas, set_metas
from raippa import removelink, addlink
from raippa import raippacategories as rc
from raippa.pages import Task, Question

class User:

    def __init__(self, request, name):
        self.request = request
        self.name = name

    def is_teacher(self):
        teachergroup = Page(self.request, "TeacherGroup")
        raw = teachergroup.get_raw_body()

        for line in raw.split("\n"):
            if line.startswith(" * "):
                link = line[3:].rstrip()

                if link.startswith("[[") and link.endswith("]]"):
                    link = link[2:-2]

                if link == self.name:
                    return True

        return False

    def is_student(self):
        metas = get_metas(self.request, self.name, ["gwikicategory"], checkAccess=False)
        if rc['student'] in metas.get('gwikicategory', list()):
            return True
        return False

    def save_answers(self, question, overallvalue, save_dict, usedtime):
        histories = self.histories(question.pagename)

        if len(histories) == 1:
            history = histories[0]
            remove = {history: get_keys(self.request, history)}
        elif len(histories) < 1:
            history = self.name+"/"+question.pagename
            history = history[:255]
            remove = dict()
        else:
            raise TooManyLinksException, "User %s has too many historypages linking to question %s" % (self.name, question.pagename)

        historydata = {"user": [addlink(self.name)],
                       "question": [addlink(question.pagename)],
                       "overallvalue": [unicode(overallvalue)],
                       "useragent": [self.request.getUserAgent()],
                       "time": [time.strftime("%Y-%m-%d %H:%M:%S")],
                       "gwikicategory": [rc['history']]}

        if usedtime:
            if usedtime > 1800:
                usedtime = 1800
            historydata["usedtime"] = [str(usedtime)]

        if question.options().get('answertype', None) == 'file':
            historydata = {history: historydata}
            historydata[history]['file'] = list()

            #TODO: check success
            revision = Page(self.request, history).get_real_rev()
            if revision == 99999999:
                revision = 1
            else:
                revision += 1
   
            for filename, content in save_dict.iteritems():
                parts = filename.split(".")
                if len(parts) == 1:
                    filename = u"%s_rev%i" % (parts[0], revision)
                else:
                    filename = u"%s_rev%i.%s" % (".".join(parts[:-1]), revision, parts[-1])

                filename, size = add_attachment(self.request, history, filename, content)
                historydata[history]['file'].append("[[attachment:%s]]" % filename)
                #TODO: check success with filesize

            success, msg = set_metas(self.request, remove, dict(), historydata)

            return success, msg
        else:
            historydata['right'] = list()
            historydata['wrong'] = list()

            for value, user_answers in save_dict.iteritems():
                historydata[value].extend(user_answers)

            historydata = {history: historydata}

            return set_metas(self.request, remove, dict(), historydata)

    def histories(self, questionpage=None):
        histories = list()
        
        page = self.request.graphdata.getpage(self.name)
        pagelist = page.get('in', dict()).get("user", list())

        for historypage in pagelist:
            keys = ["gwikicategory", "question"]
            metas = get_metas(self.request, historypage, keys, checkAccess=False)
        
            categories = metas.get("gwikicategory", list())
            if rc['history'] in categories:
                if questionpage:
                    for question in metas.get("question", list()):
                        if removelink(question) == questionpage:
                            histories.append(historypage)
                            break
                else:
                    histories.append(historypage)

        return histories

    def has_done(self, instance):
        if isinstance(instance, Task):
            #True, None
            #True, "exam"
            #True, "questionary"
            #False, None
            #False, "pending"
            #False, "picked"
            questionlist = instance.questionlist()
            if not questionlist:
                return False, None

            type = instance.options().get('type', 'basic')
            if type == "exam":
                return True, "exam"

            info = None

            for questionpage in questionlist:
                done, value = self.has_done(Question(self.request, questionpage))
                if type == "questionary":
                    info = "questionary"
                    if not done:
                        if not value:
                            return False, None
                else:
                    if not done:
                        return False, value
       
            return True, info
        elif isinstance(instance, Question):
            #True, historypage
            #False, None
            #False, historypage
            #False, "pending"
            #False, "picked"

            histories = self.histories(instance.pagename)
            if len(histories) > 1:
                raise ValueError, "User %s has too many history pages for question %s." % (self.name, instance.pagename)

            task = instance.task()
            if task:
                tasktype = task.options().get('type', 'basic')
            else:
                tasktype = None

            if len(histories) == 1:
                history = histories[0]
                keys = ['overallvalue']
                metas = get_metas(self.request, history, keys, checkAccess=False)

                if tasktype in ['exam', 'questionary']:
                    if 'picked' in metas.get('overallvalue', list()):
                        return False, "picked"
                    elif 'pending' in metas.get('overallvalue', list()):
                        return False, "pending"
                    return True, history

                if 'success' in metas.get('overallvalue', list()):
                    return True, history 
                elif 'picked' in metas.get('overallvalue', list()):
                    return False, "picked"
                elif 'pending' in metas.get('overallvalue', list()):
                    return False, "pending"
            else:
                history = None
   
            return False, history
        else:
            raise ValueError, instance

    def can_do(self, instance):
        if isinstance(instance, Task):
            #True, None
            #True, "redo"
            #True, "pending"
            #True, "picked"
            #False, None
            #False, "done"
            #False, "deadline"
            #False, "prerequisites"

            if not instance.questionlist():
                return False, None

            deadline, deadlines = instance.deadline() 

            if self.name in deadlines:
                deadline = deadlines[self.name]

            if deadline:
                deadline = time.strptime(deadline, "%Y-%m-%d")
                deadline = datetime.date(deadline[0], deadline[1], deadline[2])
                today = datetime.date.today()

                if deadline < today:
                    return False, "deadline"

            options = instance.options()

            for taskpage in options.get('prerequisite', list()):
                done, value = self.has_done(Task(self.request, taskpage))
                if not done:
                    return False, "prerequisites"

            questionlist = instance.questionlist()

            may = False
            reason = "done"

            for questionpage in questionlist:
                question = Question(self.request, questionpage)
                done, info = self.has_done(question)

                if done:
                    if question.options().get('redo', False):
                        may = True
                        reason = "redo"
                else:
                    if info in ['pending', 'picked']:
                        return True, info
                    else:
                        return True, None

            return may, reason

        elif isinstance(instance, Question):
            #True, None
            #True, "redo"
            #True, "pending"
            #False, None
            #False, "done"
            #False, "pending"
            #False, "picked"
            #False, "deadline"
            #False, "prerequisites"

            task = instance.task()
            if not task:
                return False, None

            may, info = self.can_do(task)
            if not may:
                return False, info

            redo = instance.options().get('redo', False)
            done, value = self.has_done(instance)

            if done:
                if not redo:
                    return False, "done"
                else:
                    return True, "redo"
            else:
                if redo and value == "pending":
                    return True, "pending"
                elif value in ["picked", "pending"]:
                    return False, value

            tasktype = task.options().get('type', None)

            if tasktype in ['basic', 'questionary'] and task.options().get('consecutive', False):
                questionlist = task.questionlist()
                prerequisites = questionlist[:questionlist.index(instance.pagename)]
                prerequisites.reverse()

                for questionpage in prerequisites:
                    question = Question(self.request, questionpage)

                    done, value = self.has_done(question)
                    if not done:
                        return False, "prerequisites"

            return True, None
        else:
            raise ValueError, instance

