# -*- coding: utf-8 -*-"
action_name = 'editTimeTrackEntry'

import datetime
import re

from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page
from MoinMoin import wikiutil
from MoinMoin.parser.text_moin_wiki import Parser

from graphingwiki.editing import metatable_parseargs
from graphingwiki.editing import get_metas

from raippa import raippacategories as rc
from raippa import addlink, pages_in_category
from raippa.pages import Task

def _enter_page(request, pagename):
    _ = request.getText

    title = _('Calendar entry editor')

    request.emit_http_headers()
    request.theme.send_title(title, pagename=pagename, 
    html_head=u'''<link rel="stylesheet" type="text/css" charset="utf-8"
    media="all" href="%s/raippa/css/calendar.css">
    <script type="text/javascript" src="%s/raippajs/calendar.js"></script>
    ''' % (request.cfg.url_prefix_static, request.cfg.url_prefix_static))

    # Start content - IMPORTANT - without content div, there is no
    # direction support!

    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    
    request.page.formatter = formatter

    request.write(request.page.formatter.startContent("content"))


def _exit_page(request, pagename):
    request.write(request.page.formatter.endContent())

    request.theme.send_footer(pagename)


def savedata(request):
    date = request.form.get('start_date', [u''])[0]
    time = request.form.get('start_time', [u''])[0]
    duration = request.form.get('duration', [u''])[0]
    title = request.form.get('description', [u''])[0]
    task = request.form.get('task', [u''])[0]
    edit = request.form.get('edit', [u''])[0]
    category = request.form.get('categories', [rc['timetrack']])[0]
    if not category:
        category = rc['timetrack']

    daterexp = re.compile('\d{4}-\d\d-\d\d')
    timerexp = re.compile('([0-1][0-9]|2[0-3]):([0-5]\d|60)')
    durrexp = re.compile('\d+:([0-5]\d|60)')
    errors = unicode()

    if daterexp.match(date) is None:
        errors += u'Invalid date!\n'

    if timerexp.match(time) is None:
        errors += u'Invalid time!\n'

    if durrexp.match(duration) is None:
        errors += u'Invalid duration %s! Correct format is HH:MM\n' %s

    if not title:
        errors += u'Missing title!\n'

    if errors:
        return errors

    if edit:
        pagename = edit
    else:
        i = 0
        #generating unique pagename
        while True:
            pagename = u'%s/%s_%s' % (request.user.name, date, i)
            i += 1
            if not Page(request, pagename).exists():
                break

    content = u'%s\n----\n' % title 

    content += u' User:: %s\n' % addlink(request.user.name)

    if date:
        content += u' Date:: %s\n' % date
    if time:
        content += u' Time:: %s\n' % time
    if task:
        content += u' Task:: %s\n' % addlink(task)
    if duration:
        content += u' Duration:: %s\n' % duration
    if category:
        content += u'----\n%s' % category

    page = PageEditor(request, pagename)
    msg = page.saveText(content, page.get_real_rev())

