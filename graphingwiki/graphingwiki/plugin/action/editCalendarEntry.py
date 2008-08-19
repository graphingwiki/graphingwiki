# -*- coding: utf-8 -*-"
action_name = 'editCalendarEntry'

import datetime
import re

from MoinMoin.Page import Page
from MoinMoin import wikiutil
from MoinMoin.parser.text_moin_wiki import Parser

from graphingwiki.editing import order_meta_input, savetext
from graphingwiki.editing import metatable_parseargs, getmetas

def _enter_page(request, pagename):
    request.http_headers()
    _ = request.getText

    title = _('Calendar entry editor')

    request.theme.send_title(title, pagename=pagename, 
    html_head=u'''<link rel="stylesheet" type="text/css" charset="utf-8"
    media="all" href="%s/modern/css/calendar.css">
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

    content = u'''%s
----
  Date:: %s
  Time:: %s
  Duration:: %s
  Type:: %s

CategoryCalendarEntry''' % (title, date,time,duration,type)
    savetext(pagename, content)

def show_entryform(request):
    time_now = datetime.datetime.now() + datetime.timedelta(minutes=30)
    time_now -= datetime.timedelta(minutes=int(time_now.strftime("%M"))%30)
    def_date = time_now.strftime("%Y-%m-%d")
    def_time = time_now.strftime("%H:%M")
    time_opts = unicode()
    if request.form.has_key('date'):
        def_date = request.form.get('date')[0].encode()

    for h in range(24):
        for m in ['00','30']:
            t = u'"%02d:%s"' % (h,m)
            if t.find(def_time) != -1:
                t += ' selected'
            time_opts += u'<option value=%s>%02d:%s</option>\n' % (t,h,m)
    html = u'''
<script type="text/javascript">
window.addEvent('domready', function(){
  starcal = new Calendar({
      start_date: 'Y-m-d',
      end_date : 'Y-m-d'
    },{
      direction : 1, draggable :
      false, offset : 1,
      pad:0
    });
  $$('#start_time, #end_time').addEvent('change', function(){
    var dur = $('duration');
    var start = $('start_time').value;
    var end = $('end_time').value;
    var start_date = $('start_date').value;
    var end_date = $('end_date').value;
    var other = this.id == "start_time" ? $('end_time') : $('start_time');

    var mins = parseInt(end.split(':')[1]) - parseInt(start.split(':')[1]);
    var hours = parseInt(end.split(':')[0]) - parseInt(start.split(':')[0]);
    if(mins <0){
      mins += 60;
      hours --;
      }
      if(start_date == end_date && hours < 0){
        other.value = this.value;
        hours = mins = 0;
        }
      mins = mins < 10 ? "0" + mins : mins;
      hours = hours < 10 ? "0" + hours : hours;
      dur.set('value', hours + ':' + mins);
    });
});
function formcheck(){
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
<table>
<tr>
  <td>Description:</td>
  <td colspan="2"><input id="description" style="width:100%%" type="text" name="description">
</tr>
<tr>
  <td>Start:</td>
  <td nowrap><input type="text" id="start_date" name="start_date" value="%s"></td>
  <td><select id="start_time" name="start_time">
    %s
  </select></td>
</tr>
<tr>
  <td>End:</td>
  <td><input type="text" id="end_date" name="end_date" value="%s"></td>
  <td><select id="end_time" name="end_time">
    %s
  </select></td>
</tr>
<tr>
  <td>Duration</td>
  <td colspan="2"><input id="duration" type="text" name="duration" value="00:00"></td>
</tr>
<tr>
  <td>Repeat:</td>
  <td colspan="2"><select name="type">
    <option value="Once" selected>Does not repeat</option>
    <option value="1">Daily</option>
    <option value="7">Weekly</option>
    <option value="14">Bi-weekly</option>
    <option value="28">Every 4 weeks</option>
  </select>
  </td>
</tr>
</table>
<input type="submit" name="save" value="save">
''' % (action_name, request.form.get('backto',[u''])[0],request.form.get('categories',[u''])[0],
def_date, time_opts, def_date, time_opts)
    request.write(html)


def execute(pagename, request):
    
    if request.form.has_key('save'):
        savedata(request)
        url = u'%s?action=showCalendarDate&date=%s&backto=%s&categories=%s' % (request.getBaseURL(),
        request.form.get('start_date',[None])[0], request.form.get('backto',[None])[0], 
        request.form.get('categories',[None])[0])
        request.http_redirect(url)

    else:
        _enter_page(request, pagename)
        show_entryform(request)

    _exit_page(request, pagename)
