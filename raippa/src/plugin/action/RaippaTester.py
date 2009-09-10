# -*- coding: utf-8 -*-
import sys, time

from raippa.pages import Answer, Question, Task, RaippaException
from raippa.user import User
from raippa import raippacategories as rc
from raippa import removelink
from graphingwiki.editing import get_metas, get_keys

from MoinMoin.Page import Page

def test_answer(request, pagename):
    answer = Answer(request, pagename)
    results = list()
     
    try:
        question = answer.question()
    except RaippaException, e:
        results.append("%s: %s" % (pagename, e.value))

    try:
        answer_text = answer.answer()
    except RaippaException, e:
        results.append("%s: %s" % (pagename, e.value))

    try:
        value = answer.value()
    except RaippaException, e:
        results.append("%s: %s" % (pagename, e.value))

    return results

def test_history(request, pagename):
    results = list()
    keys = ['question', 'usedtime', 'user', 'overallvalue', 'time']
    metas = get_metas(request, pagename, keys, checkAccess=False)

    if len(metas.get('question', list())) > 1:
        results.append(u'%s: Too many values for "question" -key.' % pagename)
    elif len(metas.get('question', list())) < 1:
        results.append(u'''%s: Page doesn't have "question" -meta.''' % pagename)

    if len(metas.get('usedtime', list())) > 1:
        results.append(u'%s: Too many values for "usedtime" -key.' % pagename)
    elif len(metas.get('usedtime', list())) < 1:
        results.append(u'''%s: Page doesn't have "usedtime" -meta.''' % pagename)
    else:
        try:
            float(metas['usedtime'][0])
        except ValueError:
            results.append(u'%s: Invalid "usedtime" value.' % pagename)

    if len(metas.get('user', list())) < 1:
        results.append(u'''%s: Page doesn't have "user" -meta.''' % pagename)

    if len(metas.get('overallvalue', list())) > 1:
        results.append(u'%s: Too many values for "overallvalue" -key.' % pagename)
    elif len(metas.get('overallvalue', list())) < 1:
        results.append(u'''%s: Page doesn't have "overallvalue" -meta.''' % pagename)

    if len(metas.get('time', list())) > 1:
        results.append(u'%s: Too many values for "time" -key.' % pagename)
    elif len(metas.get('time', list())) < 1:
        results.append(u'''%s: Page doesn't have "time" -meta.''' % pagename)
    else:
        try:
            time.strptime(metas['time'][0], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            results.append(u'%s: Invalid "time" value.' % pagename)

    return results

def test_question(request, pagename):
    results = list()

    keys = ['gwikicategory', 'question']
    metas = get_metas(request, pagename, keys, checkAccess=False)

    if rc['questionoptions'] in metas.get('gwikicategory', list()):
        if len(metas.get('question', list())) > 1:
            results.append(u'%s: Too many values for "question" -key.' % pagename)
        elif len(metas.get('question', list())) < 1:
            results.append(u'''%s: Page doesn't have "question" -meta.''' % pagename)
        else:
            if not Page(request, removelink(metas['question'][0])).exists():
                results.append(u'''%s: %s linked in doesn't exist.''' % (pagename, metas['question'][0]))
                return results

            pagename = metas['question'][0]

    question = Question(request, pagename)

    try:
        task = question.task()
    except RaippaException, e:
        results.append("%s: %s" % (pagename, e.value))
    
    answers = list()
    try:
        answers = question.answers()
    except RaippaException, e:
        results.append("%s: %s" % (pagename, e.value))

    if not answers:
        results.append("Question %s doesn't have answers." % pagename)
    else:
        for answerpage in answers:
            results.extend(test_answer(request, answerpage))

    try:
        options = question.options()
    except RaippaException, e:
        results.append("%s: %s" % (pagename, e.value))

    histories = question.histories()

    for historypage in histories:
        results.extend(test_history(request, historypage))

    return results

def test_task(request, pagename):
    results = list()
    
    keys = ['gwikicategory', 'task']
    metas = get_metas(request, pagename, keys, checkAccess=False)
    cats = metas.get('gwikicategory', list())    

    if rc['taskoptions'] in cats or rc['taskflow'] in cats:
        if len(metas.get('task', list())) > 1:
            results.append(u'%s: Too many values for "task" -key.' % pagename)
        elif len(metas.get('task', list())) < 1:
            results.append(u'''%s: Page doesn't have "task" -meta.''' % pagename)
        else:
            if not Page(request, removelink(metas['task'][0])).exists():
                results.append(u'''%s: %s linked in doesn't exist.''' % (pagename, metas['task'][0]))
                return results
                
            pagename = metas['task'][0]

    task = Task(request, pagename)

    try:
        deadlines = task.deadline()
    except RaippaException, e:
        results.append("%s: %s" % (pagename, e.value))

    try:
        options = task.options()
    except RaippaException, e:
        results.append("%s: %s" % (pagename, e.value))

    questions = list()
    try:
        questions = task.questionlist()
    except RaippaException, e:
        results.append("%s: %s" % (pagename, e.value))

    if not questions:
        results.append("Task %s doesn't have questions." % pagename)
    else:
        for questionpage in questions:
            results.extend(test_question(request, questionpage))

    return results

def execute(pagename, request):
    user = User(request, request.user.name)
    if not user.is_teacher():
        request.theme.add_msg(u"You are not allowed to do RaippaTester on this page.", "error")
        Page(request, pagename).send_page()
        return

    metas = get_metas(request, pagename, ['gwikicategory'], checkAccess=False)

    cats = metas.get('gwikicategory', list())
    if rc['answer'] in cats:
        request.write("\n".join(test_answer(request, pagename)))
    elif rc['history'] in cats:
        request.write("\n".join(test_history(request, pagename)))
    elif rc['question'] in cats or rc['questionoptions'] in cats:
        request.write("\n".join(test_question(request, pagename)))
    elif rc['task'] in cats or rc['taskflow'] in cats or rc['taskoptions'] in cats:
        request.write("\n".join(test_task(request, pagename)))
    else:
        keys = get_keys(request, pagename)
        metas = get_metas(request, request.cfg.raippa_config, keys, checkAccess=False)

    request.write("")
