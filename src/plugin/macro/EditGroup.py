from MoinMoin.Page import Page
import MoinMoin.wikiutil as wikiutil

from graphingwiki.editing import get_metas

def getgrouphtml(request, groups, parentpage):
    course = parentpage
    html = u'Select group from the list or create new.<br>\n'
    html += u'<script type="text/javascript" src="%s/common/js/mootools-1.2-core-yc.js"></script>' %request.cfg.url_prefix_static
    html += u''' 
    <script type="text/javascript">
addLoadEvent(function(){
var gsel = $('groupsel');

if(gsel){
    gsel.addEvent('change', function(){
        $$('table[id^=groupActions_]').addClass('hidden');
        var new_group = $('new_group');
        new_group.addClass('hidden');

        var acttab = $('groupActions_'+ this.value);

        if(this.value == ""){
            new_group.removeClass('hidden');
        }else if(acttab){
            acttab.removeClass('hidden');
        }
    });
    gsel.addEvent('keyup', function(){
        this.fireEvent('change');
    });
    gsel.fireEvent('change');
    if(gsel.value){
        gsel.addClass('hidden');    
    }
}
});
    </script>
    '''
    usershtml = unicode()
    selecthtml = u'<select id="groupsel" name=grouppage class="maxwidth">\n'
    selecthtml += u'<option value="" selected>Create new</option>\n'

    for group in groups:
        meta = get_metas(request, group, ["name"])
        if meta["name"]:
            groupname = meta["name"].pop()
        else:
            groupname = group

        if request.user.name in groups[group]:
            selecthtml += u'<option value="%s" selected>%s</option>\n' % (group, groupname)
        else:
            selecthtml += u'<option value="%s">%s</option>\n' % (group, groupname)

        #create user tables
        usershtml += u'<table id="groupActions_%s" border="1" class="hidden" style="width:99%%">\n' % group
        usershtml += u'<tr class=maxwidth><th>%s</th></tr>\n' % groupname
        usershtml += u'<tr><td>'
        for user in groups[group]:
            usershtml += u'%s<br>\n' % user

        usershtml += u'</td></tr>'

        if request.user.name in groups[group]:
            usershtml += u'<tr><td><input type="submit" name="leave" value="leave">\n'
        else:
            usershtml += u'<tr><td><input type="submit" name="join" value="join">\n'

        usershtml += u'<input type="submit" name="delete" value="delete" onclick="return confirm(\'This will delete group\')"></td></tr>'
        usershtml += u'</table>'

    selecthtml += u'</select><br>\n'
    
    html += u'<div style="width: 150px"><form method="post">'
    html += u'<input type="hidden" name="action" value="editGroup">'
    html += selecthtml
    html += u'''<div id="new_group">
<input id="new_group_name" class="maxwidth" type="text" name="groupname" size="20"/><br>
<input type="submit" name="create" value="create">
</div>'''
    html += u'<input type="hidden" name="course" value="%s">' % course 
    html += usershtml
    html += u'</form></div>'

    return html

def execute(macro, text):
    request = macro.request
    pagename = request.page.page_name 
    parentpage = text

    if not request.user.name:
        return u'<a href="?action=login">Login</a> or <a href="UserPreferences">create user account</a>.'

    html = u'<h2>Group selector</h2>'

    if not Page(request, parentpage).exists():
        html += u'Parent %s doesn\'t exist.' % parentpage
        return html

    getgroups = wikiutil.importPlugin(request.cfg, "action", 'editGroup', 'getgroups')
    groups = getgroups(request, parentpage)
    
    html += getgrouphtml(request, groups, parentpage)
    return html
