# -*- coding: utf-8 -*-

import os, time
from base64 import b64encode
from tempfile import mkstemp

import gv 

from graphingwiki.editing import set_metas, get_metas
from graphingwiki.util import encode_page

from MoinMoin.Page import Page
from MoinMoin.user import User as MoinUser
from MoinMoin.PageEditor import PageEditor
from MoinMoin import config

from raippa.pages import Course, Task, Question
from raippa.user import User
from raippa import addlink

def draw_graph(request, graphdict, result="both"):
    tag = str(time.time())
    G = gv.digraph(tag)
    gv.setv(G, 'charset', 'UTF-8')
    gv.setv(G, 'rankdir', 'TB')
    gv.setv(G, 'bgcolor', 'transparent')

    nodes = dict()
    for task, options in graphdict.iteritems():
        nextlist = options.get('next', list())
        if task not in nodes.keys():
            nodes[task] = gv.node(G, task.encode("utf8"))

        for nextnode in nextlist:
            if nextnode not in nodes.keys():
                nodes[nextnode] = gv.node(G, nextnode.encode("utf8"))
            gv.edge(nodes[task], nodes[nextnode])

        nodeobject = nodes[task]
        for option, value in options.iteritems():
            if option != 'next':
                gv.setv(nodeobject, option, value.encode("utf8"))

    gv.layout(G, 'dot')

    if result == "both":
        #map
        tmp_fileno, tmp_name = mkstemp()
        blob = gv.render(G, 'cmapx', tmp_name)
        
        f = file(tmp_name)
        map = f.read()
        map = map.decode('utf8')
        os.close(tmp_fileno)
        os.remove(tmp_name)

        #img
        tmp_fileno, tmp_name = mkstemp()
        glob = gv.render(G, 'png', tmp_name)
        f = file(tmp_name)
        img = b64encode(f.read())
        os.close(tmp_fileno)
        os.remove(tmp_name)
       
        html = u'''
<img src="data:image/png;base64,%s" usemap="#%s">
%s
''' % (img, tag, map)

        return html, tag
    elif result == "map":
        #map
        tmp_fileno, tmp_name = mkstemp()
        gv.render(G, 'cmapx', tmp_name)
        f = file(tmp_name)
        map = f.read()
        map = map.decode('utf8')
        os.close(tmp_fileno)
        os.remove(tmp_name)
        return map, tag
    else:
        #img
        tmp_fileno, tmp_name = mkstemp()
        gv.render(G, 'png', tmp_name)
        f = file(tmp_name)
        img = f.read()
        os.close(tmp_fileno)
        os.remove(tmp_name)
        return img, tag

def get_student_data(request, course, user):
    graph = {'first': dict()}
    flow = course.flow.fullflow()
    graph['first']['shape'] = 'point'
    graph['first']['next'] = flow.get('first', list())

    for taskpage, nextlist in flow.iteritems():
        if taskpage != 'first' and taskpage not in graph.keys():
            graph[taskpage] = dict()
        
            task = Task(request, taskpage)
            deadline, deadlines = task.deadline()
            user_deadline = deadlines.get(user.name, None)

            tooltip = u'%s:: ' % task.title()

            if user.is_teacher():
                graph[taskpage]['URL'] = u"%s/%s" % (request.getBaseURL(), taskpage)
                graph[taskpage]['label'] = u'select'
                graph[taskpage]['fillcolor'] = u'steelblue3'
                if user_deadline:
                    tooltip += u'Your deadline: %s' % user_deadline
                elif deadline:
                    tooltip += u'Deadline: %s' % deadline

                graph[taskpage]['tooltip'] = tooltip
            else:
                cando, reason = user.can_do(task)
          
                if cando:
                    if reason == "redo":
                        graph[taskpage]['label'] = u'redo'
                        graph[taskpage]['fillcolor'] = u'darkolivegreen4'
                        tooltip += u'You have passed this task but there is some questions you can do again if you want.'
                        graph[taskpage]['tooltip'] = tooltip 
                    else:
                        graph[taskpage]['label'] = u'select'
                        graph[taskpage]['fillcolor'] = u'steelblue3'
                        if user_deadline:
                            tooltip += u'Your deadline: %s' % user_deadline
                        elif deadline:
                            tooltip += u'Deadline: %s' % deadline
                    
                        graph[taskpage]['tooltip'] = tooltip

                    graph[taskpage]['URL'] = u"%s/%s" % (request.getBaseURL(), taskpage)

                else:
                    if reason == "done":
                        graph[taskpage]['label'] = u'done'
                        graph[taskpage]['fillcolor'] = u'darkolivegreen4'
                        tooltip += u'You have passed this task.'
                        graph[taskpage]['tooltip'] = tooltip 
                    elif reason == "deadline":
                        done, value = user.has_done(task)
                        if done:
                            graph[taskpage]['label'] = u'done'
                            graph[taskpage]['fillcolor'] = u'firebrick'
                            tooltip += u'You have passed this task.<br>Deadline to this task is gone.'
                            graph[taskpage]['tooltip'] = tooltip 
                        else:
                            graph[taskpage]['label'] = u''
                            graph[taskpage]['fillcolor'] = u'firebrick'
                            if user_deadline:
                                tooltip += u'Your deadline: %s' % user_deadline
                            elif deadline:
                                tooltip += u'Deadline: %s' % deadline
                            tooltip += u'<br>Deadline to this task is gone.'
                            graph[taskpage]['tooltip'] = tooltip
                    else:
                        graph[taskpage]['label'] = u''

            graph[taskpage]['next'] = nextlist
            graph[taskpage]['style'] = u'filled'

    return graph

