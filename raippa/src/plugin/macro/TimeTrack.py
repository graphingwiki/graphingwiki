from MoinMoin.Page import Page
from MoinMoin import wikiutil
from graphingwiki.editing import get_metas
from raippa import RaippaUser
from raippa import reporterror
import time

def calculate_hours(request, timetrack_entries):
    users_hours = [0,0]
    for key, info in timetrack_entries.iteritems():
        try:
            start = info[1].split(":")
            start[0] = int(start[0])
            start[1] = int(start[1])
        except:
            reporterror(request, "Invalid start time in page %s." % info[4])
            continue

        try:
            end = info[2].split(":")
            end[0] = int(end[0])
            end[1] = int(end[1])
        except:
            reporterror(request, "Invalid end time in page %s." % info[4])
            continue

        if start[0] < end[0]:
            if start[1] > end[1]:
                hours = end[0] - start[0] - 1
                minutes = (60 - start[1]) + end[1]
            else:
                hours = end[0] - start[0]
                minutes = end[1] - start[1]

        elif start[0] == end[0]:
            if start[1] <= end[1]:
                hours = 0
                minutes = end[1] - start[1]
            else:
                hours = 23
                minutes = (60 - start[1]) + end[1]
        else:
            if start[1] <= end[1]:
                hours = (24 - start[0]) + end[0]
                minutes = end[1] - start[1]
            else:
                hours = (23 - start[0]) + end[0]
                minutes = (60 - start[1]) + end[1]

        users_hours[0] += hours
        users_hours[1] += minutes

    if users_hours[1]/60 > 0:
        users_hours[0] += (users_hours[1]/60)
        users_hours[1] = users_hours[1] - ((users_hours[1]/60) * 60)

    return users_hours

def execute(macro, text):
    request = macro.request
    pagename = request.page.page_name 
    args = text.split(',')

    coursepage = unicode()
    username = unicode()
    types = list()

    for arg in args:
        if arg.strip().startswith("course="):
            coursepage = arg.split("=")[1]
        elif arg.strip().startswith("user="):
            username = arg.split("=")[1]
        elif arg.strip().startswith("types="):
            types = arg.split("=")[1].split(";")

    html = u'<h2>TimeTrack</h2>\n'

    if not coursepage:
        html += u'Missing course attribute.'
        return html

    if not request.user.name and not username:
        html += u'<a href="?action=login">Login</a> or <a href="/UserPreferences">create user account</a>.'
        return html

    if not Page(request, coursepage).exists():
        html += u'%s doesn\'t exist.' % coursepage
        return html

    if username:
        user = RaippaUser(request, user=username)
    else:
        user = RaippaUser(request)

    date_now = time.strftime("%Y-%m-%d")
    url_prefix = request.cfg.url_prefix_static
    types_html = u''

    if types:
        types_html = u'<tr><th>type:</th><td><select name="type">'
        for type in types:
            types_html += u'<option value="%s">%s</option>' % (type, type)

        types_html += u'</select></td></tr>'

    tt_form_html = u''' 
<script type="text/javascript" src="%s/raippajs/mootools-1.2-core-yc.js"></script>
<script type="text/javascript" src="%s/raippajs/mootools-1.2-more.js"></script>
<script type="text/javascript" src="%s/raippajs/calendar.js"></script>
<script type="text/javascript">
addLoadEvent(function(){
//window.addEvent('domready', function(){
if($('ttDate')){
  var calCss = new Asset.css("%s/raippa/css/calendar.css");
  var cal = new Calendar({
    ttDate : 'Y-m-d'
    },{
      direction : -1,
      draggable : false
      });
  
  $(document.body).getElements('div.tt_form').each(function(el){
     el.addClass('hidden');
      el.getElement('form').addEvent('submit', function(){

            var desc = this.getElement('input.desc');
            if(!desc.value || desc.value.length == 0){
                alert('Missing description!');
                return false;
                }
 
            var inputs = this.getElements('.time');
            for(i=0; i < 2; i++){
                    var val = inputs[i].value;
                    val = val.replace(".",":");
                    inputs[i].value = val;
                    if(/\d\d\:\d\d/.test(val) == false){
                        alert('Invalid start/end time!');
                        return false;
                        }
                }

         });
      });
  }
});
function clearText(el){
    if(el.defaultValue == el.value){
        el.value = "";
        }
    }
</script>
    ''' % (url_prefix, url_prefix, url_prefix, url_prefix)
    tt_form_html += u'''
    <div class="tt_form">
    <form method="post" action="">
    <input type="hidden" name="action" value="editTimetrack">
    <input type="hidden" name="course" value="%s">
    <table class="no_border">
    <tr>
        <th>Date:</th>
        <td><input id="ttDate" name="date" value="%s"></td>
    </tr>
    <tr>
        <th>Start time:</th>
        <td><input name="start" class="time" value="HH:MM" maxlength="5" size="6"
        onfocus="clearText(this)"></td>
    </tr>
    <tr>
        <th>End time:</th>
        <td><input class="time" name="end" value="HH:MM" maxlength="5" size="6"
        onfocus="clearText(this)"></td>
    </tr>
    <tr>
        <th>Description:</th>
        <td><input class="desc" name="description"></td>
    </tr>
    %s
    <tr>
        <th></th>
        <td><input type="submit" value="save" name="save"></td>
    </tr>
    </table>
    </form>
    </div>
    <a class="jslink" onclick="$(this).getPrevious('div').toggleClass('hidden')">add new event</a>
    <br><br>
    ''' % (coursepage, date_now, types_html)

    if (not username and request.user.name) or (request.user.name == username):
        html += tt_form_html

    user_entries = user.gettimetrack(coursepage)

    dates = user_entries.keys()
    dates.sort()
    for key in dates:
        info = user_entries[key]
        page = info[4]
        meta = get_metas(request, page, ["type"], checkAccess=False)
        type = unicode()
        if meta["type"]:
            type = meta["type"].pop()

        html += "%s %s-%s %s: %s<br>\n" % (info[0], info[1], info[2], type, info[3])

    users_hours = calculate_hours(request, user_entries)
    html += "Total: %dh %dmin<br>\n" % (users_hours[0], users_hours[1])

    getgroups = wikiutil.importPlugin(request.cfg, "action", 'editGroup', 'getgroups')
    groups = getgroups(request, coursepage)

    for group, users in groups.iteritems():
        if user.user in users:
            group_hours = users_hours[:]
            metas = get_metas(request, group, ["name"], checkAccess=False)
            if metas["name"]:
                group_name = metas["name"].pop()
            else:
                group_name = group
            
            html += u'<br><b>%s group</b><br>\n' % group_name
            for group_member in users:
                if group_member != user.user:
                    member = RaippaUser(request, group_member)
                    member_entries = member.gettimetrack(coursepage)
                    member_hours = calculate_hours(request, member_entries)
                    html += u'%s: %dh %dmin<br>\n' % (group_member, member_hours[0], member_hours[1])
                    group_hours[0] += member_hours[0]
                    group_hours[1] += member_hours[1]
                else:
                    html += u'%s: %dh %dmin<br>\n' % (user.user, users_hours[0], users_hours[1])
                
            if group_hours[1]/60 > 0:
                group_hours[0] += (group_hours[1]/60)
                group_hours[1] = group_hours[1] - ((group_hours[1]/60) * 60)

            html += u'Total: %dh %dmin<br>\n' % (group_hours[0], group_hours[1])
            break
    
    return html
