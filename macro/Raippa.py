# -*- coding: iso-8859-1 -*-
import random
import os
import gv
import datetime

from tempfile import mkstemp
from base64 import b64encode

from MoinMoin import config
from MoinMoin.action.AttachFile import getAttachDir
from MoinMoin.Page import Page

from graphingwiki.editing import getmetas
from graphingwiki.editing import edit_meta
from graphingwiki.patterns import encode
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

def graphmap(request, page, raippauser):
    G = gv.digraph(page.pagename)
    gv.setv(G, 'rankdir', 'LR')
    gv.setv(G, 'bgcolor', 'transparent')
    nodes = dict()
    flow = page.getflow()
    for node, nextlist in flow.iteritems():
        if node not in nodes.keys():
            nodes[node] = gv.node(G, node)
        for nextnode in nextlist:
            if nextnode not in nodes.keys():
                nodes[nextnode] = gv.node(G, nextnode)
            gv.edge(nodes[node], nodes[nextnode])
    for node, nodeobject in nodes.iteritems():
        if node != "end" and node != "start":
            status = raippauser.statusdict.get(node, [])
            may = raippauser.canDo(node, raippauser.currentcourse)
            if may:
                gv.setv(nodeobject, 'fillcolor', "blue")
                url = "../%s?action=flowRider&userselection=%s&start" % (page.pagename, node)
                gv.setv(nodeobject, 'URL', url)
                gv.setv(nodeobject, 'label', "do now")
                metas = getmetas(request, request.graphdata, node, ["task"], checkAccess=False)
                node_title = unicode()
                node_description = unicode()
                if metas["task"]:
                    task = encode(metas["task"][0][0])
                    metas = getmetas(request, request.graphdata, task, ["description", "title"], checkAccess=False)
                    if metas["description"]:
                        node_description = metas["description"][0][0]
                    if metas["title"]:
                        node_title = metas["title"][0][0]
                tooltip = node_title.encode("ascii", "replace")+"::"+node_description.encode("ascii", "replace")
                gv.setv(nodeobject, 'tooltip', tooltip)
            elif "[[end]]" in status or "end" in status:
                gv.setv(nodeobject, 'label', "done")
                gv.setv(nodeobject, 'fillcolor', "green")
                #url = "../%s?action=flowRider&userselection=%s&start" % (page.pagename, node)
                #gv.setv(nodeobject, 'URL', url)
            else:
                gv.setv(nodeobject, 'label', "")
                #url = "../%s?action=flowRider&userselection=%s&start" % (page.pagename, node)
                #gv.setv(nodeobject, 'URL', url)
            gv.setv(nodeobject, 'style', "filled")
        else:
            gv.setv(nodeobject, 'shape', "doublecircle")
            gv.setv(nodeobject, 'label', "")
    gv.layout(G, 'dot')

    #map
    tmp_fileno, tmp_name = mkstemp()
    gv.render(G, 'cmapx', tmp_name)
    f = file(tmp_name)
    map = f.read()
    os.close(tmp_fileno)
    os.remove(tmp_name)

    html = u'''
<script type="text/javascript" src="%s/common/js/mootools-1.2-core-yc.js"></script>
<script type="text/javascript" src="%s/common/js/mootools-1.2-more.js"></script>
<script type="text/javascript" src="%s/common/js/calendar.js"></script>
<script type="text/javascript">
window.addEvent('domready', function(){
var links = $$('area');
var tips = new Tips(links);
if($('ttDate')){
  var calCss = new Asset.css("%s/raippa/css/calendar.css");
  var cal = new Calendar({
    ttDate : 'Y-m-d'
    },{
      direction : -1,
      draggable : false
      });
}
});
</script>
''' % (request.cfg.url_prefix_static, request.cfg.url_prefix_static, request.cfg.url_prefix_static, request.cfg.url_prefix_static)
    html += map+"\n"
    return html

