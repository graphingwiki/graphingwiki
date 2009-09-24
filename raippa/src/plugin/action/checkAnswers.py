# -*- coding: iso-8859-1 -*-
import random, time

from raippa.pages import Course, Question, Answer, SaveException
from raippa.user import User

from MoinMoin.Page import Page

def unique_filename(answers, filename, index=0):
    for name, content in answers:
        if filename == name:
            index += 1
            filename = "%s_%i" % (filename, index)
            return unique_filename(answers, filename, index)

    return filename

def execute(pagename, request):
    question = Question(request, pagename)
    task = question.task()
    tasktype = task.options().get('type', None)
    answertype = question.options().get('answertype', None)

    if answertype == "file":
        answers = list()
        for key in request.form.keys():
            if key.endswith('__filename__'):
                answerkey = key[:-12]
                filename = unique_filename(answers, request.form.get(key, unicode()))
                
                answer = request.form.get(answerkey, list())
                answers.append((filename, answer[1].value))
    elif answertype == "text":
        answers = request.form.get('answer', list())
    else:
        answer_ids = request.form.get('answer', list())
        question_answers = question.answers()
        answers = list()

        for answer_id in answer_ids:
            found = False
            for question_answer in question_answers:
                if answer_id == question_answer.split("/")[-1]:
                    found = True
                    answers.append(Answer(request, question_answer).answer())
            if not found:
                request.theme.add_msg('Missing answers.', 'error')
                Page(request, pagename).send_page()
                return

    if not answers and tasktype not in ['exam']:
        request.theme.add_msg('Missing answers.', 'error')
        Page(request, pagename).send_page()
        return

    starttime = request.form.get('time', [None])[0]

    if starttime:
        try:
            usedtime = int(time.time() - float(starttime))
        except:
            usedtime = None
    else:
        usedtime = None

    user = User(request, request.user.name)

    try:
        overallvalue, successdict = question.check_answers(answers, user, usedtime, True)
    except SaveException, msg:
        request.theme.add_msg(msg.args[0], 'error')
        Page(request, pagename).send_page()
        return

    if tasktype in ['exam', 'questionary']:
        if user.can_do(task)[0]:
            page = Page(request, task.pagename)
        else:
            course = Course(request, request.cfg.raippa_config)
            if course.graphpage:
                page = Page(request, course.graphpage)
            else:
                page = Page(request, request.cfg.page_front_page)

        request.http_redirect(page.url(request))
        return

    if overallvalue in ['success', 'pending']:
        answerpages = successdict.get('right', list())

        comments = []
        while len(answerpages) > 0:
            answerpage = answerpages.pop()
            comment = Answer(request, answerpage).comment()
            if comment:
                comments.append(comment)
        
        request.session["comments"] = comments

        if user.has_done(task)[0]:
            course = Course(request, request.cfg.raippa_config)
            if course.graphpage:
                page = Page(request, course.graphpage)
            else:
                page = Page(request, request.cfg.page_front_page)
        else:
            page = Page(request, task.pagename)

        request.http_redirect(page.url(request))
        return

    else:
        #give tips only for incorrect answers (no point in giving tips for correct answers, right?)
        answerpages = successdict.get('wrong', list())
 
        tip = None

        while not tip and len(answerpages) > 0:
            answerpage = answerpages.pop(random.randrange(0, len(answerpages)))
            tips = Answer(request, answerpage).tips()

            if tips:
                tip = random.choice(tips)

        if not tip:
            tip = u'Incorrect answer.'

        request.theme.add_msg(tip, 'error')
        Page(request, pagename).send_page()

