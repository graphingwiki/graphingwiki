from graphingwiki.editing import getmetas
from graphingwiki.editing import edit_meta
from graphingwiki.editing import getkeys
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input
from graphingwiki.patterns import GraphData
from graphingwiki.patterns import getgraphdata
from graphingwiki.patterns import encode

from raippa import RaippaUser
from raippa import FlowPage
from raippa import Question
from raippa import addlink, removelink

taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
statuscategory = u'CategoryStatus'

def redirect(request, pagename, tip=None):
    if tip == "generic":
        url = u'%s/%s?action=tip' % (request.getBaseURL(), pagename)
    elif tip:
        url = u'%s/%s?action=tip&%s' % (request.getBaseURL(), pagename, tip)
    else:
        url = u'%s/%s' % (request.getBaseURL(), pagename)
    request.http_redirect(url)

def execute(pagename, request):
    request.raippauser = RaippaUser(request)

    if request.form.has_key(u'selectcourse'):
        coursename = request.form.get(u'course', [u''])[0]
        if coursename:
            currentpage = FlowPage(request, pagename, request.raippauser)
            globaldata = GraphData(request)
            metakeys = getkeys(globaldata, request.raippauser.statuspage)
            if metakeys.has_key(u'current'):
                edit_meta(request, request.raippauser.statuspage, {u'current': [addlink(request.raippauser.currentcourse)]}, {u'current': [addlink(coursename)]})
            else:
                edit_meta(request, request.raippauser.statuspage, {u'': [u'']}, {u'current': [addlink(coursename)]})
            redirect(request, coursename)
        else:
            request.write(u'Missing course name.')
    elif request.form.has_key(u'start'):
        userselection = request.form.get("userselection", [None])[0]
        currentpage = FlowPage(request, pagename, request.raippauser)
        fp, task = currentpage.setnextpage(userselection)
        if fp == "end" and task == "end":
            redirect(request, pagename)
        else:
            redirect(request, task)
    elif request.form.has_key(u'send'):
        currentpage = FlowPage(request, pagename, request.raippauser)
        if taskcategory in currentpage.categories and (currentpage.type == u'exam' or currentpage.type == u'questionary'):
            useranswers = dict()
            taskflow = currentpage.getflow()
            for key in request.form:
                if key.startswith('answer'):
                    useranswers[int(key[6:])] = request.form[key]
            if len(useranswers) != len(taskflow) and currentpage.type == u'questionary':
                redirect(request, currentpage.pagename, "noanswer")
            else:
                #let's mark user to the first taskpoint
                taskpage = FlowPage(request, taskflow[0][0], request.raippauser)
                nextflowpoint, nexttask = taskpage.setnextpage()
                for index, page_tuple in enumerate(taskflow):
                    if useranswers.get(index, None):
                        questionpage = Question(request, page_tuple[1])
                        if questionpage.answertype == "file":
                            historypage = questionpage.writefile()
                            questionpage.writehistory(request.raippauser.id, request.raippauser.currentcourse, page_tuple[0], "pending", {}, historypage)
                        else:
                            overallvalue, successdict, tips = questionpage.checkanswers(useranswers[index])
                            questionpage.writehistory(request.raippauser.id, request.raippauser.currentcourse, page_tuple[0], overallvalue, successdict)
                    if nextflowpoint != "end" and nexttask != "end" and nextflowpoint == request.raippauser.currentcoursepoint:
                        taskpage = FlowPage(request, page_tuple[0], request.raippauser)
                        nextflowpoint, nexttask = taskpage.setnextpage()
                if nextflowpoint == "end" and nexttask == "end":
                    redirect(request, request.raippauser.currentcourse)
                else:
                    redirect(request, nexttask)
        elif taskpointcategory in currentpage.categories:
            if request.form.has_key(u'answer') or request.form.has_key(u'file'):
                useranswers = request.form[u'answer']
                questionpage = currentpage.getquestionpage()
                if questionpage:
                    questionpage = Question(request, questionpage)
                    if questionpage.answertype == "file":
                        historypage = questionpage.writefile()
                        questionpage.writehistory(request.raippauser.id, request.raippauser.currentcourse, request.raippauser.currenttask, "pending", {}, historypage)
                        redirect(request, currentpage.pagename)
                    else:
                        overallvalue, successdict, tips = questionpage.checkanswers(useranswers)
                        questionpage.writehistory(request.raippauser.id, request.raippauser.currentcourse, request.raippauser.currenttask, overallvalue, successdict)
                        if overallvalue:
                            nextflowpoint, nexttask = currentpage.setnextpage()
                            if nextflowpoint == "end" and nexttask == "end":
                                redirect(request, request.raippauser.currentcourse)
                            else:
                                redirect(request, nexttask)
                        else:
                            try:
                                globaldata = GraphData(request)
                                metas = getmetas(request, globaldata, currentpage.pagename, [u'failure'], checkAccess=False)
                                globaldata.closedb()
                                failurepage = metas["failed"][0][0]
                                failurekey = request.raippauser.currentcourse + "failure"
                                input = order_meta_input(request, request.raippauser.statuspage, {failurekey: [failurepage]}, "repl")
                                process_edit(request, input, True, {request.raippauser.statuspage:[statuscategory]})
                                #TODO: penalty round message
                                redirect(request, failurepage)
                            except:
                                failurepage = currentpage.pagename
                                redirect(request, failurepage, tips[0])
                else:
                    request.write(u'Cannot find questionpage.')
            else:
                redirect(request, currentpage.pagename, "noanswer")
        else:
            request.write(u'Invalid input.')
    else:
        request.write(u'Invalid input.')