def getanswers(request, questionpage):
    page = request.graphdata.getpage(questionpage)
    linking_in = page.get('in', {})
    pagelist = linking_in.get("question", [])

    answerlist = list()

    for page in pagelist:
        metas = getmetas(request, request.graphdata, page, ["WikiCategory", "true", "false"], checkAccess=False)
        for category, type in metas["WikiCategory"]:
            if category == answercategory:
                if metas["true"]:
                    for answer, type in metas["true"]:
                        if type == "link" and answer.startswith("mailto:"):
                            answer = answer[7:]
                        break
                    answerlist.append(answer)
                elif metas["false"]:
                    for answer, type in metas["false"]:
                        if type == "link" and answer.startswith("mailto:"):
                            answer = answer[7:]
                        break
                    answerlist.append(answer)
                break

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

    meta = getmetas(request, request.graphdata, encode(questionpage), [u'question', u'answertype', u'note'], checkAccess=False)

    question = meta[u'question'][0][0]
    answertype = meta[u'answertype'][0][0]
    if meta[u'note']:
        note = meta[u'note'][0][0]
        html += u'<i>%s</i><br>\n' % note

    try:
        meta = getmetas(request, request.graphdata, encode(question), [u'WikiCategory', u'name'], checkAccess=False)
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

    
    i = 0
    if answertype == u'radio':
        answerlist = getanswers(request, questionpage)
        if social: 
            if request.user.name != question:
                answerlist.sort()
                html += name + u'<br>\n'
                for answer in answerlist:
                    i += 1
                    id = "%s_%s" % (number, i)
                    html += u'''<input type="radio" name="answer%s" id="ans%s"
                    value="%s"><label for="ans%s"> %s</label>\n''' % (str(number), id, answer.replace('"','&quot;'), id, answer)
                html += u'<br><hr>\n'
            else:
                html += u'<input type="hidden" name="answer%s" value="%s">\n' % (str(number), answerlist[0].replace('"','&quot;'))
        else:
            random.shuffle(answerlist)
            html += u'<strong>%s</strong><br>\n' % question
            for answer in answerlist:
                i += 1
                id = "%s_%s" % (number, i)
                html += u'''<input type="radio" name="answer%s" id="ans%s"
                value="%s"><label for="ans%s"> %s</label><br>\n''' % (str(number), id, answer.replace('"','&quot;'), id, answer)
            html += u'<br><hr>\n'

    elif answertype == u'checkbox':
        answerlist = getanswers(request, questionpage)
        random.shuffle(answerlist)
        html += u'<strong>%s</strong><br>\n' % question
        for answer in answerlist:
            i += 1
            id = "%s_%s" % (number, i)
            html += u'''<input type="checkbox" id="ans%s" name="answer%s" value="%s"><label
            for="ans%s">%s</label><br>\n''' % (id, str(number), answer.replace('"','&quot;'), id,  answer)
        html += u'<br><hr>\n'
    elif answertype ==u'file':
        html += u'<strong>%s</strong><br><input type="file" name="answer%s"><br><hr>\n' % (question, number)
    else:
        html += u'<strong>%s</strong><br><input type="text" name="answer%s" size="50"><br><hr>\n' % (question, number)

    html += u'<br>'
    return html

def questionform(macro):
    request = macro.request
    try:
        meta = getmetas(request, request.graphdata, encode(request.page.page_name), ["question"], checkAccess=False)
        questionpage = encode(meta["question"][0][0])
        meta = getmetas(request, request.graphdata, questionpage, ["answertype"], checkAccess=False)
        answertype = meta["answertype"][0][0]
    except:
        return u'Failed to generate question form.'

    def submitform():
        return u'''
<form method="POST" enctype="multipart/form-data" action="%s">
    <input type="hidden" name="action" value="flowRider">
    %s
    <input type='submit' name='send' value='Submit'>
</form>''' % (request.page.page_name.split("/")[-1], questionhtml(request, questionpage))

    def includecomment(historypage):
        commentpage = historypage+"/comment"
        if Page(request, commentpage).exists():
            import MoinMoin.wikiutil as wikiutil
            includemacro = wikiutil.importPlugin(request.cfg, "macro", 'Include')

            return u'Comments:%s' % includemacro(macro, commentpage)
        else:
            return unicode()

    if answertype == "file":
        page = request.graphdata.getpage(questionpage)
        linking_in = page.get('in', {})
        pagelist = linking_in["question"]
        for page in pagelist:
            meta = getmetas(request, request.graphdata, page, ["WikiCategory", "user", "overallvalue"], checkAccess=False)
            for category, type in meta["WikiCategory"]:
                if category == historycategory:
                    for user, type in meta["user"]:
                        if user == request.user.name:
                            for value, type in meta["overallvalue"]:
                                #print meta, page
                                if value == "pending":
                                    return u'You have already answered this question. Waiting for your answer to be checked.\n' 
                                elif value and value != "pending" and value != "False":
                                    return u'''
You got %s right! Click Continue or submit new file.
<form method="POST" enctype="multipart/form-data" action="%s">
<input type="hidden" name="action" value="flowRider">
<input type='submit' name='next' value='Continue'>
</form>
%s
%s''' % (value, request.page.page_name.split("/")[-1], includecomment(page), submitform())
                                elif value == "False":
                                    return u'''
Your answer was incorrect! Try again.
%s
%s''' % (includecomment(page), submitform())
                            break
                    break
        
    return submitform() 

