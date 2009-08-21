from raippa.pages import Course, Task, Question
from raippa import pages_in_category
from raippa import raippacategories as rc
from raippa import removelink

from graphingwiki.editing import get_metas
from MoinMoin.Page import Page

class CourseStats:

    def __init__(self, request, config):
        self.request = request
        self.config = config
        self.course = Course(request, config)

    def students(self):
        pagelist = pages_in_category(self.request, rc['student'])
        return pagelist

class TaskStats:

    def __init__(self, request, taskpage):
       self.request = request
       self.task = Task(request, taskpage)

    def students(self, user=None):
        questions = self.task.questionlist()

        if not questions:
            return dict(), dict()

        done = dict()
        doing = dict()
        rev_count = dict()

        for question in questions:
            stats = QuestionStats(self.request, question)
            done_question, doing_question = stats.students(user)
            rev_count[question] = list()

            for student in done:
                if student not in done_question:
                    if doing.get(student, None) == None:
                        doing[student] = list()
                    doing[student].append(question)

            for student in done_question:
                if done.get(student, None) == None:
                    done[student] = list()
                done[student].append(question)
                rev_count[question].append(done_question[student])

            for student in doing_question:
                if doing.get(student, None) == None:
                    doing[student] = list()
                doing[student].append(question)
                rev_count[question].append(doing_question[student])

        return done, doing, rev_count

class QuestionStats:

    def __init__(self, request, questionpage):
        self.request = request
        self.question = Question(request, questionpage)
        self.histories = None

    def students(self, user=None):
        done = dict()
        doing = dict()

        if user:
            histories = user.histories(self.question.pagename)
        elif self.histories == None:
            self.histories = self.question.histories()
            histories = self.histories

        keys = ['user', 'overallvalue']
        for history in histories:
            metas = get_metas(self.request, history, keys, checkAccess=False)

            users = metas.get('user', list())
            if not users:
                continue

            revision = Page(self.request, history).get_real_rev()

            overallvalue = metas.get('overallvalue', [None])[0]
            if overallvalue == "success":
                for user in users:
                    user = removelink(user)
                    metas = get_metas(self.request, user, ['gwikicategory'], checkAccess=False)
                    if rc['student'] in metas.get('gwikicategory', list()):
                        done[user] = revision
            else:
                for user in users:
                    metas = get_metas(self.request, user, ['gwikicategory'], checkAccess=False)
                    if rc['student'] in metas.get('gwikicategory', list()):
                        doing[user] = revision

        return done, doing
