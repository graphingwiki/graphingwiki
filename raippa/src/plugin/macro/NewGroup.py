 # -*- coding: iso-8859-1 -*-
from raippa.user import User
from MoinMoin import user
from MoinMoin.Page import Page

generates_headings = False

def name_gui(request, f):
    result = list()
    result.append(f.rawHTML('<form method="post">'))
    result.append(f.rawHTML('<input type="hidden" name="action" value="newgroup">'))
    result.append(f.rawHTML('<input type="text" name="groupname">'))
    result.append(f.rawHTML('<input type="submit" name="submit" value="New Group">'))
    result.append(f.rawHTML('</form>'))

    return result

def macro_NewGroup(macro):
    request = macro.request
    formatter = macro.formatter
    page = macro.request.page
    pagename = macro.request.page.page_name
    page = macro.request.page

    result = list()

    user = User(request, request.user.name)
    if user.is_student() or user.is_teacher():
        result.extend(name_gui(request, formatter))

    return "".join(result) 