def taskform(request):
    currentpage = FlowPage(request, request.page.page_name)
    currentcoursepoint = FlowPage(request, request.raippauser.currentcoursepoint)
    html = unicode()
    disabled = unicode()
    prerequisites = currentcoursepoint.getprerequisite()
    if prerequisites:
        successdict = dict()
        for task in prerequisites:
            successdict[task] = False
            taskpage = FlowPage(request, task)
            lastquestion = Question(request, taskpage.getflow().pop()[1])
            for useranswer in lastquestion.gethistories():
                if useranswer[3] == request.raippauser.currentcourse and useranswer[0] == request.raippauser.id:
                    if taskpage.type == "exam" or taskpage.type == "questionary" or  useranswer[1] != "False":
                        successdict[task] = True
                        break

        prerequisitehtml = u'prerequisites:<br>\n'
        for task, value in successdict.iteritems():
            if value == False:
                prerequisitehtml += u'%s: MISSING<br>' % (task)
                disabled = u'disabled'
            else:
                prerequisitehtml += u'%s: DONE<br>' % (task)
        if disabled:
            html += prerequisitehtml

    if currentpage.type == u'exam' or currentpage.type == 'questionary':
        flow = currentpage.getflow()
        html += u'''
<form method="POST" enctype="multipart/form-data" action="%s">
    <input type="hidden" name="action" value="flowRider">''' % request.page.page_name.split("/")[-1] 
        questionnumber = 0
        for taskpoint, question in flow:
            html += questionhtml(request, question, questionnumber)
            questionnumber += 1
        html += u'''
    <input type="submit" name="send" value="Submit">
</form>'''
    else:
        html += u'''
<form method="POST" action="%s">
    <input type="hidden" name="action" value="flowRider"><br>
    <input %s type='submit' name='start' value=Start><br>
</form>''' % (request.page.page_name.split("/")[-1], disabled)

    return html

def courselisthtml(request):
    request.graphdata.reverse_meta()
    vals_on_pages = request.graphdata.vals_on_pages

    courselist = set([])
    for page in vals_on_pages:
        if page == coursecategory:
            courselist.update(vals_on_pages[page])

    if request.user.name:
        if courselist:
            html = u'''
<form method="POST" action="%s">
    <input type="hidden" name="action" value="flowRider">
    <select name="course">''' % request.page.page_name.split("/")[-1]
            for page in courselist:
                metas = getmetas(request, request.graphdata, encode(page), [u'id', u'name'], checkAccess=False)
                id = metas[u'id'][0][0]
                name = metas[u'name'][0][0]
                html += u'<option value="%s">%s - %s</option>\n' % (page.replace('"','&quot;'), id, name)
            html += u'''
    </select>
    <br>
    <input type="submit" name="selectcourse" value="SelectCourse">
    <br>
</form>'''
        else:
            html = u'No courses in system.'
    else:
        html = u'<a href="?action=login">Login</a> or <a href="UserPreferences">create user account</a>.'

    return html

def execute(macro, text):
    request = macro.request
    if not hasattr(request, 'graphdata'):
        getgraphdata(request)
    request.raippauser = RaippaUser(request)
    pagename = encode(request.page.page_name)
    html = str()
    
    #request.write(request.cfg.page_front_page)
    if pagename == "RAIPPA":
        userpage = Page(request, request.user.name)
        if request.user.name and not userpage.exists():
            msg = edit_meta(request, request.user.name, {"":""}, {"name":[request.user.aliasname]}, True, [usercategory])
        elif request.user.name and userpage.exists():
            metas = getmetas(request, request.graphdata, encode(request.user.name), ["name"], checkAccess=False)
            if not metas["name"]:
                msg = edit_meta(request, encode(request.user.name), {"":""}, {"name":[request.user.aliasname]})
        return courselisthtml(request) 
    else:
        metas = getmetas(request, request.graphdata, pagename, ["WikiCategory", "start", "option"], checkAccess=False)
        for category, type in metas["WikiCategory"]:
            if category == coursecategory:
                coursepage = FlowPage(request, pagename)
                html =  graphmap(request, coursepage, request.raippauser)
                html += "<img src='%s/%s?action=drawgraphui' usemap='#%s'><br>\n" % (request.getBaseURL(), pagename, pagename)
                for option, type in metas["option"]:
                    if option == "timetrack":
                        timetracklist = request.raippauser.gettimetrack(coursepage.pagename)
                        if timetracklist:
                            html += u'''
<hr><b>TimeTrack</b><br>
<table>\n'''
                            total = int()
                            for tt_description in timetracklist:
                                total += int(timetracklist[tt_description][1])
                                html += u'<tr><td>%s</td><td>%sh</td><td>%s</td></tr>\n' % (timetracklist[tt_description][0], timetracklist[tt_description][1], tt_description)

                            html += u'''
<tr><td>total:</td><td>%ih</td></tr>
</table>''' % total    
                        now = datetime.datetime.now()
                        tt_date = now.strftime("%Y-%m-%d")
                        html += u'''
<form method="POST">
    <input type="hidden" name="action" value="timetrack"><br>
    Date:
    <input type="text" id="ttDate" name="date" value="%s"><br>
    time in hours:
    <input type="text" size="4" name="hours"><br>
    description:<br>
    <input type="text" size="50" name="description"><br>
    <input type='submit' name='submit' value=Submit><br>
</form>'''  % tt_date
                return html
            elif category == taskcategory:
                return taskform(request)
            elif category == taskpointcategory:
                return questionform(macro)

        return u'Invalid page or category.'
