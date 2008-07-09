# -*- coding: iso-8859-1 -*-
import random
import os

from MoinMoin import config
from MoinMoin.action.AttachFile import getAttachDir

from graphingwiki.editing import getmetas
from graphingwiki.patterns import GraphData, encode
from graphingwiki.patterns import getgraphdata

from raippa import RaippaUser
from raippa import FlowPage
from raippa import Question

answercategory = u'CategoryAnswer'
usercategory = u'CategoryUser'
coursecategory = u'CategoryCourse'
taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
historycategory = u'CategoryHistory'

def getanswers(request, questionpage):
    page = request.globaldata.getpage(questionpage)
    linking_in = page.get('in', {})
    pagelist = linking_in["question"]

    answerlist = list()

    for page in pagelist:
        metas = getmetas(request, request.globaldata, page, [u'WikiCategory', u'true', u'false'], checkAccess=False)
        for metatuple in metas[u'WikiCategory']:
            category = metatuple[0]
            if category == answercategory:
                if metas[u'true']:
                    answerlist.append(metas[u'true'][0][0])
                if metas[u'false']:
                    answerlist.append(metas[u'false'][0][0])

    return answerlist

def getattachments(request, pagename):
    attach_dir = getAttachDir(request, pagename)
    if os.path.isdir(attach_dir):
        files = map(lambda a: a.decode(config.charset), os.listdir(attach_dir))
        files.sort()
        return files
    return [] 

def questionhtml(request, questionpage, number=""):
    html = unicode()
    note = unicode()
    social = False

    meta = getmetas(request, request.globaldata, encode(questionpage), [u'question', u'answertype', u'note'], checkAccess=False)

    question = meta[u'question'][0][0]
    answertype = meta[u'answertype'][0][0]
    if meta[u'note']:
        note = meta[u'note'][0][0]
        html += note + u'<br>\n'

    try:
        meta = getmetas(request, request.globaldata, encode(question), [u'WikiCategory', u'name'], checkAccess=False)
        for metatuple in meta[u'WikiCategory']:
            category = metatuple[0]
            if category == usercategory:
                name = meta[u'name'][0][0]
                social = True
    except:
        pass

    images = getattachments(request, questionpage)
    if images:
        image_url = request.getBaseURL() + u'/' + questionpage + u'?action=getAttachment&target=' + images[0]
        html += u'<img src="%s"><br>\n' % image_url

    
    if answertype == u'radio':
        answerlist = getanswers(request, questionpage)
        if social: 
            if request.user.name != question:
                answerlist.sort()
                html += name + u'<br>\n'
                for answer in answerlist:
                    html += u'<input type="radio" name="answer%s" value="%s"> %s\n' % (str(number), answer, answer)
                html += u'<br><hr>\n'
            else:
                html += u'<input type="hidden" name="answer%s" value="%s">\n' % (str(number), answerlist[0])
        else:
            random.shuffle(answerlist)
            html += question + u'<br>\n'
            for answer in answerlist:
                html += u'<input type="radio" name="answer%s" value="%s"> %s<br>\n' % (str(number), answer, answer)
            html += u'<br><hr>\n'

    elif answertype == u'checkbox':
        answerlist = getanswers(request, questionpage)
        random.shuffle(answerlist)
        html += question + u'<br>\n'
        for answer in answerlist:
            html += u'<input type="checkbox" name="answer%s" value="%s"> %s<br>\n' % (str(number), answer, answer)
        html += u'<br><hr>\n'
    elif answertype ==u'file':
        html += u'%s<br><input type="file" name="answer%s"><br><hr>\n' % (question, number)
    else:
        html += u'%s<br><input type="text" name="answer%s" size="50"><br><hr>\n' % (question, number)

    html += u'<br>'
    return html

def questionform(request):
    try:
        meta = getmetas(request, request.globaldata, encode(request.page.page_name), ["question"], checkAccess=False)
        questionpage = encode(meta["question"][0][0])
        meta = getmetas(request, request.globaldata, questionpage, ["answertype"], checkAccess=False)
        answertype = meta["answertype"][0][0]
    except:
        return u'Failed to generate question form.'

    if answertype == "file":
        page = request.globaldata.getpage(questionpage)
        linking_in = page.get('in', {})
        pagelist = linking_in["question"]
        for page in pagelist:
            meta = getmetas(request, request.globaldata, page, ["WikiCategory", "user", "overallvalue"], checkAccess=False)
            for category, type in meta["WikiCategory"]:
                if category == historycategory:
                    for user, type in meta["user"]:
                        if user == request.user.name:
                            for value, type in meta["overallvalue"]:
                                if value == "pending":
                                    return u'You have already answered this question. Waiting for your answer to be checked.'
                            break
                    break
        
    html = u'''
<form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="action" value="flowRider">
    %s
    <input type='submit' name='send' value='Submit'>
</form>''' % questionhtml(request, questionpage)

    return html

