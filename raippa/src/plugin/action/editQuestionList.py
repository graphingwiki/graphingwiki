#-*- coding: iso-8859-1 -*-
import random

from raippa.pages import Task
from raippa.user import User
from raippa import unicode_form
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor


def save_new_task(request, pagename):
    page = PageEditor(request, pagename)
    template = Page(request, "TaskTemplate").get_raw_body()

    try:
        msg = page.saveText(template, page.get_real_rev())
    except Exception, e:
        return False, unicode(e)

    return True, msg

def execute(pagename, request):
    request.form = unicode_form(request.form)

    user = User(request, request.user.name)
    success = False
    if user.is_teacher():

        if request.form.get("newTask", [u""])[0]:
            name = request.form.get("pagename", [u""])[0]
            if len(name) > 240:
                name = name[:240]
            success, msg =  save_new_task(request, name)
            
            page = Page(request, pagename)
            request.theme.add_msg(msg)
            Page(request, pagename).send_page()
            return

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
        task_options["consecutive"] = [request.form.get("consecutive", [u""])[0]]
        
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

