#-*- coding: iso-8859-1 -*-
import random

from raippa.pages import Course
from raippa.user import User
from raippa import unicode_form
from MoinMoin.Page import Page

def execute(pagename, request):
    request.form = unicode_form(request.form)

    user = User(request, request.user.name)
    success = False
    if user.is_teacher():
        flow = dict()
        prerequirements = dict()
        flow_queue = [u"first"]

        while len(flow_queue)>0:
            task = flow_queue.pop()
            next = request.form.get("flow_" + task, [])
            flow_queue.extend(next)
            if next:
                flow[task]= next

            prerequirements[task] = request.form.get("req_" + task, [])

        course = Course(request, request.cfg.raippa_config)
        success, msg = course.save_flow(flow, prerequirements)
        if success:
            msg = u"Course flow saved successfully."
        else:
            msg = u"Saving failed!"
    else:
        msg = u"You need to be teacher to edit course flow."

    page = Page(request, pagename)

    if not success:
        request.theme.add_msg(msg, 'error')
        Page(request, pagename).send_page()
    else:
        request.theme.add_msg(msg)
        Page(request, pagename).send_page()

