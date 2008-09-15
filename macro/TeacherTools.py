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
  <script type="text/javascript" src="%s/common/js/mootools-1.2-core-yc.js"></script>
<script type="text/javascript">
window.addEvent('domready', function(){
  var typesel = $('qtypesel');
  typesel.addEvent('change', function(){
      checkQtype();
    });

    checkQtype();
  });


function checkQtype(){
  var typesel = $('qtypesel');
  var qlist = $$('select[id^=q_type]');
  qlist.setStyle('display', 'none');
  qlist.value = '';
  var selected = $(typesel.value);
  if(selected){
    selected.setStyle('display','');
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
  var value = form.getChildren('select')[0].value;
  if(confirm('Do you really want to delete '+ value+'?')){
 form.grab(new Element('input', {
    'type' : 'hidden',
    'name' : 'delete',
    'value' : 'delete'
    }));

  form.submit();
  }
}
</script>'''  % request.cfg.url_prefix_static
    html += u'''
<table class="no_border">
<tr><td colspan="2">
Courses:
</td></tr>
<tr>
<td width="300px">
<form method="post" id="course_form"  action="%s">
    <input type="hidden"id="course_action" name="action" value="editCourse">
    <select size="1" name="course" class="maxwidth">''' % request.request_uri.split("?")[0]
    for page in courselist:
        listtext = unicode()
        metas = getmetas(request, request.globaldata, page, ["id", "name"])
        for id, type in metas["id"]:
            listtext += id
            break
        for name, type in metas["name"]:
            listtext += u' - ' + name
            break 
        html += u'<option name="course" value="%s">%s</option>\n' % (page.replace('"', '&quot;'), listtext)
    html += '''
    </select></td>
    <td>
    <input type='button' name='delete' value='delete'
    onclick="del_confirm('course_form');">
    <input type='submit' name='edit' value='edit'>
    <input type='submit' name='new' value='new'>
    <input type="button" value="stats" onclick="sel_stats();">
    </td>
</form>
</tr>
<tr><td colspan="2">
Tasks:
</td></tr>
<tr>
<td>
<form method="post" id="task_form" action="%s">
<input type="hidden" name="action" value="editTask">
    <select size="1" name="task" class="maxwidth">''' % request.request_uri.split("?")[0]
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, taskcategory)
    for page in pagelist:
        metas = getmetas(request, request.globaldata, page, ["title", "description"])
        if metas["title"]:
            for description, type in metas["title"]:
                break
        else:
            for description, type in metas["description"]:
                break
        html += u'<option name="task" value="%s">%s</option>\n' % (page.replace('"', '&quot;'), description)
    html += '''
    </select>
    </td>
    <td>
    <input type='button' name='delete' value='delete'
    onclick="del_confirm('task_form');">
    <input type='submit' name='edit' value='edit'>
    <input type='submit' name='new' value='new'>
    </td>
</form>
</tr>
'''
    html += u'''
<tr><td colspan="2">
Question type:
</td></tr>
<tr>
<td>
<form method="post" id="question_form" action="%s">
    <input type="hidden" name="action" value="editQuestion">''' % request.request_uri.split("?")[0]
    globaldata, pagelist, metakeys, styles = metatable_parseargs(request, questioncategory)
   
    typedict = {None:list()}    
    for page in pagelist:
            try:
                metas = getmetas(request, request.graphdata, encode(page), ["type", "question"])
                question = metas["question"][0][0]
                if metas["type"]:
                    for type, metatype in metas["type"]:
                        if not typedict.has_key(type):
                            typedict[type] = list()
                        typedict[type].append((page, question))
                else:
                    typedict[None].append((page, question))
            except:
                pass
    #typelist
    html += u'<select id="qtypesel" class="maxwidth" name="question_type">\n'
    for type in typedict:
        html += '<option value="q_type_%s">%s</option>\n' % (str(type).replace('"', '&quot;'), type)
    html += u'''</select></td><td>
</td></tr>
<tr><td colspan="2">
Questions:
</td></tr>
<tr><td>
'''

    #questionlists
    for type, questionlist in typedict.iteritems():
        html += u'''
<select  class="maxwidth" id="q_type_%s" name="questionList">\n''' % str(type).replace('"', '&quot;')
        for questionpagename, questiontext in questionlist:
            html += u'<option name="question" value="%s">%s</option>\n' % (questionpagename.replace('"', '&quot;'), questiontext)
        html += u'</select>\n'

    html += u'''
    </td><td>
    <input type='button' name='delete' value='delete'
    onclick="del_confirm('question_form')">
    <input type='button' name='edit' value='edit' onclick="submitQuestion();">
    <input type='submit' name='new' value='new'>
    </td>
</form>
</tr>
</table>
'''
    return html

def execute(macro, text):
    request = macro.request
    request.globaldata = getgraphdata(request)

    return coursesform(request)
