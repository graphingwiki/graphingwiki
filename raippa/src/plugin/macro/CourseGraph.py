# -*- coding: utf-8 -*-

import os, time
from base64 import b64encode
from tempfile import mkstemp

import gv 

from graphingwiki.editing import set_metas, get_metas
from graphingwiki.util import encode_page

from MoinMoin import config

from raippa.pages import Course, Task
from raippa.user import User
from raippa.stats import CourseStats, TaskStats
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
    graph = dict()
    flow = course.flow.fullflow()

    for taskpage, nextlist in flow.iteritems():
        if taskpage != 'first' and taskpage not in graph.keys():
            graph[taskpage] = dict()
        
            task = Task(request, taskpage)

            if user.is_teacher():
                graph[taskpage]['URL'] = taskpage
                graph[taskpage]['label'] = u'select'
                graph[taskpage]['fillcolor'] = u'steelblue3'
                graph[taskpage]['tooltip'] = task.title()
                #TODO: show deadline
            else:
                cando, reason = user.can_do(task)
          
                if cando:
                    if reason == "redo":
                        graph[taskpage]['label'] = u'redo'
                        graph[taskpage]['fillcolor'] = u'darkolivegreen4'
                        graph[taskpage]['tooltip'] = u'Done::You have passed this task but there is some questions you can do again if you want.'
                    else:
                        graph[taskpage]['label'] = u'select'
                        graph[taskpage]['fillcolor'] = u'steelblue3'
                        graph[taskpage]['tooltip'] = task.title()
                        #TODO: show deadline

                    graph[taskpage]['URL'] = taskpage

                else:
                    if reason == "done":
                        graph[taskpage]['label'] = u'done'
                        graph[taskpage]['fillcolor'] = u'darkolivegreen4'
                        graph[taskpage]['tooltip'] = u'Done::You have passed this task.'
                    elif reason == "deadline":
                        done, value = user.has_done(task)
                        if done:
                            graph[taskpage]['label'] = u'done'
                            graph[taskpage]['fillcolor'] = u'darkolivegreen4'
                            graph[taskpage]['tooltip'] = u'Done::You have passed this task.'
                        else:
                            graph[taskpage]['label'] = u''
                            graph[taskpage]['fillcolor'] = u'firebrick'
                            graph[taskpage]['tooltip'] = u'Deadline::Deadline to this task is gone.'
                    else:
                        graph[taskpage]['label'] = u''

            graph[taskpage]['next'] = nextlist
            graph[taskpage]['style'] = u'filled'

    return graph

def get_stat_data(request, course, user=None):
    graph = dict()
    flow = course.flow.fullflow()

    course_stats = CourseStats(request, course.config)
    students = course_stats.students()

    for taskpage, nextlist in flow.iteritems():
        if taskpage != 'first' and taskpage not in graph.keys():
            task = Task(request, taskpage)
            questions = task.questionlist()
            title = task.title()

            stats = TaskStats(request, taskpage)
            done, doing, rev_count = stats.students(user)

            max = int()

            for question, revs in rev_count.iteritems():
                for rev in revs:
                    if rev > max:
                        max = rev

            graph[taskpage] = dict()

            if user:
                done_questions = done.get(user.name, list())
                if len(done_questions) == len(questions):
                    graph[taskpage]['label'] = u'done'
                    tip = u"%s::Student has done all the questions in this task.<br>" % (title)
                else:
                    graph[taskpage]['label'] = u'%i/%i' % (len(done_questions), len(questions))
                    tip = u"%s::Student has done %i questions out of %i.<br>" % (title, len(done_questions), len(questions))

                if max <= 0:
                    graph[taskpage]['fillcolor'] = u'steelblue3'
                elif max <= 3:
                    graph[taskpage]['fillcolor'] = u'darkolivegreen4'
                elif max <= 6:
                    graph[taskpage]['fillcolor'] = u'gold'
                else:
                    graph[taskpage]['fillcolor'] = u'firebrick'

            else:
                done_all = list(set(done.keys()).difference(set(doing.keys())))
                graph[taskpage]['label'] = u'%i/%i' % (len(doing.keys()), len(done_all))
                tip = u"%s::%i students is doing this task and %i has passed it.<br>" % (title, len(doing), len(done_all))

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

def macro_CourseGraph(macro):
    request = macro.request
    formatter = macro.formatter
    page = macro.request.page
    pagename = macro.request.page.page_name

    if not request.user.name:
        return 

    user = User(request, request.user.name)
    teacher = user.is_teacher()

    course = Course(request, request.cfg.raippa_config)

    #set graphpage to config
    if teacher:
        metas = get_metas(request, course.config, ["graph"], checkAccess=False)

        if not metas.get("graph", list()):
            data = {course.config: {"graph": [addlink(pagename)]}}
            success, msg = set_metas(request, dict(), dict(), data)

    result = list()
    url_prefix = request.cfg.url_prefix_static

    tooltip = u'''
<script type="text/javascript" src="%s/raippajs/mootools-1.2-more.js"></script>
<script type="text/javascript" src="%s/raippajs/calendar.js"></script>
<script type="text/javascript">
addLoadEvent(function(){
//window.addEvent('domready', function(){
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
''' % (url_prefix, url_prefix, url_prefix)
    result.append(tooltip)

    if course.flow:
        #IE does not support base64 encoded images so we get it from drawgraphIE action
        if True: #'MSIE' in request.getUserAgent():
            url = u"%s/%s?action=drawgraphIE" % (request.getBaseURL(), pagename)
            map, tag = draw_graph(request, get_student_data(request, course, user), result='map')
            img = u'<img src="%s&type=student" usemap="#%s"><br>\n' % (url, tag)
            result.append(map)
            result.append(img)
            if teacher:
                map, tag = draw_graph(request, get_stat_data(request, course, None), result='map')
                img = u'<img src="%s&user=%s&type=stats" usemap="#%s"><br>\n' % (url, user.name, tag)
                result.append(map)
                result.append(img)
        else:
            html, tag = draw_graph(request, get_student_data(request, course, user))
            result.append(html)
            if teacher:
                result.append("stats ui:<br>")
                html, tag = draw_graph(request, get_stat_data(request, course, None))
                result.append(html)

        return u'\n'.join(result)
    else:
        return unicode()
