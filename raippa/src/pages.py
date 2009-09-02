# -*- coding: utf-8 -*-

import time
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.user import User as MoinUser
from MoinMoin.logfile import editlog
from graphingwiki.editing import get_revisions, get_metas, get_keys, set_metas 
from raippa import removelink, addlink, randompage
from raippa import raippacategories as rc
from raippa.flow import Flow

class DeadLinkException(Exception):
    pass

class TooManyKeysException(Exception):
    pass

class TooManyLinksException(Exception):
    pass

class TooManyValuesException(Exception):
    pass

class MissingMetaException(Exception):
    pass

class PageDoesNotExistException(Exception):
    pass

class SaveException(Exception):
    pass

class Answer:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename

    def question(self):
        pagedata = self.request.graphdata.getpage(self.pagename)
        pages = pagedata.get('in', dict()).get('answer', list())

        questions = list()

        for page in pages:
            keys = ["gwikicategory", "question"]
            qmetas = get_metas(self.request, page, keys, checkAccess=False)
            
            if rc['questionoptions'] in qmetas.get('gwikicategory', list()):
                for questionpage in qmetas.get("question", list()):
                    questions.append(removelink(questionpage))

        if len(questions) == 1:
            return Question(self.request, questions[0])
        elif len(questions) > 1:
            raise TooManyValuesException(u'Too many pages linking in to %s.' % self.pagename)
        else:
            return None

    def answer(self):
        metas = get_metas(self.request, self.pagename, ['answer'], checkAccess=False)
        answers = metas.get('answer', list())

        answer = None

        if len(answers) == 1:
            answer = answers[0]
            #TODO: if page, get content
        elif len(answers) > 1:
            raise TooManyValuesException(u'Page %s has too many "answer" -metas.' % self.pagename)
        else:
            raise MissingMetaException(u'''Page %s doesn't have "answer" -meta.''' % self.pagename)

        return answer

    def value(self):
        metas = get_metas(self.request, self.pagename, ['value'], display=True, checkAccess=False)
        values = metas.get('value', list())

        value = None

        if len(values) == 1:
            value = values[0]
        elif len(values) > 1:
            raise TooManyValuesException(u'Page %s has too many "value" -metas.' % self.pagename)
        else:
            raise MissingMetaException(u'''Page %s doesn't have "value" -meta.''' % self.pagename)

        return value

    def tips(self):
        metas = get_metas(self.request, self.pagename, ['tip'], checkAccess=False)
        tips = metas.get('tip', list())

        return tips

    def comment(self):
        metas = get_metas(self.request, self.pagename, ['comment'], checkAccess=False)
        comments = metas.get('comment', list())
        if len(comments) == 1:
            return comments[0]
        elif len(comments) > 1:
            raise TooManyValuesException(u'Page %s has too many "comment" -metas.' % self.pagename)
        else:
            return None