def get_stat_data(request, course, user=None):
    flow = course.flow.fullflow()
    graph = {'first': dict()}
    flow = course.flow.fullflow()
    graph['first']['shape'] = 'point'
    graph['first']['next'] = flow.get('first', list())


    for taskpage, nextlist in flow.iteritems():
        if taskpage != 'first' and taskpage not in graph.keys():
            task = Task(request, taskpage)
            questions = task.questionlist()
            title = task.title()
            done, doing, values = task.stats(user, totals=False)

            if values:
                max = values[0]
            else:
                max = int()

            tasktype = task.options().get('type', 'basic')
            graph[taskpage] = dict()

            if user:
                user_done = int()
                for question, students in done.iteritems():
                    if user.name in students.keys():
                        user_done += 1

                if user_done == len(questions):
                    graph[taskpage]['label'] = u'done'

                    if tasktype == 'exam':
                        tip = u"%s::Student has answered to all the questions in this exam.<br>" % (title)
                    elif tasktype == 'questionary':
                        tip = u"%s::Student has answered to all the questions in this questionary.<br>" % (title) 
                    else:
                        tip = u"%s::Student has done all the questions in this task.<br>" % (title)
                else:
                    graph[taskpage]['label'] = u'%i/%i' % (user_done, len(questions))
                    if tasktype == 'exam':
                        tip = u"%s::Student has answered %i questions out of %i in this exam.<br>" % (title, user_done, len(questions))
                    elif tasktype == 'questionary':
                        tip = u"%s::Student has answered %i questions out of %i in this questionary.<br>" % (title, user_done, len(questions))
                    else:
                        tip = u"%s::Student has done %i questions out of %i.<br>" % (title, user_done, len(questions))

            else:
                doing_users = list()
                for question, students in doing.iteritems():
                    doing_users.extend(students)
                doing_users = list(set(doing_users))

                done_all = list()
                for index, question in enumerate(questions):
                    if index == 0:
                        for student in done.get(question, list()):
                            if student not in doing_users:
                                done_all.append(student)
                    else:
                        for student in done_all:
                            if student not in done.get(question, list()):
                                try:
                                    done_all.remove(student)
                                except:
                                    pass
                                if student not in doing_users:
                                    doing_users.append(student)

                graph[taskpage]['label'] = u'%i|%i' % (len(doing_users), len(done_all))
                if tasktype == 'exam':
                   tip = u"%s::%i students has started this exam and %i has answered to all the questions.<br>" % (title, len(doing_users), len(done_all)) 
                elif tasktype == 'questionary':
                   tip = u"%s::%i students has started this questionary and %i has answered to all the questions.<br>" % (title, len(doing_users), len(done_all))
                else:
                   tip = u"%s::%i students is doing this task and %i has passed it.<br>" % (title, len(doing_users), len(done_all))

            if max <= 0:
                graph[taskpage]['fillcolor'] = u'steelblue3'
            elif max <= 3:
                graph[taskpage]['fillcolor'] = u'darkolivegreen4'
            elif max <= 6:
                graph[taskpage]['fillcolor'] = u'gold'
            else:
                graph[taskpage]['fillcolor'] = u'firebrick'

            graph[taskpage]['tooltip'] = tip
            graph[taskpage]['URL'] = taskpage
            graph[taskpage]['next'] = nextlist
            graph[taskpage]['style'] = u'filled'

    return graph

