#-*- coding: iso-8859-1 -*-
import random

from raippa.pages import Task
from raippa.user import User
from raippa import unicode_form
from MoinMoin.Page import Page

answer_options = ("answer", "tip", "comment", "value")

def execute(pagename, request):
    request.form = unicode_form(request.form)

    user = User(request, request.user.name)
    success = False
    if user.is_teacher():
        flow = dict()
        flow_queue = [u"first"]

        while len(flow_queue)>0:
            question = flow_queue.pop()
            next = request.form.get("flow_" + question, [])
            flow_queue.extend(next)
            if next:
                flow[question]= next
        task_options = dict()
        task_options["type"] = [request.form.get("type", [u"basic"])[0]]
        task_options["deadline"] = [request.form.get("deadline", [u""])[0]]

        task = Task(request, pagename)
        success, msg = task.save_flow(flow, task_options)
        if success:
            msg = u"Question list saved successfully."
        else:
            msg = u"Saving failed!"
    else:
        msg = u"You need to be teacher to edit question list."

    page = Page(request, pagename)

    if not success:
        request.theme.add_msg(msg, 'error')
        Page(request, pagename).send_page()
    else:
        request.theme.add_msg(msg)
        Page(request, pagename).send_page()