class Question:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename
        self.optionspage = u'%s/options' % pagename

    def title(self):
        raw_content = Page(self.request, self.pagename).get_raw_body()
        title = unicode()

        for line in raw_content.split("\n"):
            if line.startswith("== ") and line.endswith(" =="):
                title = line[3:-3]

        return title

    def answers(self):
        answers = list()

        if not Page(self.request, self.optionspage).exists():
            return answers

        metas = get_metas(self.request, self.optionspage, ['answer'], checkAccess=False)
        answerpages = metas.get('answer', list())

        for answerpage in answerpages:
            answerpage = removelink(answerpage)
            if not Page(self.request, answerpage).exists():
                raise DeadLinkException(u"Page %s linked in %s doesn't exist." % (answerpage, self.optionspage))

            answers.append(answerpage)
            
        return answers

    def check_answers(self, user_answers, user, usedtime=None, save_history=False):
        success_dict = {"right":list(), "wrong":list()}
        save_dict = dict() 
        overallvalue = str()

        questiontype = self.options().get('answertype', None)
        if not questiontype:
            raise MissingMetaException(u"Question %s doesn't have answertype option." % self.pagename)

        if questiontype in ['checkbox', 'radio', 'text']:
            answerpages = self.answers()
            save_dict = {"right":list(), "wrong":list()}
            overallvalue = "success"

            for answerpage in answerpages:
                answer = Answer(self.request, answerpage)

                if answer.value() == "right":
                    if answer.answer() not in user_answers:
                        success_dict["wrong"].append(answerpage)
                        if questiontype != 'text':
                            overallvalue = "failure"
                    else:
                        user_answers.remove(answer.answer())
                        success_dict["right"].append(answerpage)
                        save_dict["right"].append(answer.answer())
                else:
                    if answer.answer() in user_answers:
                        success_dict["wrong"].append(answerpage)
                        save_dict["wrong"].append(answer.answer())
                        overallvalue = "failure"
                    else:
                        success_dict["right"].append(answerpage)

            if len(answerpages) > 0 and len(user_answers) > 0:
                overallvalue = "failure"
                for user_answer in user_answers:
                    save_dict["wrong"].append(user_answer)

        elif questiontype == 'file':
            for filename, content in user_answers:
                overallvalue = "pending"
                save_dict[filename] = content
        else:
            raise ValueError, "Incorrect answertype." 

        if save_history:
            #TODO: check if save was successfull
            success, msg = user.save_answers(self, overallvalue, save_dict, usedtime)
            if not success:
                raise SaveException, msg

        return overallvalue, success_dict 

    def save_question(self, answers_data, options):
        save_data = dict()
        save_data[self.optionspage] = dict()
        remove = dict()
        remove[self.pagename] = list()
        remove[self.optionspage] = list()
        pages_to_delete = list()
        old_answers = list()

        if len(answers_data) > 0:
            remove[self.optionspage].append("answer")
            old_answers = self.answers()
            new_answers = list()
            answerpages = list()

            for anspage in old_answers:
                remove[anspage] = ["value", "answer", "comment", "tip"]

            for ans in answers_data:
                try:
                    old_page = ans.get("old_page", [u""])[0]
                    anspage = old_answers.pop(old_answers.index(old_page))

                except:
                    anspage = self.pagename +"/" +randompage(self.request, "answer")

                save_data[anspage] ={
                        "answer" : ans.get("answer", [u""]),
                        "value" : ans.get("value", [u""]),
                        "tip" : ans.get("tip", [u""]),
                        "comment" : ans.get("comment", [u""]),
                        "gwikicategory" : [rc['answer']]
                    }
                new_answers.append(addlink(anspage))

            save_data[self.optionspage]["answer"] = new_answers

        if options:
            remove[self.optionspage].extend(["redo", "answertype"])
            save_data[self.optionspage]["redo"] =  options.get("redo", [u"True"])
            save_data[self.optionspage]["answertype"] = options.get("answertype", [u""])
            save_data[self.optionspage]["question"] =  [self.pagename]
            save_data[self.optionspage]["gwikicategory"] =  [rc['questionoptions']]

        success, msg =  set_metas(self.request, remove, dict(), save_data)

        if success:
            for page in old_answers:
                rm_success, rm_msg = PageEditor(self.request,page).deletePage()

        return success, msg

    def options(self):
        options = dict()

        if not Page(self.request, self.optionspage).exists():
            return options

        optionkeys = ['answertype', 'redo']
        metas = get_metas(self.request, self.optionspage, optionkeys, checkAccess=False)

        for key in optionkeys:
            values = metas.get(key, list())
            if len(values) == 1:
                options[key] = values[0]
            elif len(values) > 1:
                raise TooManyValuesException(u'Question %s has too many %s options.' % (self.pagename, key))          
            elif len(values) < 1:
                raise MissingMetaException(u"Question %s doesn't have %s option." % (self.pagename, key))

        return options

    def histories(self):
        histories = list()

        page = self.request.graphdata.getpage(self.pagename)
        pagelist = page.get('in', dict()).get("question", list())

        for historypage in pagelist:
            metas = get_metas(self.request, historypage, ["gwikicategory"], checkAccess=False)

            categories = metas.get("gwikicategory", list())

            if rc['history'] in categories:
                histories.append(historypage)

        return histories

    def students(self, user=None):
        done = dict()
        doing = dict()

        if user:
            histories = user.histories(self.pagename)
        else:
            histories = self.histories()

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

    def history_revisions(self, histories=None):
        if not histories:
            histories = self.histories()

        revisions = dict()

        for historypage in histories:
            revisions[historypage] = dict()
            editors = dict()
            log = editlog.EditLog(self.request, rootpagename=historypage)
            for line in log:
                editors[int(line.rev)] = MoinUser(self.request, line.userid).name

            pages, keys = get_revisions(self.request, Page(self.request, historypage))

            keys = ['user',
                    'overallvalue', 'right', 'wrong',
                    'time', 'usedtime',
                    'gwikicategory', 'gwikirevision']

            for page in pages:
                metas = get_metas(self.request, page, keys)

                revision = int(metas.get('gwikirevision', list())[0])
                editor = editors[revision]

                users = list()
                for user in metas.get('user', list()):
                    users.append(removelink(user))

                if editor not in users:
                    continue

                right = metas.get('right', list())
                wrong = metas.get('wrong', list())

                overall = metas.get('overallvalue', list())
                if len(overall) < 1 or len(overall) > 1:
                    continue
                else:
                    overall = overall[0]

                answer_time = metas.get('time', list())
                if len(answer_time) < 1 or len(answer_time) > 1:
                    continue
                else:
                    try:
                        time.strptime(answer_time[0], "%Y-%m-%d %H:%M:%S")
                        answer_time = answer_time[0]
                    except:
                        continue
            
                used = metas.get('usedtime', list())
                if len(used) < 1 or len(used) > 1:
                    continue
                else:
                    try:
                        used = int(float(used[0]))
                    except:
                        continue
            
                revisions[historypage][revision] = [users, overall, right, wrong, answer_time, used]

        return revisions

    def used_time(self, user=None):
        if user:
            histories = user.histories(self.pagename)
        else:
            histories = self.histories()

        revisions = Question(request, self.pagename).history_revisions(histories)
        total_time = int()
        total_revs = int()
        
        for historypage in revisions:
            if not revisions.get(historypage, dict()):
                continue

            user_total = int()
            for rev_number in revisions[historypage].keys():
                user_total += revisions[historypage][rev_number][5]

            total_time += user_total
            total_revs += len(revisions[historypage].keys())

        return total_time, total_revs

    def task(self):
        pagedict = self.request.graphdata.getpage(self.pagename).get('in', dict())

        tasks = list()

        for key, pages in pagedict.iteritems():
            if key not in ['_notype', 'question']:
                for page in pages:
                    keys = ["gwikicategory", "task"]
                    metas = get_metas(self.request, page, keys, checkAccess=False)
                    if rc['taskflow'] in metas.get('gwikicategory', list()):
                        for taskpage in metas.get('task', list()):
                            tasks.append(removelink(page[:-5]))

        if len(tasks) == 1:
            return Task(self.request, tasks[0])
        elif len(tasks) > 1:
            raise TooManyLinksException(u"Question %s linked in: %s" % (self.pagename, ", ".join(tasks)))

        return None


