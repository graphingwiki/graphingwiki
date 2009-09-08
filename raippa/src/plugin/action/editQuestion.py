#-*- coding: iso-8859-1 -*-
import random

from raippa.pages import Question, Answer
from raippa.user import User
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

question_options = ("redo", "answertype")
answer_options = ("answer", "tip", "comment", "value")

def sanitize(input):
    input = unicode(input)
    input = input.replace("\r", "")
    input = input.replace("\n", " ")
    return input.strip()



def save_new_question(request, pagename):
    page = PageEditor(request, pagename)
    template = Page(request, "QuestionTemplate").get_raw_body()

    try:
        msg = page.saveText(template, page.get_real_rev())
    except Exception, e:
        return False, unicode(e)

    return True, msg


def execute(pagename, request):
  
    user = User(request, request.user.name)
    success = False
    if user.is_teacher():
        if request.form.get("newQuestion", [u""])[0]:
            name = request.form.get("pagename", [u""])[0]
            if len(name) > 240:
                name = name[:240]
            success, msg =  save_new_question(request, name)
            
            page = Page(request, pagename)
            request.theme.add_msg(msg)
            Page(request, pagename).send_page()
            return

        
        answer_data = list()
        for key in request.form:
            if key.startswith("answer"):
                try:
                    index = unicode(int(key[6:]))
                except (ValueError):
                    continue

                answer = sanitize(request.form.get(key, [u""])[0])
                if not answer:
                    continue

                tip = sanitize(request.form.get("tip" + index, [u""])[0])
                comment = sanitize(request.form.get("comment" + index, [u""])[0])
                value = sanitize(request.form.get("value" + index, [u""])[0])
                old_page = request.form.get("page" + index, [u""])[0]
                answer_data.append({
                    "answer": [answer],
                    "value" : [value],
                    "tip" : [tip],
                    "comment" : [comment],
                    "old_page" : [old_page]})


        question_options = dict()
        question_options["redo"] = [request.form.get("redo", [u"False"])[0]]
        question_options["answertype"] = [request.form.get("answertype", [u""])[0]]

        question = Question(request, pagename)
        success, msg = question.save_question(answer_data, question_options)
        if success:
            msg = u"Question saved successfully."
        else:
            msg = u"Saving failed!"
    else:
        msg = u"You need to be teacher to edit questions."

    page = Page(request, pagename)

    if not success:
        request.theme.add_msg(msg, 'error')
        Page(request, pagename).send_page()
    else:
        request.theme.add_msg(msg)
        Page(request, pagename).send_page()

