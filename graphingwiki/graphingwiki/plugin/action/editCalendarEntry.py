# -*- coding: utf-8 -*-"
action_name = 'editCalendarEntry'

import datetime
import re

from MoinMoin.Page import Page
from MoinMoin import wikiutil
from MoinMoin.parser.text_moin_wiki import Parser

from graphingwiki.editing import order_meta_input, savetext
from graphingwiki.editing import metatable_parseargs, getmetas
from graphingwiki.patterns import getgraphdata

def _enter_page(request, pagename):
    request.http_headers()
    _ = request.getText

    title = _('Calendar entry editor')

    request.theme.send_title(title, pagename=pagename, 
    html_head=u'''<link rel="stylesheet" type="text/css" charset="utf-8"
    media="all" href="%s/raippa/css/calendar.css">
    <script type="text/javascript" src="%s/common/js/mootools-1.2-core-yc.js"></script>
    <script type="text/javascript" src="%s/common/js/calendar.js"></script>
    ''' % (request.cfg.url_prefix_static, request.cfg.url_prefix_static, request.cfg.url_prefix_static))

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
    type = request.form.get('type', [u''])[0]
    until = request.form.get('until', [u''])[0]
    edit = request.form.get('edit', [u''])[0]
    category = request.form.get('categories', [u'CategoryCalendarEntry'])[0]
    location = request.form.get('location', [u''])[0]
    capacity = request.form.get('capacity', [u''])[0]

    daterexp = re.compile('\d{4}-\d\d-\d\d')
    timerexp = re.compile('([0-1][0-9]|2[0-3]):([0-5]\d|60)')
    errors = unicode()

    if daterexp.match(date) is None:
        errors += u'Invalid date!\n'

    if timerexp.match(time) is None:
        errors += u'Invalid time!\n'

    if not title:
        errors += u'Missing title!\n'

    if errors:
        return errors

    i = 0
    #generating unique pagename
    while True:
        pagename = u'%s_%s' % (date,i)
        i += 1
        if not Page(request, pagename).exists():
            break

    if edit:
        pagename = edit

    content = u'''%s
----
  Date:: %s
  Time:: %s
  Duration:: %s
  Type:: %s
  Until:: %s
  Location:: %s
  Capacity:: %s

%s''' % (title, date, time, duration, type, until, location, capacity, category)
    savetext(pagename, content)

def show_entryform(request):
    time_now = datetime.datetime.now() + datetime.timedelta(minutes=30)
    time_now -= datetime.timedelta(minutes=int(time_now.strftime("%M"))%30)
    def_date = time_now.strftime("%Y-%m-%d")
    def_time = time_now.strftime("%H:%M")
    type = u'Once'
    duration = u'00:00'
    edit_page = u''
    title = u''
    capacity = unicode()
    location = unicode()
    until = ''
    time_opts = unicode()
    categories = categories = request.form.get('categories',
    ['CategoryCalendarEntry'])[0]

    if request.form.has_key('date'):
        def_date = request.form.get('date')[0].encode()
    
    elif request.form.has_key('edit'):
        edit =  request.form.get('edit')[0].encode()
        edit_page = u'<input type="hidden" name="edit" value="%s">' % edit
        def_date = edit.split('_')[0]
        #categories = ','.join(categories)
        globaldata, pagelist, metakeys, styles = metatable_parseargs(request, categories, get_all_keys=True)
        if not hasattr(request, 'graphdata'):
            getgraphdata(request)
        meta = getmetas(request, request.graphdata, edit, metakeys, display=False, checkAccess=True)

        if meta[u'Date']:
            if meta.has_key(u'Duration'):
                try:
                    duration = meta[u'Duration'][0][0]
                except:
                    None

            if meta.has_key(u'Capacity'):
                try:
                    capacity = meta[u'Capacity'][0][0]
                except:
                    None

            if meta.has_key(u'Location'):
                try:
                    location = meta[u'Location'][0][0]
                except:
                    None

            if meta.has_key(u'Time'):
                try:
                    def_time = meta[u'Time'][0][0]
                except:
                    None

            if meta.has_key(u'Type'):
                try:
                    type = meta[u'Type'][0][0]
                    until = meta[u'Until'][0][0]
                except:
                    type = u'Once'

            body = Page(request, edit).get_raw_body()
            if '----' in body:
                title = body.split('----')[0]

    for h in range(24):
        for m in ['00','30']:
            t = u'"%02d:%s"' % (h,m)
            if t.find(def_time) != -1:
                t += ' selected'
            time_opts += u'<option value=%s>%02d:%s</option>\n' % (t,h,m)
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
 untilcal = new Cal({
      until : 'Y-m-d',
      draggable : false
   });
  $$('#start_time, #end_time').addEvents({
    'change': function(){
        setDuration(this.id);
      },
    'keyup' : function(){
        setDuration(this.id);
      }
      });
  
  $('duration').addEvent('change',function(){
    setDuration('start_time', true);
  });

  $('type').addEvent('change', function(){
    repeatcheck();
 });