def show_entryform(request):
    time_now = datetime.datetime.now() + datetime.timedelta(minutes=30)
    time_now -= datetime.timedelta(minutes=int(time_now.strftime("%M"))%30)
    def_date = time_now.strftime("%Y-%m-%d")
    def_time = time_now.strftime("%H:%M")
    duration = u'00:00'
    edit_page = u''
    title = u''
    time_opts = unicode()
    categories = categories = request.form.get('categories', [rc['timetrack']])[0]

    if request.form.has_key('date'):
        def_date = request.form.get('date')[0].encode()
    
    elif request.form.has_key('edit'):
        edit =  request.form.get('edit')[0].encode()
        edit_page = u'<input type="hidden" name="edit" value="%s">' % edit
        def_date = edit.split('_')[0]
        #categories = ','.join(categories)
        pagelist, metakeys, styles = metatable_parseargs(request, categories, get_all_keys=True)
        meta = get_metas(request, edit, metakeys, display=False, checkAccess=True)

        if meta[u'Date']:
            if meta.has_key(u'Duration'):
                try:
                    duration = meta[u'Duration'][0]
                except:
                    None

            if meta.has_key(u'Time'):
                try:
                    def_time = meta[u'Time'][0]
                except:
                    None

            body = PageEditor(request, edit).get_raw_body()
            if '----' in body:
                title = body.split('----')[0]

            temp = list()
            for line in title.split("\n"):
                if not line.startswith("#acl"):
                    temp.append(line)
            title = " ".join(temp)

    for h in range(24):
        for m in ['00','30']:
            t = u'"%02d:%s"' % (h,m)
            if t.find(def_time) != -1:
                t += ' selected'
            time_opts += u'<option value=%s>%02d:%s</option>\n' % (t,h,m)

    tasklist = unicode()
    for task in pages_in_category(request, rc['task']):
        tasktitle = Task(request, task).title()
        if not tasktitle:
            tasktitle = task

        tasklist += "    <option value='%s'>%s</option>\n" % (task, tasktitle)

        pass

    html = u'''
<script type="text/javascript">
window.addEvent('domready', function(){
  $('end-tr').setStyle('display', '');
 var Cal = new Class({
   Extends : Calendar,
   write : function(cal){
     this.parent(cal);
     setDuration('start_time');
     }
   });
 starcal = new Cal({
      start_date: 'Y-m-d',
      end_date : 'Y-m-d'
    },{
      direction : 0, 
      draggable : false, 
      offset : 1,
      pad:0
    });
  $$('#start_time, #end_time').addEvents({
    'change': function(){
        setDuration(this.id);
      },
    'keyup' : function(){
        setDuration(this.id);
      }
      });
  
  $('duration').addEvents({
      'change':function(){
            setDuration('start_time', true);
        }
  });

  setDuration('start_time', true);
});

function setDuration(absolute_time, reverse){
    var dur = $('duration');
    var start = $('start_time').value;
    var end = $('end_time').value;
    var start_date = $('start_date').value;
    var end_date = $('end_date').value;
    var other = $(absolute_time).id == "start_time" ? $('end_time') : $('start_time');

    var start_time = new Date();
    var end_time = new Date();
    start_time.setFullYear(start_date.split('-')[0].toInt());
    start_time.setMonth(start_date.split('-')[1].toInt()-1);
    start_time.setDate(start_date.split('-')[2].toInt());
    start_time.setHours(start.split(':')[0].toInt());
    start_time.setMinutes(start.split(':')[1].toInt());

    end_time.setFullYear(end_date.split('-')[0].toInt());
    end_time.setMonth(end_date.split('-')[1].toInt()-1);
    end_time.setDate(end_date.split('-')[2].toInt());
    end_time.setHours(end.split(':')[0].toInt());
    end_time.setMinutes(end.split(':')[1].toInt());

    var diff = end_time.valueOf() - start_time.valueOf();
    if(diff<0){
      $('end_date').set('value', start_date);
      diff = 0;
      }
    diff =  Math.floor(diff /60000);
    hours = Math.floor(diff/60);
    mins = diff - hours * 60;

    //setting end time based on duration and start time
    if(reverse == true){
        hours = (dur.value.split(':')[0] || 0).toInt();
        mins = (dur.value.split(':')[1] || 0).toInt();
        
        //fix incorrect formatting
        dur.value = hours < 10 ? '0' + hours : '' + hours;
        dur.value += mins <10 ? ':0' + mins : ':' + mins;

        if(hours > -1 && mins > -1){
          end_time = new Date(start_time.valueOf() + hours * 3600000 + mins * 60000);
          eh = end_time.getHours(); 
          eh = eh < 10 ? '0'+eh : eh;

          em = end_time.getMinutes();
          em = em < 10 ? '0'+em : em;

          eyear = end_time.getFullYear();
          eyear = eyear < 10 ? '0'+eyear : eyear;

          emonth = end_time.getMonth() + +1;
          emonth = emonth < 10 ? '0'+emonth : emonth;

          eday = end_time.getDate();
          eday = eday < 10 ? '0'+eday : eday;
          $('end_date').set('value',eyear +'-'+ emonth +'-' + eday);

          if(em != "00" && em != "30"){
            $('end_time').grab(new Element('option', {
              'value' : eh + ':' + em,
              'text' : eh + ':' + em
              }));
            }
          $('end_time').set('value', eh+ ':' +em);
        }
        return;
      }
 
    if(diff == 0){
        other.value = $(absolute_time).value;
        hours = mins = 0;
    }

      mins = mins < 10 ? "0" + mins : mins;
      hours = hours < 10 ? "0" + hours : hours;
      dur.set('value', hours + ':' + mins);

  }

function formcheck(){
  //setDuration('start_time');
  var desc = $('description');
  var dur = $('duration').value;
  
  if(desc.value.length < 1){
    alert('No description!');
    return false;
    }
  if(dur.test(/\d+:([0-5]\d|60)/) !== true){
    alert('Invalid duration ' + dur +'! Correct format is HH:MM');
    return false;
    }
  return true;
  }
</script>
<form id="entryform" method="post" onsubmit="return formcheck();">
<input type="hidden" name="action" value="%s">
<input type="hidden" name="categories" value="%s">
<!-- edit? -->
%s
<table>
<tr>
  <td>Description:</td>
  <td colspan="2"><input id="description" style="width:100%%" type="text"
  name="description" value="%s"></td>
</tr>
<tr>
  <td>Task:</td>
  <td colspan="2">
  <select name="task">
    <option value="" selected></option>
%s
  </select>
  </td>
</tr>
<tr>
  <td>Start:</td>
  <td nowrap><input type="text" id="start_date" name="start_date" value="%s"></td>
  <td><select id="start_time" name="start_time">
    %s
  </select></td>
</tr>
<tr id="end-tr" style="display:none;">
  <td>End:</td>
  <td><input type="text" id="end_date" name="end_date" value="%s"></td>
  <td><select id="end_time" name="end_time">
    %s
  </select></td>
</tr>
<tr>
  <td>Duration</td>
  <td colspan="2"><input id="duration" type="text" name="duration" value="%s"></td>
</tr>
</table>
<input type="submit" name="save" value="save">
''' % (action_name, request.form.get('categories',[u''])[0], edit_page, title, 
tasklist, def_date, time_opts, def_date, time_opts, duration)
    request.write(html)

def execute(pagename, request):
 
    if request.form.has_key('save'):
        errors = savedata(request)
        if errors:
            _enter_page(request, pagename)
            for error in errors:
               request.write(error)
            _exit_page(request, pagename)
            return None
        url = u'%s/%s?action=showTimeTrackEntries&date=%s&categories=%s' % (
        request.getBaseURL(), pagename, request.form.get('start_date',[None])[0], 
        request.form.get('categories',[None])[0])
        request.http_redirect(url)
    else:
        _enter_page(request, pagename)
        show_entryform(request)
        _exit_page(request, pagename)
