import os, time
from base64 import b64encode
from tempfile import mkstemp

import gv 

from graphingwiki.util import encode
from graphingwiki.editing import set_metas, get_metas

from MoinMoin import config

from raippa.pages import Course, Task
from raippa.user import User
from raippa.stats import CourseStats, TaskStats
from raippa import addlink

def draw_graph(request, graphdict, result="both"):
    tag = str(time.time())
    G = gv.digraph(tag)
    gv.setv(G, 'rankdir', 'TB')
    gv.setv(G, 'bgcolor', 'transparent')

    nodes = dict()
    for task, options in graphdict.iteritems():
        nextlist = options.get('next', list())
        if task not in nodes.keys():
            nodes[task] = gv.node(G, str(task))

        for nextnode in nextlist:
            if nextnode not in nodes.keys():
                nodes[nextnode] = gv.node(G, str(nextnode))
            gv.edge(nodes[task], nodes[nextnode])

        nodeobject = nodes[task]
        for option, value in options.iteritems():
            if option != 'next':
                gv.setv(nodeobject, option, value)

    gv.layout(G, 'dot')

    if result == "both":
        #map
        tmp_fileno, tmp_name = mkstemp()
        gv.render(G, 'cmapx', tmp_name)
        f = file(tmp_name)
        map = f.read()
        os.close(tmp_fileno)
        os.remove(tmp_name)

        #img
        tmp_fileno, tmp_name = mkstemp()
        gv.render(G, 'png', tmp_name)
        f = file(tmp_name)
        img = b64encode(f.read())
        os.close(tmp_fileno)
        os.remove(tmp_name)
       
        url_prefix = request.cfg.url_prefix_static

        html = u'''
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
<img src="data:image/png;base64,%s" usemap="#%s">
%s
''' % (url_prefix, url_prefix, url_prefix, img, tag, map)

        return html
    elif result == "map":
        #map
        tmp_fileno, tmp_name = mkstemp()
        gv.render(G, 'cmapx', tmp_name)
        f = file(tmp_name)
        map = f.read()
        os.close(tmp_fileno)
        os.remove(tmp_name)
        return map
    else:
        #img
        tmp_fileno, tmp_name = mkstemp()
        gv.render(G, 'png', tmp_name)
        f = file(tmp_name)
        img = f.read()
        os.close(tmp_fileno)
        os.remove(tmp_name)
        return img

def get_student_data(request, course, user):
    graph = dict()
    flow = course.flow.fullflow()

    for taskpage, nextlist in flow.iteritems():
        if taskpage != 'first' and taskpage not in graph.keys():
            taskpage = str(taskpage)
            graph[taskpage] = dict()
        
            task = Task(request, taskpage)

            if user.is_teacher():
                graph[taskpage]['URL'] = taskpage
                graph[taskpage]['label'] = 'select'
                graph[taskpage]['fillcolor'] = 'steelblue3'
                graph[taskpage]['tooltip'] = task.title().encode("ascii", "replace")
                #TODO: show deadline
            else:
                cando, reason = user.can_do(task)
          
                if cando:
                    if reason == "redo":
                        graph[taskpage]['label'] = 'redo'
                        graph[taskpage]['fillcolor'] = 'darkolivegreen4'
                        graph[taskpage]['tooltip'] = 'Done::You have passed this task but there is some questions you can do again if you want.'
                    else:
                        graph[taskpage]['label'] = 'select'
                        graph[taskpage]['fillcolor'] = 'steelblue3'
                        graph[taskpage]['tooltip'] = task.title().encode("ascii", "replace")
                        #TODO: show deadline

                    graph[taskpage]['URL'] = taskpage
#                    from codecs import getencoder
#                    encoder = getencoder(config.charset)
#                    graph[taskpage]['tooltip'] = encoder('дце', 'replace')[0]

                else:
                    if reason == "done":
                        graph[taskpage]['label'] = 'done'
                        graph[taskpage]['fillcolor'] = 'darkolivegreen4'
                        graph[taskpage]['tooltip'] = 'Done::You have passed this task.'
                    elif reason == "deadline":
                        done, value = user.has_done(task)
                        if done:
                            graph[taskpage]['label'] = 'done'
                            graph[taskpage]['fillcolor'] = 'darkolivegreen4'
                            graph[taskpage]['tooltip'] = 'Done::You have passed this task.'
                        else:
                            graph[taskpage]['label'] = ''
                            graph[taskpage]['fillcolor'] = 'firebrick'
                            graph[taskpage]['tooltip'] = 'Deadline::Deadline to this task is gone.'
                    else:
                        graph[taskpage]['label'] = ''

            graph[taskpage]['next'] = nextlist
            graph[taskpage]['style'] = 'filled'

    return graph

def get_stat_data(request, course, user=None):
    graph = dict()
    flow = course.flow.fullflow()

    course_stats = CourseStats(request, course.config)
    students = course_stats.students()

    for taskpage, nextlist in flow.iteritems():
        if taskpage != 'first' and taskpage not in graph.keys():
            taskpage = str(taskpage)
            task = Task(request, taskpage)
            questions = task.questionlist()
            title = task.title().encode("ascii", "replace")

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
                    graph[taskpage]['label'] = 'done'
                    tip = "%s::Student has done all the questions in this task.<br>" % (title)
                else:
                    graph[taskpage]['label'] = '%i/%i' % (len(done_questions), len(questions))
                    tip = "%s::Student has done %i questions out of %i.<br>" % (title, len(done_questions), len(questions))

                if max <= 0:
                    graph[taskpage]['fillcolor'] = 'steelblue3'
                elif max <= 3:
                    graph[taskpage]['fillcolor'] = 'darkolivegreen4'
                elif max <= 6:
                    graph[taskpage]['fillcolor'] = 'gold'
                else:
                    graph[taskpage]['fillcolor'] = 'firebrick'

            else:
                done_all = list(set(done.keys()).difference(set(doing.keys())))
                graph[taskpage]['label'] = '%i/%i' % (len(doing.keys()), len(done_all))
                tip = "%s::%i students is doing this task and %i has passed it.<br>" % (title, len(doing), len(done_all))

            if max <= 0:
                graph[taskpage]['fillcolor'] = 'steelblue3'
            elif max <= 3:
                graph[taskpage]['fillcolor'] = 'darkolivegreen4'
            elif max <= 6:
                graph[taskpage]['fillcolor'] = 'gold'
            else:
                graph[taskpage]['fillcolor'] = 'firebrick'

            graph[taskpage]['tooltip'] = tip
            graph[taskpage]['URL'] = taskpage
            graph[taskpage]['next'] = nextlist
            graph[taskpage]['style'] = 'filled'

    return graph

def macro_CourseGraph(macro):
    request = macro.request
    formatter = macro.formatter
    page = macro.request.page
    pagename = macro.request.page.page_name

    user = User(request, request.user.name)
    teacher = user.is_teacher()

    course = Course(request, request.cfg.raippa_config)

    #set graphpage to config
    if teacher:
        metas = get_metas(request, course.config, ["graph"], display=True, checkAccess=False)

        if not metas.get("graph", list()):
            data = {course.config: {"graph": [addlink(pagename)]}}
            success, msg = set_metas(request, dict(), dict(), data)

    result = list()

    if course.flow:
        result.append(draw_graph(request, get_student_data(request, course, user)))
        if teacher:
            result.append("stats ui:<br>")
            result.append(draw_graph(request, get_stat_data(request, course, None)))

        return u'\n'.join(result)
    else:
        return unicode()
