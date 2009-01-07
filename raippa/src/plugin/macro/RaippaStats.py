import os
import gv
from base64 import b64encode
from tempfile import mkstemp

from MoinMoin.Page import Page

from graphingwiki.editing import get_metas
from graphingwiki.editing import metatable_parseargs

from raippa import RaippaUser
from raippa import raippacategories, getflow, reporterror

def draw_coursestats(request, course, user=None, compress=True):
    pagename = str(request.page.page_name)
    course = str(course)
    try:
        flow = getflow(request, course)
    except Exception, inst:
        exceptionargs = "".join(inst.args)
        reporterror(request, exceptionargs)
        return u'''
<h2>An Error Has Occurred</h2>
Error is reported to the admins. Please come back later.'''

    G = gv.digraph(course)
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
            metas = get_metas(request, node, ["task"], display=True, checkAccess=False)
            if metas["task"]:
                task = str(metas["task"].pop())
            else:
                reporterror(request, u"%s doesn't have task link." % node)
                task = None

            if user:
                try:
                    value, reason = user.hasDone(node, course)
                    if value:
                        gv.setv(nodeobject, 'fillcolor', "darkolivegreen4")
                    else:
                        gv.setv(nodeobject, 'fillcolor', "steelblue3")
                except Exception, inst:
                    exceptionargs = "".join(inst.args)
                    reporterror(request, exceptionargs)

                if task:
                    url = "../%s?action=raippaStats&course=%s&user=%s&task=%s" % (pagename, course, str(user.user), task)
                    gv.setv(nodeobject, 'URL', url)
            else:
               #TODO: user count here
                gv.setv(nodeobject, 'fillcolor', "darkolivegreen4")
                if task:
                    url = "../%s?action=raippaStats&course=%s&task=%s" % (pagename, course, task)
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
<img src="data:image/png;base64,%s" usemap="#%s">
%s          
''' % (img, course, map)
    return html

def draw_courselist(request, courses, user=None, selected=None, compress=True, show_compress=True):

    html = u'''
<form method="POST" enctype="multipart/form-data" id="courses" action="%s">
<input type="hidden" name="action" value="raippaStats" onsubmit="return false;">
<select name="course">
''' % (request.page.page_name.split("/")[-1])

    for coursepage, coursename in courses.iteritems():
        if selected == coursepage:
            html += u'<option selected value="%s">%s</option>\n' % (coursepage, coursename)
        else:
            html += u'<option value="%s">%s</option>\n' % (coursepage, coursename)

    html += u'''
</select>
<input type="submit" name="send" value="Show Graph"><br>
'''

    if user:
        html += u'<input type="hidden" name="user" value="%s">' % user.user

    if show_compress:
        if compress:
            checked = u'checked'
        else:
            checked = unicode()
        html += u'Compress graph: <input type="checkbox" name="compress" %s onclick="this.form.submit();">\n' % checked

    html += u'</form>\n'

    return html

def getcourses(request, user=None):
    if user:
        courselist = user.getcourses()
    else:
        courselist, keys, s = metatable_parseargs(request, raippacategories["coursecategory"], checkAccess=False)

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
    
    username = None
    taskpage = None
    coursepage = None

    for arg in text.split(","):
        if arg.strip().startswith("user="):
            username = arg.split("=")[1]
        elif arg.strip().startswith("course="):
            coursepage = arg.split("=")[1]

            if not Page(request, coursepage).exists():
                message = u'%s does not exist.' % coursepage
                Page(request, pagename).send_page(msg=message)
                return None

            metas = get_metas(request, coursepage, ["gwikicategory"], display=True, checkAccess=False)
            if raippacategories["coursecategory"] not in metas["gwikicategory"]:
                message = u'%s is not coursepage.' % coursepage
                Page(request, pagename).send_page(msg=message)
                return None

        elif arg.strip().startswith("task"):
            taskpage = arg.split("=")[1]

    currentuser = RaippaUser(request, request.user.name)
    if currentuser.user != username and not currentuser.isTeacher():
        return u'You are not allowed to view users (%s) statistics.' % username

    if username:
        user = RaippaUser(request, username)
        courses = getcourses(request, user)
    else:
        courses = getcourses(request)

    if coursepage and coursepage not in courses.keys():
        return u'%s not in courselist.' % coursepage
    elif not coursepage:
        if len(courses.keys()) > 0:
            selected = courses.keys()[0]
        else:
            selected = None
    else:
        selected = coursepage

    if username:
        html = draw_courselist(request, courses, user, selected)
        if selected:
            html += draw_coursestats(request, selected, user)
    else:
        html = draw_courselist(request, courses, selected=selected)
        if selected:
            html += draw_coursestats(request, selected)

    return html 