def draw_teacher_ui(request, course):
    result = list()
    f = request.formatter
    
    #editor

    prefix =request.cfg.url_prefix_static 

    result.append(f.rawHTML(''' 
 <script type="text/javascript" src="%s/raippajs/moocanvas.js"></script>
 <script type="text/javascript" src="%s/raippajs/stats.js"></script>
 <script type="text/javascript" src="%s/raippajs/course_edit.js"></script>
<script type="text/javascript">

var courseModalizer = new Class({
        Extends: modalizer,
        click : function() {
            this.els.fireEvent('close');
            var changed = false;
            this.els.each(function(el){
               if(el.hasClass('edited')) changed=true;
            });
            if (!changed || confirm('Discard changes and close course editor?')) {
               this.close();
            }

        }

});

function editor(view){
    var edit = new Element('div');
    var overall = $('statsBox').clone().removeClass('hidden'); 
    var statsdiv = new Element('div');
    var stats = new CourseStats(statsdiv,{
            'overallStats' : overall
        });
    var modal = new courseModalizer([edit, statsdiv], { 
        tabLabels : ["edit", "stats"],
        defTab : view
        });
    var editor = new courseEditor(edit);
    }
</script>
    <br>
    <a class="jslink" onclick="editor(0);">edit</a>
    &nbsp;
    <a class="jslink" onclick="editor(1);">stats</a>
    ''' % (prefix, prefix, prefix)))
    #stats
    result.append(f.div(1,css_class='hidden',id="statsBox"))
    if 'MSIE' in request.getUserAgent():
        url = u"%s/%s?action=drawgraphIE" % (request.getBaseURL(), request.page.page_name)
        user = User(request, request.cfg.raippa_config)
        map, tag = draw_graph(request, get_stat_data(request, course, None), result='map')
        img = u'<img src="%s&user=%s&type=stats" usemap="#%s"><br>\n' % (url, user.name, tag)
        html = map + u"\n" + img
        result.append(html)
    else:
        html, tag = draw_graph(request, get_stat_data(request, course, None))
        result.append(html)

    result.append(f.div(0))
    return result

def create_user_page(userpage, request):
    user = request.user
    template = Page(request, "StudentTemplate").get_raw_body()

    template = template.replace("email::", "email:: %s" % user.email)
    template = template.replace("name::", "name:: %s" % user.aliasname)

    page = PageEditor(request, userpage)

    page.saveText(template, page.get_real_rev())


def macro_CourseGraph(macro):
    request = macro.request
    formatter = macro.formatter
    page = macro.request.page
    pagename = macro.request.page.page_name

    if not request.user.name:
        return u'Login or create user.' 

    user = User(request, request.user.name)
    teacher = user.is_teacher()

    #find out if the user has an user page
    userpage = Page(request, request.user.name)
    if not userpage.exists():
        create_user_page(userpage.page_name, request)

    course = Course(request, request.cfg.raippa_config)

    #set graphpage to config
    if teacher:
        remove = {course.config: ['graph']}
        data = {course.config: {"graph": [addlink(pagename)]}}
        success, msg = set_metas(request, remove, dict(), data)

    result = list()
    url_prefix = request.cfg.url_prefix_static

    tooltip = u'''
<script type="text/javascript">
window.addEvent('domready', function(){
var links = $$('area');
var tips = new Tips(links);
});
</script>
'''
    result.append(tooltip)

    if course.flow:
        #IE does not support base64 encoded images so we get it from drawgraphIE action
        if 'MSIE' in request.getUserAgent():
            url = u"%s/%s?action=drawgraphIE" % (request.getBaseURL(), pagename)
            map, tag = draw_graph(request, get_student_data(request, course, user), result='map')
            img = u'<img src="%s&type=student" usemap="#%s"><br>\n' % (url, tag)
            result.append(map)
            result.append(img)
        else:
            html, tag = draw_graph(request, get_student_data(request, course, user))
            result.append(html)

        if teacher:
            result.extend(draw_teacher_ui(request, course))

        return u'\n'.join(result)
    else:
        return unicode()
