from graphingwiki.editing import get_metas
from graphingwiki.editing import metatable_parseargs

from raippa import RaippaUser
from raippa import raippacategories

def coursesform(request):
    html = unicode()
    courselist, metakeys, styles = metatable_parseargs(request,raippacategories["coursecategory"])
    if courselist:
        html += u'''
  <script type="text/javascript" src="%s/raippajs/mootools-1.2-core-yc.js"></script>
<script type="text/javascript">
window.addEvent('domready', function(){
  var qtypesel = $('qtypesel');
  qtypesel.addEvent('change', function(){
      checkType(qtypesel);
    });

    checkType(qtypesel);

   var ttypesel = $('ttypesel');
   ttypesel.addEvent('change', function(){
      checkType(ttypesel);
    });

    checkType(ttypesel);

  });


function checkType(sel){
  var typesel = $(sel);
  if(sel.id == 'qtypesel'){
    var qlist = $$('select[id^=q_type]');
  }else if(sel.id == 'ttypesel'){
    var qlist = $$('select[id^=t_type]');
  }
  qlist.setStyle('display', 'none');
  qlist.value = '';
  var selected = $(typesel.value);
  if(selected){
    selected.setStyle('display','');
  }
}


function submitTasks(){
  var typesel = $('ttypesel');
  var selected = $(typesel.value);
  var form = $('task_form');
  if(selected){
    var question = new Element('input', {
      'type' : 'hidden',
      'value':  selected.value,
      'name' : 'task'
      });
    var edit = new Element('input', {
      'type': 'hidden',
      'name' : 'edit',
      'value' : 'edit'
      });
  edit.inject(form);
  question.inject(form);
  form.submit();
  }
}


function submitQuestion(){
  var typesel = $('qtypesel');
  var selected = $(typesel.value);
  var form = $('question_form');
  if(selected){
    var question = new Element('input', {
      'type' : 'hidden',
      'value':  selected.value,
      'name' : 'question'
      });
    var edit = new Element('input', {
      'type': 'hidden',
      'name' : 'edit',
      'value' : 'edit'
      });
  edit.inject(form);
  question.inject(form);
  form.submit();
  }
}


function sel_stats(){
  $('course_action').set('value', 'teacherTools');
  var form = $('course_form');
  form.grab(new Element('input', {
    'type' : 'hidden',
    'name' : 'selectcourse',
    'value' : 'stats'
    }));
  form.submit();
  }

function del_confirm(form){
  var form = $(form);

  if(form.id != 'course_form'){
	var sel = $(form.getElements('select')[0].value);
  }else if(form){
	var sel = form.getElements('select')[0];
  }

  if(sel){
    var value = sel.value;
    var desc = $$('option[value='+value+']')[0].text;
    }else{
      return false;
      }
  if(confirm('Do you really want to delete "'+ desc+'"?')){
 form.grab(new Element('input', {
    'type' : 'hidden',
    'name' : 'delete',
    'value' : 'delete'
    }));
if(form.id == 'task_form'){
  var name = 'task';
  }else{
  var name = 'question';
    }

form.grab(new Element('input', {
  'type' : 'hidden',
  'name' : name,
  'value' : value
  }));
  form.submit();
  }
}

</script>'''  % request.cfg.url_prefix_static
    html += u'''
<form method="post" id="course_form"  action="%s">
<table class="no_border">
<tr>
<td style="width:200px">
</td>
<td colspan="2">
Courses:
</td></tr>
<tr>
<td style="width:200px">
</td>
<td style="width:300px;">
    <input type="hidden"id="course_action" name="action" value="EditCourse">
    <select size="1" name="course" class="maxwidth">''' % request.request_uri.split("?")[0]
    for page in courselist:
        listtext = unicode()
        metas = get_metas(request, page, ["id", "name"])

        if metas["id"]:
            listtext += metas["id"].pop()
        else:
            pass
            #TODO: handle missing id

        if metas["name"]:
            listtext += u' - ' + metas["name"].pop()
        else:
            pass
            #TODO: handle missing name

        html += u'<option value="%s">%s</option>\n' % (page.replace('"', '&quot;'), listtext)


    #TODO: better stats
    #<input type="button" value="stats" onclick="sel_stats();">
    html += '''
    </select></td>
    <td>
    <input type='button' name='delete' value='delete'
    onclick="del_confirm('course_form');">
    <input type='submit' name='edit' value='edit'>
    <input type='submit' name='new' value='new'>
    </td>
</tr>
</table>
</form>
'''

    pagelist, metakeys, styles = metatable_parseargs(request, raippacategories["taskcategory"])
    subjectdict = dict()
    for page in pagelist:
        metas = get_metas(request, page, ["title", "description", "subject"])
        if metas["title"]:
            description = metas["title"].pop()
        else:
            description = page+" (missing title)"

        if metas["subject"]:
            for subject in metas["subject"]:
                if not subjectdict.has_key(subject):
                    subjectdict[subject] = list()
                subjectdict[subject].append((page, description))
        else:
            if not subjectdict.has_key(None):
                subjectdict[None] = list()
            subjectdict[None].append((page, description))

    #subjectlist
    html += u'''
<form method="post" id="task_form" action="%s">
<table class="no_border">
<tr><td>
Tasks subjects:
</td><td colspan="2">
Tasks:
</td></tr>
<tr><td style="width:200px;">
''' % request.request_uri.split("?")[0]

    html += u'<select class="maxwidth" id="ttypesel" name="tasksubject">\n'

    for subject in subjectdict:
        html+=u'<option value="t_type_%s">%s</option>\n' % (subject, subject)

    html += u'''</select>
</td><td style="width:300px;">
'''
    #tasklists
    for subject, tasklist in subjectdict.iteritems():
        html += u'''<select  name="taskList" id="t_type_%s" class="maxwidth">\n''' % unicode(subject).replace('"','&quot;')
        for taskpagename, taskdescription in tasklist:
            html += u'<option value="%s">%s</option>\n' % (taskpagename, taskdescription)
        html += u'</select>\n'

    html += u'''
    </td>
    <td>
    <input type="hidden" name="action" value="EditTask">
    <input type='button' name='delete' value='delete'
    onclick="del_confirm('task_form');">
    <input type='button' name='edit' value='edit' onclick="submitTasks();">
    <input type='submit' name='new' value='new'>
    </td>
</tr>
</table>
</form>
'''
    html += u'''
<form method="post" id="question_form" action="%s">
<table class="no_border">
<tr><td>
Question type:
</td><td colspan="2">
Questions:
</td></tr>
<tr>
<td style="width:200px;">
    <input type="hidden" name="action" value="EditQuestion">''' % request.request_uri.split("?")[0]

    pagelist, metakeys, styles = metatable_parseargs(request,raippacategories["questioncategory"])
    typedict = dict()    
    for page in pagelist:
        metas = get_metas(request, page, ["type", "question"])
        if metas["question"]:
            question = metas["question"].pop()
        else:
            pass
            #TODO: handle missing question

        if metas["type"]:
            for type in metas["type"]:
                if not typedict.has_key(type):
                    typedict[type] = list()
                typedict[type].append((page, question))
        else:
            if not typedict.has_key(None):
                typedict[None] = list()
            typedict[None].append((page, question))

    #typelist
    html += u'<select id="qtypesel" class="maxwidth" name="question_type">\n'

    for type in typedict:
        html += '<option value="q_type_%s">%s</option>\n' % (unicode(type).replace('"', '&quot;'), type)

    html += u'''</select></td>
    <td style="width:300px">
'''

    #questionlists
    for type, questionlist in typedict.iteritems():
        html += u'''
<select  class="maxwidth" id="q_type_%s" name="questionList">\n''' % unicode(type).replace('"', '&quot;')
        for questionpagename, questiontext in questionlist:
            html += u'<option value="%s">%s</option>\n' % (questionpagename.replace('"', '&quot;'), questiontext)
        html += u'</select>\n'

    html += u'''
    </td><td>
    <input type='button' name='delete' value='delete'
    onclick="del_confirm('question_form')">
    <input type='button' name='edit' value='edit' onclick="submitQuestion();">
    <input type='submit' name='new' value='new'>
    </td>
</tr>
</table>
</form>
'''
    return html

def execute(macro, text):
    request = macro.request

    if not request.user.name:
        return u'<a href="?action=login">Login</a> or <a href="UserPreferences">create user account</a>.'

    ruser = RaippaUser(request)
    if not ruser.isTeacher():
        return u'You are not allowed to use TeacherTools.'

    return coursesform(request)

