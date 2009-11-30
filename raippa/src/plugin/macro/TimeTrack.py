 # -*- coding: iso-8859-1 -*-
from raippa.user import User
from raippa import pages_in_category, users_in_group, removelink
from raippa import raippacategories as rc
from MoinMoin import user
from MoinMoin.Page import Page
from graphingwiki.editing import get_metas

generates_headings = False

def user_gui(request, f, user, entries, new_table=True):
    result = list()
    
    metas = get_metas(request, user, ['name'], checkAccess=False)
    username = removelink(metas.get('name', [""])[0])

    if new_table:
        result.append(f.table(1))

    result.append(f.table_row(1))

    result.append(f.table_cell(1))
    result.append(f.strong(1))
    result.append(f.text("%s (" % username))
    result.append(f.pagelink(1, user))
    result.append(f.text("%s" % user))
    result.append(f.pagelink(0, user))
    result.append(f.text(")"))
    result.append(f.strong(0))
    result.append(f.table_cell(0))

    result.append(f.table_cell(1))
    result.append(f.strong(1))
    result.append(f.text("Duration"))
    result.append(f.table_cell(0))
    result.append(f.strong(0))

    result.append(f.table_cell(1))
    result.append(f.strong(1))
    result.append(f.text("Task"))
    result.append(f.strong(0))

    result.append(f.table_cell(1))
    result.append(f.strong(1))
    result.append(f.text("Description"))
    result.append(f.strong(0))

    result.append(f.table_cell(0))
    result.append(f.table_row(0))

    hours = int()
    minutes = int()

    for entry in entries:
        result.append(f.table_row(1))
        result.append(f.table_cell(1))
        result.append(f.text(entry[0]))
        result.append(f.table_cell(0))

        result.append(f.table_cell(1))
        result.append(f.text(entry[1]))
        result.append(f.table_cell(0))

        hours += int(entry[1].split(":")[0])
        minutes += int(entry[1].split(":")[1])

        if minutes > 59:
            hours += 1
            minutes = minutes - 60

        task = removelink(entry[2])
        result.append(f.table_cell(1))
        result.append(f.pagelink(1, task))
        result.append(f.text("%s" % task))
        result.append(f.pagelink(0, task))
        result.append(f.table_cell(0))

        result.append(f.table_cell(1))
        result.append(f.text(entry[3]))
        result.append(f.table_cell(0))
        result.append(f.table_row(0))

    result.append(f.table_row(1))
    result.append(f.table_cell(1))
    result.append(f.text("total"))
    result.append(f.table_cell(0))
    result.append(f.table_cell(1))
    result.append(f.text("%.2i:%.2i" % (hours, minutes)))
    result.append(f.table_cell(0))
    result.append(f.table_row(0))

    if new_table:
        result.append(f.table(0))

    return result

def group_gui(request, f, entries):
    users = entries.keys()
    result = list()

    hours = int()
    minutes = int()

    for user in entries:
        result.extend(user_gui(request, f, user, entries[user], True))

        for entry in entries[user]:
            hours += int(entry[1].split(":")[0])
            minutes += int(entry[1].split(":")[1])

            if minutes > 59:
                hours += 1
                minutes = minutes - 60


    result.append(f.table(1))
    result.append(f.table_row(1))

    result.append(f.table_cell(1))
    result.append(f.strong(1))
    result.append(f.text("Group total:"))
    result.append(f.strong(0))
    result.append(f.table_cell(0))

    result.append(f.table_cell(1))
    result.append(f.strong(1))
    result.append(f.text("%.2i:%.2i" % (hours, minutes)))
    result.append(f.strong(0))
    result.append(f.table_cell(0))

    result.append(f.table_row(0))

    result.append(f.table(0))

    return result

def timetrack_entries(request, users):
    pages = pages_in_category(request, rc['timetrack'])
    temp = dict()
    keys = ['Date', 'Task','Time', 'Duration', 'User']

    for page in pages:
        metas = get_metas(request, page, keys, checkAccess=False)
        user = removelink(metas.get('User', [""])[0])
        if not user or user not in users:
            continue

        date = metas.get('Date', [""])
        if not date:
            continue
        date = date[0]

        time = metas.get('Time', [""])
        if not time:
            continue
        time = time[0]

        duration = metas.get('Duration', [""])
        if not duration:
            continue
        duration = duration[0]

        task = metas.get('Task', [""])
        if not task:
            task = ""
        else:
            task = task[0]

        if not temp.get(user, None):
            temp[user] = dict()

        content = Page(request, page).getPageText()
        if '----' in content:
            content = content.split('----')[0]

        datetime = "%s %s" % (date, time)

        if not temp.get(user, None):
            temp[user] = dict()
        temp[user][datetime] = (duration, task, content)

    entries = dict()
    for user in temp:
        entries[user] = list()
        user_entries = temp[user]

        for entry in sorted(user_entries.keys()):
            single_entry = user_entries[entry]
            entries[user].append([entry, single_entry[0], single_entry[1], single_entry[2]])

    return entries 

def macro_TimeTrack(macro, args):
    request = macro.request
    formatter = macro.formatter
    page = macro.request.page
    pagename = macro.request.page.page_name
    page = macro.request.page

    result = list()

    if args:
        target = args
    else:
        target = pagename

    users = users_in_group(request, target)

    ruser = User(request, request.user.name)
    if not ruser.is_teacher() and target != ruser.name and ruser.name not in users:
        return ""
      
    metas = get_metas(request, target, ['gwikicategory'], checkAccess=False)
    categories = metas.get('gwikicategory', list())

    if rc['group'] in categories:
        entries = timetrack_entries(request, users)
        result.extend(group_gui(request, formatter, entries))
    elif rc['student'] in categories:
        entries = timetrack_entries(request, [target])
        result.extend(user_gui(request, formatter, target, entries.get(target, list())))
    else:
        return "Invalid input page %s." % target 

    return "".join(result) 
