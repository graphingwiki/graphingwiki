# -*- coding: iso-8859-1 -*-
import random

from raippa.pages import Course, Question, Answer
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
    answertype = question.options().get('answertype', None)

    if answertype == "file":
        answers = list()
        for key in request.form.keys():
            if key.endswith('__filename__'):
                answerkey = key[:-12]
                filename = unique_filename(answers, request.form.get(key, unicode()))
                
                answer = request.form.get(answerkey, list())
                answers.append((filename, answer[1].value))
    else:
        answers = request.form.get('answer', list())

    if not answers:
        request.theme.add_msg('Missing answers.', 'error')
        Page(request, pagename).send_page()
        return

    user = User(request, request.user.name)

    overallvalue, successdict = question.check_answers(answers, user, True)

    if overallvalue in ['success', 'pending']:
        answerpages = successdict.get('right', list())

        #TODO: handle comments
        comment = None
        while not comment and len(answerpages) > 0:
            answerpage = answerpages.pop(random.randrange(0, len(answerpages)))
            comment = Answer(request, answerpage).comment()

        task = question.task()
        questionlist = task.questionlist()
        if questionlist and pagename == questionlist[-1]:
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
        answerpages = successdict.get('right', list())
        answerpages.extend(successdict.get('wrong', list()))
 
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

