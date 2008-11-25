# -*- coding: iso-8859-1 -*-
import os
import gv
from base64 import b64encode
from tempfile import mkstemp

from graphingwiki.editing import get_metas

from raippa import RaippaUser
from raippa import getflow, reporterror, pageexists

def draw(request, course, raippauser, result="both"):
    quarantined = raippauser.isQuarantined()

    G = gv.digraph(str(course))
    gv.setv(G, 'rankdir', 'LR')
    gv.setv(G, 'bgcolor', 'transparent')
    nodes = dict()
    try:
        flow = getflow(request, course)
    except Exception, inst:
        exceptionargs = "".join(inst.args)
        reporterror(request, exceptionargs)
        return u'''
<h2>An Error Has Occurred</h2>
Error is reported to the admins. Please come back later.'''

    for node, nextlist in flow.iteritems():
        if node not in nodes.keys():
            nodes[node] = gv.node(G, node)
        for nextnode in nextlist:
            if nextnode not in nodes.keys():
                nodes[nextnode] = gv.node(G, str(nextnode))
            gv.edge(nodes[node], nodes[nextnode])
    for node, nodeobject in nodes.iteritems():
        if node != "end" and node != "start":
            try:
                may, reason = raippauser.canDo(node, course)
            except Exception, inst:
                exceptionargs = "".join(inst.args)
                reporterror(request, exceptionargs)
                return u'''
<h2>An Error Has Occurred</h2>
Error is reported to the admins. Please come back later.'''

            if may:
                keys = ["deadline", "task"]
                nodemetas = get_metas(request, node, keys, display=True, checkAccess=False)
                node_deadline = str()
    
                if reason == "redo":
                    gv.setv(nodeobject, 'fillcolor', "chartreuse4")
                    gv.setv(nodeobject, 'label', "redo")
                else:
                    gv.setv(nodeobject, 'fillcolor', "steelblue3")
                    gv.setv(nodeobject, 'label', "select")

                    if nodemetas["deadline"]:
                        node_deadline = u'deadline: ' + nodemetas["deadline"].pop()
                        node_deadline = node_deadline.encode("ascii", "replace")

                if nodemetas["task"]:
                    task =  nodemetas["task"].pop()
                    if not quarantined:
                        url = "../%s?action=flowRider&select=%s&course=%s" % (str(request.page.page_name), str(task), str(course))
                        gv.setv(nodeobject, 'URL', url)

                    keys = ["description", "title"]
                    taskmeta = get_metas(request, task, keys, checkAccess=False)

                    if reason == "redo":
                        node_description = "You have passed this task but there is some questions you can do again if you want."
                    else:
                        if taskmeta["description"]:
                            node_description = taskmeta["description"].pop()
                        else:
                            node_description = str()
                    node_description = node_description.encode("ascii", "replace")

                    if taskmeta["title"]:
                        node_title =  taskmeta["title"].pop()
                    else:
                        node_title = str()
                    node_title = node_title.encode("ascii", "replace")

                    tooltip = "%s::%s<br>%s" %(node_title, node_description, node_deadline)
                    gv.setv(nodeobject, 'tooltip', tooltip)
                else:
                    gv.setv(nodeobject, 'tooltip', "Missing task link.")
            else:   
                if reason == "done":
                    gv.setv(nodeobject, 'label', "done")
                    gv.setv(nodeobject, 'fillcolor', "darkolivegreen4")
                    gv.setv(nodeobject, 'tooltip', "done::You have passed this task.")
                elif reason == "deadline":
                    gv.setv(nodeobject, 'label', "")
                    gv.setv(nodeobject, 'fillcolor', "firebrick")
                    tooltip = "Deadline::Deadline to this task is gone."
                    gv.setv(nodeobject, 'tooltip', tooltip)
                else:
                    gv.setv(nodeobject, 'label', "")
            gv.setv(nodeobject, 'style', "filled")
        else:
            gv.setv(nodeobject, 'shape', "doublecircle")
            gv.setv(nodeobject, 'label', "")
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
<script type="text/javascript" src="%s/raippajs/mootools-1.2-core-yc.js"></script>
<script type="text/javascript" src="%s/raippajs/mootools-1.2-more.js"></script>
<script type="text/javascript" src="%s/raippajs/calendar.js"></script>
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
<img src="data:image/png;base64,%s" usemap="#%s">
%s
''' % (url_prefix, url_prefix, url_prefix, url_prefix, img, course, map)

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

def execute(macro, text):
    request = macro.request
    

    if not text:
        reporterror(request, u"CourseGraph macro in %s does not have course page." % currentpage)
        return u'Missing course page.'

    if not request.user.name:
        return u'<a href="?action=login">Login</a> or <a href="UserPreferences">create user account</a>.'

    course = text
    if pageexists(request, course):
        ruser = RaippaUser(request)
        pagename = request.page.page_name
        html = unicode()
        if ruser.isTeacher():
            html += u'<a href="%s/%s?action=editCourse">[edit course]</a><br>\n' % (request.getBaseURL(), course)

        #check if user is quarantined
        if ruser.isQuarantined():
            html += u"You have been quarantined. You can't do tasks right now. Please come back later.<br>\n"

        #IE does not support base64 encoded images so we get it from drawgraphui action
        if 'MSIE' in request.getUserAgent():
            html += draw(request, course, ruser, result="map")
            html += u'<img src="%s/%s?action=drawgraphui&course=%s" usemap="#%s"><br>\n' % (request.getBaseURL(), pagename, course, course)
        else:
            html += draw(request, course, ruser)
        return html
    else:
        reporterror(request, u"The page %s used in %s does not exist." % (course, currentpage))
        return u'Page (%s) does not exist.' % course

