import os
import gv
from base64 import b64encode
from tempfile import mkstemp

from MoinMoin.Page import Page

from graphingwiki.editing import get_metas
from graphingwiki.editing import metatable_parseargs

from raippa import RaippaUser
from raippa import raippacategories
from raippa import getcourseusers, getflow, reporterror

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
                    tooltip = "../%s?action=drawchart&course=%s&task=%s&user=%s" % (pagename, course, task, str(user.user))
                    gv.setv(nodeobject, 'tooltip', tooltip)
            else:
               #TODO: user count here
                gv.setv(nodeobject, 'fillcolor', "darkolivegreen4")
                if task:
                    url = "../%s?action=raippaStats&course=%s&task=%s" % (pagename, course, task)
                    gv.setv(nodeobject, 'URL', url)
                    tooltip = "../%s?action=drawchart&course=%s&task=%s" % (pagename, course, task)
                    gv.setv(nodeobject, 'tooltip', tooltip)

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

def draw_ui(request, courses, course=None, user=None, compress=True, show_compress=True):

    currentuser = RaippaUser(request, request.user.name)

    html = u'''
<form method="POST" enctype="multipart/form-data" id="courses" action="%s">
<input type="hidden" name="action" value="raippaStats" onsubmit="return false;">
<select name="course">
''' % (request.page.page_name.split("/")[-1])

    for coursepage, coursename in courses.iteritems():
        if coursepage == course:
            html += u'<option selected value="%s">%s</option>\n' % (coursepage, coursename)
        else:
            html += u'<option value="%s">%s</option>\n' % (coursepage, coursename)

    html += u'</select>\n<input type="submit" name="send" value="Select course"><br>\n'

    if currentuser.isTeacher():
        if user:
            html += u'<select name="user">\n<option value="none">All</option>\n'
        else:
            html += u'<select name="user">\n<option selected value="none">All</option>\n'

        if course and course in courses.keys():
            coursepage = course

        for c_user in getcourseusers(request, coursepage):
            metas = get_metas(request, c_user, ["name"], checkAccess=False)
            if metas["name"]:
                username = u'- %s' % metas["name"].pop()
            else:
                username = unicode()

            if user and c_user == user.user: 
                html += u'<option selected value="%s">%s %s</option>\n' % (c_user, c_user, username)
            else:
                html += u'<option value="%s">%s %s</option>\n' % (c_user, c_user, username)
        html += u'</select>\n'
    else:
        html += u'<input type="hidden" name="user" value="%s">\n' % user.user

    html += u'<input type="submit" name="send" value="Select user"><br>\n'

    if show_compress:
        if compress:
            checked = u'checked'
        else:
            checked = unicode()
        html += u'''
Compress graph: <input type="checkbox" name="compress" %s onclick="this.form.submit();">\n
''' % checked

    html += u'''
</form>\n'''

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

    if not request.user.name:
        return u'<a href="?action=login">Login</a> or <a href="/UserPreferences">create user account</a>.'
    
    currentuser = RaippaUser(request, request.user.name)
    if not currentuser.isTeacher():
        user = RaippaUser(request, request.user.name)
    elif currentuser.isTeacher():
        user = None

    courses = getcourses(request, user)

    html = draw_ui(request, courses, user=user)

    if user and len(courses) < 1:
        html += u'User %s not in any course.<br>\n' % (user.user)
    elif not user and len(courses) < 1:
        html += u'No courses in Raippa.<br>\n'
    else: 
        if user:
            html += draw_coursestats(request, courses.keys()[0], user)
        else:
            html += u'''
<table border="1">
<tr>
  <td>%s</td>
  <td><img src="http://dev.raippa.fi/ecode/statistics?action=drawchart&&course=Course/521267A&task=Task/26271"/></td>
</tr>
</table>
''' % (draw_coursestats(request, courses.keys()[0]))

    return html 
