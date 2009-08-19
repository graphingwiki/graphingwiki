import datetime, time

from MoinMoin.Page import Page
from MoinMoin.action.AttachFile import add_attachment
from graphingwiki.editing import get_keys, get_metas, set_metas
from raippa import addlink
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

    def save_answers(self, question, overallvalue, save_dict):
        histories = self.histories(question.pagename)

        if len(histories) == 1:
            history = histories[0]
            remove = {history: get_keys(self.request, history)}
        elif len(histories) < 1:
            history = "History/"+self.name+"/"+question.pagename
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

        if question.options().get('answertype', None) == 'file':
            historydata = {history: historydata}

            #TODO: check success
            success, msg = set_metas(self.request, remove, dict(), historydata)
            if success:
                revision = Page(self.request, history).get_real_rev()
   
                for filename, content in save_dict.iteritems():
                    filename = u"%s.rev%i" % (filename, revision)
                    filename, size = add_attachment(self.request, history, filename, content)
                    #TODO: check success with filesize

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
            metas = get_metas(self.request, historypage, keys, display=True, checkAccess=False)
        
            categories = metas.get("gwikicategory", list())
            if rc['history'] in categories:
                if questionpage:
                    if questionpage in metas.get("question", list()):
                        histories.append(historypage)
                else:
                    histories.append(historypage)

        return histories

    def has_done(self, instance):
        if isinstance(instance, Task):
            #True, None
            #False, None
            #False, "pending"
            #False, "picked"
            questionlist = instance.questionlist()
            if not questionlist:
                return False, None

            for questionpage in questionlist:
                done, value = self.has_done(Question(self.request, questionpage))
                if not done:
                    return False, value
       
            return True, None
        elif isinstance(instance, Question):
            #True, historypage
            #False, None
            #False, historypage
            #False, "pending"
            #False, "picked"
            histories = self.histories(instance.pagename)
            if len(histories) > 1:
                raise ValueError, "User %s has too many history pages for question %s." % (self.name, instance.pagename)
            if len(histories) == 1:
                history = histories[0]
                keys = ['overallvalue']
                metas = get_metas(self.request, history, keys, display=True, checkAccess=False)

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

            options = instance.options()
            deadline = options.get('deadline', None)

            if deadline:
                #TODO: type check
                deadline = time.strptime(deadline, "%Y-%m-%d")
                deadline = datetime.date(deadline[0], deadline[1], deadline[2])
                today = datetime.date.today()

                if deadline < today:
                    return False, "deadline"

            for taskpage in options.get('prerequisite', list()):
                done, value = self.has_done(Task(self.request, taskpage))
                if not done:
                    return False, "prerequisites"

            may_total = False
            may_reason = None

            questionlist = instance.questionlist()
            for questionpage in questionlist:
                question = Question(self.request, questionpage)
                may, reason = self.can_do(question)

                if may:
                    may_total = True
                    may_reason = reason
                elif not may and reason in ['pending', 'picked']:
                    return True, reason

            if may_total:
               return True, may_reason

            return False, "done"

        elif isinstance(instance, Question):
            #True, None
            #True, "redo"
            #True, "pending"
            #False, None
            #False, "done"
            #False, "pending"
            #False, "picked"
            #False, "prerequisites"

            task = instance.task()
            if not task:
                return False, None

            redo = instance.options().get('redo', unicode())
            done, value = self.has_done(instance)

            if done:
                if redo != "True":
                    return False, "done"
                else:
                    return True, "redo"
            else:
                if redo == "True" and value == "pending":
                    return True, "pending"
                elif value in ["picked", "pending"]:
                    return False, value

            questionlist = task.questionlist()
            for questionpage in questionlist:
                question = Question(self.request, questionpage)

                done, value = self.has_done(question)
                if question.pagename != instance.pagename and not done:
                    return False, "prerequisites"
                elif question.pagename == instance.pagename:
                    return True, None

            return False, None
        else:
            raise ValueError, instance

