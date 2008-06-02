# -*- coding: utf-8 -*-"
action_name = 'editQuestion'
import os
import random

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.action.AttachFile import getAttachDir

from graphingwiki.editing import getmetas
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import GraphData, encode
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input

usercategory = u'CategoryUser'
questioncategory = u'CategoryQuestion'
answercategory = u'CategoryAnswer'
tipcategory = u'CategoryTip'

def randompage(request, type):
    pagename = "%s/%i" % (type, random.randint(10000,99999))
    page = Page(request, pagename)
    while page.exists():
        pagename = "%s/%i" % (type, random.randint(10000,99999))
        page = Page(request, pagename)

    return pagename

def addlink(pagename):
    return '[['+pagename+']]'

def do_upload(request, pagename):
    filename = None
    if request.form.has_key('file__filename__'):
        filename = request.form['file__filename__']
        target = filename

    filecontent = request.form['file'][0]
    if len(target) > 1 and (target[1] == ':' or target[0] == '\\'):    
        bsindex = target.rfind('\\')
        if bsindex >= 0:
            target = target[bsindex+1:]        

    target = wikiutil.taintfilename(target)
    attach_dir = getAttachDir(request, pagename, create=1)
    fpath = os.path.join(attach_dir, target).encode(config.charset)
    exists = os.path.exists(fpath)
    if exists:
        try:
            os.remove(fpath)
        except:
            pass
    stream = open(fpath, 'wb')
    try:
        stream.write(filecontent)
    finally:
        stream.close()

def show_basicform(request):
#TODO: javasciprt: add more answers dynamically
#TODO: javascript: create answer UI dynamically depending on aswer type
 #TODO: javascript: if answer type is file, show select for manual or automatic checking
 #TODO: javascript: hide tip and show it only if answer value is False
    html = str()
    html += u'''
<form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="action" value="%s">
    question: <input type="text" name="question"><br>
    note: <input type="text" name="note"><br>
    image: <input type="file" name="file"/><br>
    <hr>
    answer type: <select name="answertype">
        <option value="radio">radio
        <option value="checkbox">checkbox
        <option value="text">text
        <option value="regexp">regexp
        <option value="file">file
    </select>''' % action_name

    for answernumber in range(1,6):
        html += '''
    <br>answer: <input type="text" name="answer%s">
    <input type="radio" name="value%s" value="true" checked>True
    <input type="radio" name="value%s" value="false">False
    tip: <input type="text" name="tip%s">
''' % (answernumber, answernumber, answernumber, answernumber)

    html += u'''
    <hr>
    <input type="submit" name="save" value="Save">
</form>'''

    request.write(html)

def show_socialform(request):
    globaldata, userlist, metakeys, styles = metatable_parseargs(request, usercategory)
    users = dict()
    for user in userlist:
        metas = getmetas(request, globaldata, encode(user), ["name"], checkAccess=False)
        if metas["name"]:
            users[user] = metas["name"][0][0]

    html = str()
    html += u'''
<form method="POST" enctype="multipart/form-data">
    <input type="hidden" name="action" value="%s">
    select user: <select name="question">''' % action_name
    for userpage in users:
        html += u'<option value="%s">%s\n' % (userpage, users[userpage])
    html += u'''
    </select><br>
    note: <input type="text" name="note"><br>
    <input type="hidden" name="answertype" value="radio">
    answer: <input type="text" name="answer1"><br>
    <input type="hidden" name="value1" value="true">

    answer: <input type="text" name="answer2"<br>
    <input type="hidden" name="value2" value="true">

    answer: <input type="text" name="answer3"><br>
    <input type="hidden" name="value3" value="true">
'''
    html += u'''
    <input type="submit" name="save" value="Save">
</form>'''

    request.write(html)

def show_typeselector(request):
    html = str()
    html += u'''
<form method="POST">
    <input type="hidden" name="action" value="%s">
    select question type: <select name="type">
        <option value="basic">basic text/image
        <option value="social">social questinary
    </select>
''' % action_name
    html += u'''
    <input type="submit" name="select" value="Select">
</form>'''

    request.write(html)

def writemetas(request,  questionpage=None, answerpage=None, tippage=None):
    #edit questionpage
    questiondata = {u'question': [request.form["question"][0]],
                    u'note': [request.form["note"][0]],
                    u'answertype': [request.form["answertype"][0]]}

    if questionpage:
        input = order_meta_input(request, questionpage, questiondata, "repl")
        process_edit(request, input)
    else:
        questionpage = randompage(request, "Question")
        input = order_meta_input(request, questionpage, questiondata, "add")
        process_edit(request, input, True, {questionpage:[questioncategory]})

    #find all the answers
    answerdict = dict()
    for key in request.form:
        if key != u'answertype' and key.startswith(u'answer'):
            answer = request.form[key][0]
            if not answer:
                continue
            answerpage = None
            answernumber = key[6:]
            value = request.form["value"+answernumber][0]
            tip = request.form.get("tip"+answernumber, [u''])[0]
            
            #edit answerpage
            answerdata = {u'question': [addlink(questionpage)]} 
            if value == u'true': 
                answerdata[u'true'] = [answer]
            else:
                answerdata[u'false'] = [answer]

            if answerpage:
                input = order_meta_input(request, answerpage, answerdata, "repl")
                process_edit(request, input)
            else:
                answerpage = randompage(request, "Answer")
                input = order_meta_input(request, answerpage, answerdata, "add")
                process_edit(request, input, True, {answerpage:[answercategory]})

            #edit tippage
            if value != u'true' and tip != u'':
                tipdata = {u'answer': [addlink(answerpage)],
                           u'tip': [tip]}
                if tippage:
                    input = order_meta_input(request, tippage, tipdata, "repl")
                    process_edit(request, input)
                else:
                    tippage = randompage(request, "Tip")
                    input = order_meta_input(request, tippage, tipdata, "add")
                    process_edit(request, input, True, {tippage:[tipcategory]})

    if request.form.get('file', [u''])[0]:
        do_upload(request, questionpage)

def _enter_page(request, pagename):
    request.http_headers()
    _ = request.getText
    
    request.theme.send_title(_('Teacher Tools'), formatted=False)
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter

    request.write(request.page.formatter.startContent("content"))

def _exit_page(request, pagename):
    # End content
    request.write(request.page.formatter.endContent())
    # Footer
    request.theme.send_footer(pagename)

def execute(pagename, request):
    #_ = request.getText
    #request.setContentLanguage(request.lang)
    if request.form.has_key('save'):
        writemetas(request)
        url = u'%s/%s?action=TeacherTools' % (request.getBaseURL(), pagename)
        request.http_redirect(url)
    elif request.form.has_key('type'):
        _enter_page(request, pagename)
        if request.form[u'type'][0] == u'social':
            show_socialform(request)
        else:
            show_basicform(request)
        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        show_typeselector(request)
        _exit_page(request, pagename)
