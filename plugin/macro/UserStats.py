import os
import gv
from base64 import b64encode
from tempfile import mkstemp

from MoinMoin.Page import Page

from graphingwiki.editing import get_metas

from raippa import RaippaUser
from raippa import getflow, reporterror

def draw_coursestats(request, course, user=None, compress=True):
    if user: 
        try:
            flow = getflow(request, course)
        except Exception, inst:
            exceptionargs = "".join(inst.args)
            reporterror(request, exceptionargs)
            return u'''
<h2>An Error Has Occurred</h2>
Error is reported to the admins. Please come back later.'''

        G = gv.digraph(str(course))
        gv.setv(G, 'rankdir', 'TB')
        gv.setv(G, 'bgcolor', 'transparent')
        if compress:
            gv.setv(G, 'ratio', "compress")
            gv.setv(G, 'size', "7.0, 6.0")
        nodes = dict()

        for node, nextlist in flow.iteritems():
            if node not in nodes.keys():
                nodes[node] = gv.node(G, str(node))

            for nextnode in nextlist:
                if nextnode not in nodes.keys():
                    nodes[nextnode] = gv.node(G, str(nextnode))
                gv.edge(nodes[node], nodes[nextnode])

        for node, nodeobject in nodes.iteritems():
            if node == "end" or node == "start":
                gv.setv(nodeobject, 'shape', "doublecircle")
            else:
                try:
                    value, reason = user.hasDone(node, course)
                except Exception, inst:
                    exceptionargs = "".join(inst.args)
                    reporterror(request, exceptionargs)
                    return u'''
<h2>An Error Has Occurred</h2>
Error is reported to the admins. Please come back later.'''
                if value:
                    gv.setv(nodeobject, 'fillcolor', "darkolivegreen4")
                else:
                    gv.setv(nodeobject, 'fillcolor', "steelblue3")
                url = "../%s" % (str(request.page.page_name))
                gv.setv(nodeobject, 'URL', url)
                gv.setv(nodeobject, 'style', "filled")
            gv.setv(nodeobject, 'label', "")

        gv.layout(G, 'dot')

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
<script type="text/javascript" src="%s/raippajs/mootools-1.2-more.js"></script><script type="text/javascript" src="%s/raippajs/calendar.js"></script>
<script type="text/javascript">
window.addEvent('domready', function(){
var links = $$('area');
var tips = new Tips(links);
if($('ttDate')){
  var calCss = new Asset.css("%s/raippa/css/calendar.css");
  var cal = new Calendar({    ttDate : 'Y-m-d'
    },{
      direction : -1,
      draggable : false
      });   }
});
</script>
<img src="data:image/png;base64,%s" usemap="#%s">
%s          
''' % (url_prefix, url_prefix, url_prefix, url_prefix, img, course, map)
        return html
    else:
        return course

def draw_ui(request, courses, user, selected=None, compress=True):
    if compress:
        compress = u'checked'
    else:
        compress = unicode()

    html = u'''
<form method="POST" enctype="multipart/form-data" action="%s">
<input type="hidden" name="action" value="userStats" onsubmit="return false;">
<input type="hidden" name="user" value="%s">
<input type="hidden" name="select">
<select name="course">
''' % (request.page.page_name.split("/")[-1], user.user)

    for coursepage, coursename in courses.iteritems():
        if not selected:
            selected = coursepage

        if coursepage == selected:
            html += u'<option selected value="%s">%s</option>\n' % (coursepage, coursename)
        else:
            html += u'<option value="%s">%s</option>\n' % (coursepage, coursename)

    html += u'''
</select>
<input type="submit" name="send" value="Select"><br>
Compress graph: <input type="checkbox" name="compress" %s onclick="this.form.submit();">
</form>
%s
''' % (compress, draw_coursestats(request, selected, user, compress))

    return html

def getcourses(request, user):
    courselist = user.getcourses()
    courses = dict()
    for coursepage in courselist:
        metas = get_metas(request, coursepage, ["id", "name"], display=True, checkAccess=False)

        coursename = unicode()
        if metas["id"]:
            coursename += metas["id"].pop()
        else:
            coursename += coursepage

        if metas["name"]:
            coursename += " - %s" % metas["name"].pop()

        courses[coursepage] = coursename

    return courses

def execute(macro, text):
    request = macro.request
    pagename = request.page.page_name 
    username = text

    user = RaippaUser(request, username)
    currentuser = RaippaUser(request, request.user.name)

    if user.user != currentuser.user and not currentuser.isTeacher():
        return u'You are not allowed to view users (%s) statistics.' % user.user

    courses = getcourses(request, user)
    return draw_ui(request, courses, user) 
