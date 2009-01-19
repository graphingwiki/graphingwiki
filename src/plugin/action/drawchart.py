# -*- coding: utf-8 -*-"
from pychart import *
from tempfile import mkstemp
import os 

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page

from raippa import Question
from raippa import getflow

def drawchart(request, coursepage, taskpage, user=None):
    theme.output_format = "png"
    theme.use_color = 1
    theme.reinitialize()

    data = list()
    max = int()

    taskflow = getflow(request, taskpage)
    for index, point in enumerate(taskflow):
        taskpoint = point[0]
        questionpage = point[1]
        question = Question(request, questionpage)
        histories = question.gethistories(coursefilter=coursepage, taskfilter=taskpoint)

        users = list()
        has_passed = int()

        for history in histories:
            h_users = history[0]
            overallvalue = history[1]
            historypage = history[5]
            for h_user in h_users:
                if h_user not in users:
                    users.append(h_user)

                    if overallvalue not in ["False", "pending", "picked", "recap"]:
                        has_passed += 1

        if len(users) > 0:
            users_in_question = len(users) - has_passed
            if users_in_question > max:
                max = users_in_question
            data.append(["/14Q%d" % index, users_in_question])
        else:
            data.append(["/14Q%d" % index, 0])

        if index == len(taskflow)-1:
            data.append(["/14End", has_passed])

    ar = area.T(y_range=(0, max),
                legend = None,
                size=(350, 250),
                x_coord=category_coord.T(data, 0),
                y_axis = axis.Y(label="/14Users in question"),
                x_axis = axis.X(label="/14Questions"))
 
    ar.add_plot(bar_plot.T(hcol=1, cluster=(0, 1), data=data))

    tmp_fileno, tmp_name = mkstemp()
    can = canvas.init(tmp_name)
    ar.draw(can)
    can.close()

    fd = open(tmp_name)
    data = fd.read()
    fd.close()
    os.remove(tmp_name)

    return data

def execute(pagename, request):

    coursepage = request.form.get("course", [None])[0]
    taskpage = request.form.get("task", [None])[0]
    username = request.form.get("user", [None])[0]

    picture = drawchart(request, coursepage, taskpage, username)
    request.write(picture)
    return None