//loading old repeat type
var deftype = "%s";
$$('option[value='+deftype+']').each(function(el){
    el.selected = true;
});

  repeatcheck(true);
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
        hours = dur.value.split(':')[0].toInt();
        mins = dur.value.split(':')[1].toInt();
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
function repeatcheck(no_init){
  var rep = $('type');
  if(rep.value == 'Once'){
    $('until-tr').setStyle('display', 'none');
    if(!no_init){
      $('until').value = '';
    }
  }else{
    if(!no_init){
      $('until').value = $('end_date').value;
    }
    $('until-tr').setStyle('display', '');
  }
}

function formcheck(){
  //setDuration('start_time');
  var desc = $('description');
  if(desc.value.length < 1){
    alert('No description!');
    return false;
    }
  return true;
  }
</script>
<form id="entryform" method="post" onsubmit="return formcheck();">
<input type="hidden" name="action" value="%s">
<input type="hidden" name="backto" value="%s">
<input type="hidden" name="categories" value="%s">
<!-- edit? -->
%s
<table>
<tr>
  <td>Description:</td>
  <td colspan="2"><input id="description" style="width:100%%" type="text"
  name="description" value="%s">
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
<tr>
  <td>Location</td>
  <td colspan="2"><input id="location" type="text" name="location" value="%s"></td>
</tr>
<tr>
  <td>Capacity</td>
  <td colspan="2"><input id="capacity" type="text" name="capacity" size="4" value="%s"></td>
</tr>
<tr>
  <td>Repeat:</td>
  <td colspan="2"><select id="type" name="type">
    <option value="Once" selected>Does not repeat</option>
    <option value="1">Daily</option>
    <option value="7">Weekly</option>
    <option value="14">Bi-weekly</option>
    <option value="28">Every 4 weeks</option>
  </select>
  </td>
</tr>
<tr id="until-tr">
  <td>Until:</td>
  <td colspan="2"><input id="until" type="text" name="until" value="%s"></td>
</tr>
</table>
<input type="submit" name="save" value="save">
''' % (type, action_name, request.form.get('backto',[u''])[0],request.form.get('categories',[u''])[0],
edit_page, title, def_date, time_opts, def_date, time_opts, duration, location, capacity, until)
    request.write(html)


def execute(pagename, request):
    
    if request.form.has_key('save'):
        print request.form
        savedata(request)
        url = u'%s?action=showCalendarDate&date=%s&backto=%s&categories=%s' % (request.getBaseURL(),
        request.form.get('start_date',[None])[0], request.form.get('backto',[None])[0], 
        request.form.get('categories',[None])[0])
        request.http_redirect(url)

    else:
        _enter_page(request, pagename)
        show_entryform(request)

    _exit_page(request, pagename)
