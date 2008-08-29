from graphingwiki.editing import getmetas
from graphingwiki.patterns import encode
from graphingwiki.editing import metatable_parseargs
from graphingwiki.patterns import getgraphdata

coursecategory = u'CategoryCourse'
taskcategory = u'CategoryTask'
questioncategory = u'CategoryQuestion'

def coursesform(request):
    html = str()
    globaldata, courselist, metakeys, styles = metatable_parseargs(request, coursecategory)
    if courselist:
        html += u'''
Stats: 
<form method="POST">
    <input type="hidden" name="action" value="teacherTools">
    <select name="course">'''
        for page in courselist:
            listtext = unicode()
            metas = getmetas(request, request.globaldata, page, ["id", "name"])
            for id, type in metas["id"]:
                listtext += id
                break
            for name, type in metas["name"]:
                listtext += u' - ' + name
                break 
            html += u'<option value="%s">%s\n' % (page, listtext)
        html += u'''</select>
    <input type='submit' name='selectcourse' value='stats'>
</form>'''
    html += u'''
Courses:
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editCourse">
    <select size="1" name="course">''' % request.request_uri.split("?")[0]
    for page in courselist:
        listtext = unicode()
        metas = getmetas(request, request.globaldata, page, ["id", "name"])
        for id, type in metas["id"]:
            listtext += id
            break
        for name, type in metas["name"]:
            listtext += u' - ' + name
            break 
        html += u'<option name="course" value="%s">%s\n' % (page, listtext)
    html += '''
    </select>
    <input type='submit' name='delete' value='delete'>
    <input type='submit' name='edit' value='edit'>
    <input type='submit' name='new' value='new'>
</form>
Tasks:
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editTask">
    <select size="1" name="task">''' % request.request_uri.split("?")[0]
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, taskcategory)
    for page in pagelist:
        metas = getmetas(request, request.globaldata, page, ["description"])
        for description, type in metas["description"]:
            break
        html += u'<option name="task" value="%s">%s\n' % (page, description)
    html += '''
    </select>
    <input type='submit' name='delete' value='delete'>
    <input type='submit' name='edit' value='edit'>
    <input type='submit' name='new' value='new'>
</form>'''
    html += u'''
Questions:
<form method="POST" action="%s">
    <input type="hidden" name="action" value="editQuestion">
    <select name="question">''' % request.request_uri.split("?")[0]
    globaldata, questionlist, metakeys, styles = metatable_parseargs(request, questioncategory)
    for page in questionlist:
        metas = getmetas(request, request.globaldata, page, ["question"])
        for question, type in metas["question"]:
            break
        html += u'<option value="%s">%s\n' % (page, question)
    html += u'''</select>
    <input type='submit' name='delete' value='delete'>
    <input type='submit' name='edit' value='edit'>
    <input type='submit' name='new' value='new'>
</form>'''
    return html

def execute(macro, text):
    request = macro.request
    request.globaldata = getgraphdata(request)

    return coursesform(request)