def taskform(request):
    currentpage = FlowPage(request, request.page.page_name, request.raippauser)
    html = unicode()
    disabled = unicode()
    prerequisites = currentpage.getprerequisite()
    if prerequisites:
        successdict = dict()
        for task in prerequisites:
            successdict[task] = False
            taskpage = FlowPage(request, task)
            lastquestion = Question(request, taskpage.getflow().pop()[1])
            for useranswer in lastquestion.gethistories():
                if useranswer[3] == request.raippauser.currentcourse and \
                useranswer[0] == request.raippauser.id and \
                useranswer[1] != "False":
                    successdict[task] = True
                    break

        html += u'prerequisites:<br>\n'
        for task, value in successdict.iteritems():
            if value == False:
                html += u'%s: MISSING<br>' % (task)
                disabled = u'disabled'
            else:
                html += u'%s: DONE<br>' % (task)

    if currentpage.type == u'exam' or currentpage.type == 'questionary':
        flow = currentpage.getflow()
        html += u'''
<form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="action" value="flowRider">'''
        questionnumber = 0
        for taskpoint, question in flow:
            html += questionhtml(request, question, questionnumber)
            questionnumber += 1
        html += u'''
    <input type="submit" name="send" value="Submit">
</form>'''
    else:
        html += u'''
<form method="POST">
    <input type="hidden" name="action" value="flowRider"><br>
    <input %s type='submit' name='start' value=Start><br>
</form>''' % disabled

    return html

def courselisthtml(request):
    request.globaldata.reverse_meta()
    vals_on_pages = request.globaldata.vals_on_pages

    courselist = set([])
    for page in vals_on_pages:
        if page == coursecategory:
            courselist.update(vals_on_pages[page])

    if request.user.name:
        if courselist:
            html = u'''
<form method="POST">
    <input type="hidden" name="action" value="flowRider">
    <select name="course">'''
            for page in courselist:
                metas = getmetas(request, request.globaldata, encode(page), [u'id', u'name'], checkAccess=False)
                id = metas[u'id'][0][0]
                name = metas[u'name'][0][0]
                html += u'<option value="%s">%s - %s\n' % (page, id, name)
            html += u'''
    </select>
    <br>
    <input type="submit" name="selectcourse" value="SelectCourse">
    <br>
</form>'''
        else:
            html = u'No courses in system.'
    else:
        html = u'Login or create user.'

    return html

def execute(macro, text):
    request = macro.request
    request.globaldata = getgraphdata(request)
    request.raippauser = RaippaUser(request)
    pagename = encode(request.page.page_name)
    html = str()
    
    #request.write(request.cfg.page_front_page)
    if pagename == u'RAIPPA':
        return courselisthtml(request) 
    else:
        metas = getmetas(request, request.globaldata, pagename, ["WikiCategory", "start"], checkAccess=False)
        for category, type in metas["WikiCategory"]:
            if category == coursecategory:
                if len(metas["start"]) > 1:
                    for startpoint, type, in metas["start"]:
                        html += u'''
<form method="POST">
    <input type="hidden" name="action" value="flowRider">
    <input type="hidden" name="userselection" value="%s">
    %s<input type='submit' name='start' value="Select"><br>
</form>''' % (startpoint, startpoint)
                else:
                    try:
                        statuspage = encode(request.user.name + "/status")
                        meta = getmetas(request, request.globaldata, statuspage, [pagename], checkAccess=False)
                        coursestate = meta[pagename][0][0]
                        if coursestate == u'end':
                            #return u'<br>You have already passed this course.'
                            buttontext = u'Restart'
                        else:
                            buttontext = u'Continue'
                    except:
                        buttontext = u'Start'

                    html = u'''
<form method="POST">
    <input type="hidden" name="action" value="flowRider"><br>
    <input type='submit' name='start' value=%s><br>
</form>''' % buttontext
                return html
            elif category == taskcategory:
                return taskform(request)
            elif category == taskpointcategory:
                return questionform(request)

        return u'Invalid page or category.'
