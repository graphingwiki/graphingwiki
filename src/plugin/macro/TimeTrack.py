from MoinMoin.Page import Page
from MoinMoin import wikiutil
from graphingwiki.editing import get_metas
from raippa import RaippaUser
import time

def calculate_hours(timetrack_entries):
    users_hours = [0,0]
    for key, info in timetrack_entries.iteritems():
        start = info[1].split(":")
        start[0] = int(start[0])
        start[1] = int(start[1])

        end = info[2].split(":")
        end[0] = int(end[0])
        end[1] = int(end[1])

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
    coursepage = text

    html = u'<h2>TimeTrack</h2>\n'

    if not request.user.name:
        html += u'<a href="?action=login">Login</a> or <a href="UserPreferences">create user account</a>.'
        return html

    if not Page(request, coursepage).exists():
        html += u'%s doesn\'t exist.' % coursepage
        return html

    user = RaippaUser(request)
    date_now = time.strftime("%Y-%m-%d")
    url_prefix = request.cfg.url_prefix_static
    tt_form_html = ''' 
<script type="text/javascript" src="%s/raippajs/mootools-1.2-core-yc.js"></script>
<script type="text/javascript" src="%s/raippajs/mootools-1.2-more.js"></script>
<script type="text/javascript" src="%s/raippajs/calendar.js"></script>
<script type="text/javascript">
addLoadEvent(function(){
if($('ttDate')){
  var calCss = new Asset.css("%s/raippa/css/calendar.css");
  var cal = new Calendar({
    ttDate : 'Y-m-d'
    },{
      direction : -1,
      draggable : false
      });
  $('tt_form').addClass('hidden');
}
});
function clearText(el){
    if(el.defaultValue == el.value){
        el.value = "";
        }
    }
</script>

    ''' % (url_prefix, url_prefix, url_prefix, url_prefix)
    tt_form_html += '''
    <div id="tt_form">
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
        <td><input name="start" value="HH:MM" maxlength="5" size=5"
        onfocus="clearText(this)"></td>
    </tr>
    <tr>
        <th>End time:</th>
        <td><input name="end" value="HH:MM" maxlength="5" size=5"
        onfocus="clearText(this)"></td>
    </tr>
    <tr>
        <th>Description:</th>
        <td><input name="description"></td>
    </tr>
    <tr>
        <th></th>
        <td><input type="submit" value="save" name="save"></td>
    </tr>
    </table>
    </form>
    </div>
    <a class="jslink" onclick="$('tt_form').toggleClass('hidden')">add new event</a>
    <br><br>
    ''' % (coursepage, date_now)
    html += tt_form_html
    user_entries = user.gettimetrack(coursepage)

#    html += u'<table border="1">\n'
    for key, info in user_entries.iteritems():
#        html += u'''
#<tr>
#  <td>%s</td>
#  <td>%s-%s</td>
#  <td>%s</td>
#</tr>\n''' % (info[0], info[1], info[2], info[3])
        html += "%s %s %s %s<br>\n" % (info[0], info[1], info[2], info[3])

    users_hours = calculate_hours(user_entries)
    html += "Total: %dh %dmin<br>\n" % (users_hours[0], users_hours[1])
#    html += u'<tr><td>Total:</td><td>%dh %dmin</td></tr>\n' % (users_hours[0], users_hours[1])
#    html += u'</table>\n'

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
            
            html += u'<br>%s group<br>\n' % group_name
            for group_member in users:
                if group_member != user.user:
                    member = RaippaUser(request, group_member)
                    member_entries = member.gettimetrack(coursepage)
                    member_hours = calculate_hours(member_entries)
                    html += u'%s %dh %dmin<br>\n' % (group_member, member_hours[0], member_hours[1])
                    group_hours[0] += member_hours[0]
                    group_hours[1] += member_hours[1]
                else:
                    html += u'%s %dh %dmin<br>\n' % (user.user, users_hours[0], users_hours[1])
                
            if group_hours[1]/60 > 0:
                group_hours[0] += (group_hours[1]/60)
                group_hours[1] = group_hours[1] - ((group_hours[1]/60) * 60)

            html += u'Total: %dh %dmin<br>\n' % (group_hours[0], group_hours[1])
            break
    
    return html
