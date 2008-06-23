# -*- coding: iso-8859-1 -*-
import random
import os

from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin.Page import Page
from MoinMoin.action.AttachFile import getAttachDir

from graphingwiki.editing import metatable_parseargs
from graphingwiki.editing import getmetas
from graphingwiki.patterns import GraphData, encode

answercategory = u'CategoryAnswer'
usercategory = u'CategoryUser'
coursecategory = u'CategoryCourse'
taskcategory = u'CategoryTask'
taskpointcategory = u'CategoryTaskpoint'
historycategory = u'CategoryHistory'

def getanswers(request, questionpage):
    globaldata = GraphData(request)
    page = globaldata.getpage(questionpage)
    linking_in = page.get('in', {})
    pagelist = linking_in["question"]

    answerlist = list()

    for page in pagelist:
        metas = getmetas(request, globaldata, page, [u'WikiCategory', u'true', u'false'], checkAccess=False)
        for metatuple in metas[u'WikiCategory']:
            category = metatuple[0]
            if category == answercategory:
                if metas[u'true']:
                    answerlist.append(metas[u'true'][0][0])
                if metas[u'false']:
                    answerlist.append(metas[u'false'][0][0])

    globaldata.closedb()

    return answerlist

def getattachments(request, pagename):
    attach_dir = getAttachDir(request, pagename)
    if os.path.isdir(attach_dir):
        files = map(lambda a: a.decode(config.charset), os.listdir(attach_dir))
        files.sort()
        return files
    return [] 

def getflow(request, target):
    globaldata = GraphData(request)
    meta = getmetas(request, globaldata, encode(target), [u'start'], checkAccess=False)
    taskpoint = encode(meta[u'start'][0][0])
    flow = list()

    while taskpoint != u'end':
        meta = getmetas(request, globaldata, taskpoint, [u'question', u'next'], checkAccess=False)
        questionpage = encode(meta[u'question'][0][0])
        flow.append((questionpage, taskpoint))
        taskpoint = encode(meta[u'next'][0][0])

    globaldata.closedb()
    return flow

def questionhtml(request, questionpage, number=""):
    html = unicode()
    note = unicode()
    social = False

    globaldata = GraphData(request)
    meta = getmetas(request, globaldata, encode(questionpage), [u'question', u'answertype', u'note'], checkAccess=False)
    globaldata.closedb()

    question = meta[u'question'][0][0]
    answertype = meta[u'answertype'][0][0]
    if meta[u'note']:
        note = meta[u'note'][0][0]
        html += note + u'<br>\n'

    try:
        globaldata = GraphData(request)
        meta = getmetas(request, globaldata, encode(question), [u'WikiCategory', u'name'], checkAccess=False)
        globaldata.closedb()
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
    globaldata = GraphData(request)
    try:
        meta = getmetas(request, globaldata, encode(request.page.page_name), ["question"], checkAccess=False)
        questionpage = encode(meta["question"][0][0])
        meta = getmetas(request, globaldata, questionpage, ["answertype"], checkAccess=False)
        answertype = meta["answertype"][0][0]
        globaldata.closedb()
    except:
        globaldata.closedb()
        return u'Failed to generate question form.'

    if answertype == "file":
        globaldata = GraphData(request)
        page = globaldata.getpage(questionpage)
        linking_in = page.get('in', {})
        pagelist = linking_in["question"]
        for page in pagelist:
            meta = getmetas(request, globaldata, page, ["WikiCategory", "user", "overalvalue"], checkAccess=False)
            for category, type in meta["WikiCategory"]:
                if category == historycategory:
                    for user, type in meta["user"]:
                        if user == request.user.name:
                            for value, type in meta["overalvalue"]:
                                if value == "pending":
                                    return u'You have already answered this question. Waiting for your answer to be checked.'
                            break
                    break
        globaldata.closedb()
        
    html = u'''
<form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="action" value="flowRider">
    %s
    <input type='submit' name='send' value='Submit'>
</form>''' % questionhtml(request, questionpage)

    return html

def taskform(request):
    globaldata = GraphData(request)
    metas = getmetas(request, globaldata, encode(request.page.page_name), [u'type'], checkAccess=False)
    globaldata.closedb()
    if metas[u'type']:
        tasktype = metas[u'type'][0][0]
    else:
        tasktype = u'basic'

    if tasktype == u'exam' or tasktype == 'questionary':
        flow = getflow(request, request.page.page_name)
        html = u'''
<form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="action" value="flowRider">'''
        questionnumber = 0
        for question, flowpoint in flow:
            html += questionhtml(request, question, questionnumber)
            questionnumber += 1
        html += u'''
    <input type="submit" name="send" value="Submit">
</form>'''
    else:
        html = u'''
<form method="POST">
    <input type="hidden" name="action" value="flowRider"><br>
    <input type='submit' name='start' value=Start><br>
</form>'''

    return html

def courselisthtml(request):
    globaldata = GraphData(request)
    globaldata.reverse_meta()
    vals_on_pages = globaldata.vals_on_pages
    globaldata.closedb()

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
                globaldata = GraphData(request)
                metas = getmetas(request, globaldata, encode(page), [u'id', u'name'], checkAccess=False)
                globaldata.closedb()
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
    pagename = encode(request.page.page_name)
    
    #request.write(request.cfg.page_front_page)
    if pagename == u'RAIPPA':
        return courselisthtml(request) 
    else:
        globaldata = GraphData(request)
        meta = getmetas(request, globaldata, pagename, [u'WikiCategory'], checkAccess=False)
        globaldata.closedb()
        for metatuple in meta['WikiCategory']:
            category = metatuple[0]
            if category == coursecategory:
                globaldata = GraphData(request)
                try:
                    statuspage = encode(request.user.name + "/status")
                    meta = getmetas(request, globaldata, statuspage, [pagename], checkAccess=False)
                    coursestate = meta[pagename][0][0]
                    globaldata.closedb()
                    if coursestate == u'end':
                        #return u'<br>You have already passed this course.'
                        buttontext = u'Restart'
                    else:
                        buttontext = u'Continue'
                except:
                    globaldata.closedb()
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