class Task:

    def __init__(self, request, pagename):
        self.request = request
        self.pagename = pagename
        self.optionspage = u'%s/options' % pagename
        self.flowpage = u'%s/flow' % pagename
        if Page(request, self.flowpage).exists():
            self.flow = Flow(request, self.flowpage)
        else:
            self.flow = None

    def deadline(self):
        metas = get_metas(self.request, self.optionspage, ['deadline'], checkAccess=False)
        overall = None
        deadlines = dict()
        for value in metas.get('deadline', list()):
            try:
                kek = time.strptime(value, "%Y-%m-%d")
                if not overall:
                    overall = value 
                else:
                    raise TooManyKeysException, "Task %s has too many overal deadlines." % self.pagename
            except ValueError:
                value = removelink(value)
                if Page(self.request, value).exists():
                    keys = get_keys(self.request, value)
                    dmetas = get_metas(self.request, value, keys, checkAccess=False)
                    for key in dmetas:
                        umeta = get_metas(self.request, key, ["gwikicategory"], checkAccess=False)
                        if rc['student'] in umeta.get('gwikicategory', list()):
                            users_deadlines = list()
                            for deadline in dmetas.get(key, list()):
                                try:
                                    time.strptime(deadline, "%Y-%m-%d")
                                    users_deadlines.append(deadline)
                                except:
                                    pass

                            if len(users_deadlines) > 1:
                                raise TooManyKeysException, "Page %s has too many deadlines for user %s." % (value, key)
                            elif len(users_deadlines) == 1:
                                deadlines[key] = users_deadlines[0]

        return overall, deadlines

    def options(self):
        options = dict()

        if not Page(self.request, self.optionspage).exists():
            return options

        optionkeys = ['type', 'prerequisite']
        metas = get_metas(self.request, self.optionspage, optionkeys, checkAccess=False)
        for key in optionkeys:
            values = list()

            for value in metas.get(key, list()):
                values.append(removelink(value))

            if key == 'prerequisite':
                if len(values) > 0:
                    options[key] = values

            else:
                if len(values) == 1:
                    options[key] = values[0]
                elif len(values) > 1:
                    raise TooManyValuesException(u'Task %s has too many %s options.' % (self.pagename, key))
                elif len(values) < 1:
                    raise MissingMetaException(u"Task %s doesn't have %s option." % (self.pagename, key))

        return options

    def questionlist(self):
        if not self.flow:
            return list()

        questionlist = list()
        next = 'first'

        while next != None:
            nextlist = self.flow.next_from_point(next)
            if len(nextlist) > 1:
                raise TooManyKeysException(u"Flow %s has too many metas with key %s." % (self.flowpage, next))
            elif len(nextlist) < 1:
                next = None
            else:
                next = nextlist[0]

                if next and next in questionlist:
                    raise TooManyValuesException("Flow %s has key %s linked in multiple times." % self.flowpage)       
                elif not Page(self.request, next).exists():
                    raise DeadLinkException(u"Page %s linked in %s doesn't exist." % (next, self.flowpage))

                questionlist.append(next)

        return questionlist

    def students(self, user=None):
        questions = self.questionlist()

        if not questions:
            return dict(), dict(), dict()

        done = dict()
        doing = dict()
        rev_count = dict()

        for question in questions:
            done_question, doing_question = Question(self.request, question).students(user)
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

    def used_time(self, user=None):
        flow = self.questionlist()
        total_time = int()
        total_count = int()

        for questionpage in flow:
            used_time, try_count = Question(self.request, questionpage).used_time(user) 
            total_time += used_time
            total_count += try_count

        return total_time, total_count

    def title(self):
        raw_content = Page(self.request, self.pagename).get_raw_body()
        title = unicode()

        for line in raw_content.split("\n"):
            if line.startswith("== ") and line.endswith(" =="):
                title = line[3:-3]

        return title

    def save_flow(self, flow, options):
        save_data = dict()
        save_data[self.optionspage] = dict()
        save_data[self.flowpage] = dict()
        remove = dict()
        remove[self.pagename] = list()
        remove[self.optionspage] = list()
        remove[self.flowpage] = list()

        #TODO: create copy of questions that already exists in other tasks
        if flow:
            remove[self.flowpage] = self.questionlist()
            remove[self.flowpage].extend(["first"])
            for key,val in flow.iteritems():
                if len(val) > 1:
                    raise TooManyValuesException("Trying to save too many values to flow node.")
                save_data[self.flowpage][key] = [addlink(val[0])]

            remove[self.flowpage].extend(["task"])
            save_data[self.flowpage]["task"] = [addlink(self.pagename)]
            save_data[self.flowpage]["gwikicategory"] = [rc['taskflow']]

        if options:
            remove[self.optionspage].extend(["type", "deadline", "task"])
            save_data[self.optionspage]["type"] = options.get("type", [u""])
            save_data[self.optionspage]["deadline"] = options.get("deadline", [u""])

        save_data[self.optionspage]["task"] =  [addlink(self.pagename)]
        save_data[self.optionspage]["gwikicategory"] =  [rc['taskoptions']]

        success, msg =  set_metas(self.request, remove, dict(), save_data)

        return success, msg



class Course:

    def __init__(self, request, config):
        self.request = request
        self.config = config

        if not Page(request, config).exists():
            self.graphpage = None
            self.flowpage = None
            self.flow = None
        else:
            keys = ['graph', 'flow'] 
            metas = get_metas(self.request, self.config, keys, checkAccess=False)

            graphs = metas.get('graph', list())
            if len(graphs) == 1:
                self.graphpage = removelink(graphs[0])
            elif len(graphs) < 1:
                self.graphpage = None
            else:
                raise TooManyValuesException("Page %s has too many graph values" % self.config)

            flows = metas.get('flow', list())
            if len(flows) == 1:
                self.flowpage = removelink(flows[0])
                self.flow = Flow(request, self.flowpage)
            elif len(flows) < 1:
                self.flowpage = None
                self.flow = None
            else:
                raise TooManyValuesException("Page %s has too many flow values" % self.config)

    def students(self, user):
        done_all, doing_all = dict()
        flow = self.flow.fullflow()

        for taskpage in flow:
            if taskpage != "first":
                task = Task(request, taskpage)
                done, doing, revs = task.users(user)

                for doing_user in doing:
                    if doing_user not in doing_all:
                        doing_all[doing_user] = list()
                    doing_all[doing_user].append(taskpage)

                for done_user in done:
                    if done_user not in done_all:
                        done_all[done_user] = list()
                    done_all[done_user].append(taskpage)

        return done_all, doing_all

    def used_time(self, user=None):
        total_time = int()
        total_tries = int()

        flow = self.flow.fullflow()
        for taskpage in flow:
            if taskpage != "first":
                task = Task(request, taskpage)
                task_time, try_count = task.used_time(user)
                total_time += task_time
                total_tries += try_count 
                
        return total_time, total_tries
