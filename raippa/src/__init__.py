import random, os, re
from MoinMoin import config, wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

raippausers = "admin", "teacher", "student"

forbidden = ['CategoryTaskFlow',
             'CategoryTaskOptions',
             'CategoryQuestionOptions',
             'CategoryAnswer',
             'CategoryTestInput',
             'CategoryTestOutput',
             'CategoryHistory',
             'CategoryDeadline',
             'CategoryBotComment']


raippacategories = {"task": "CategoryTask",
                    "taskflow": "CategoryTaskFlow",
                    "taskoptions": "CategoryTaskOptions",
                    "history": "CategoryHistory",
                    "question": "CategoryQuestion",
                    "questionoptions": "CategoryQuestionOptions",
                    "answer": "CategoryAnswer",
                    "testinput": "CategoryTestInput",
                    "testoutput": "CategoryTestOutput",
                    "timetrack": "CategoryTimeTrack",
                    "group": "CategoryGroup",
                    "student": "CategoryStudent",
                    "deadline": "CategoryDeadline"}

def to_json(arg):
    """Formats python data structures to json. 
    Supports any combination of:
        str,unicode,
        int,long,float,bool,null
        dict,list,tuple    
    """
    def parse(raw): 
       
        if isinstance(raw, (unicode,str)):
            raw = raw.replace("\r", '')
            raw = raw.replace("\n", '\\n')
            raw = raw.replace('\\' ,'\\\\')
            raw = raw.replace('"' ,'\\"')
            return '"%s"' %raw

        elif isinstance(raw, bool):
            if raw:
                return "true"
            else:
                return "false"

        elif isinstance(raw, (int, float, long)):
            return raw

        elif isinstance(raw, dict):
            result = list()
            for key, val in raw.items():
                result.append('%s : %s' % (parse(unicode(key)), parse(val)))

            return "{\n" + ",\n".join(result) + "\n}"

        elif isinstance(raw, (list, tuple, set)):
            result = list()
            for val in raw:
                result.append('%s' % (parse(val)))

            return '[\n' +  ",\n".join(result) + "\n]"

        else:
            return "null"


    result = parse(arg)
    if result[0]  not in ["[", "{"]:
        result = '[' + result +']'
    return result

def attachment_content(request, pagename, filename):
    if isinstance(filename, unicode):
        filename = filename.encode(config.charset)

    if request.page and pagename == request.page.page_name:
        page = request.page
    else:
        page = Page(request, pagename)

    attachdir = page.getPagePath("attachments", check_create=1)
    fpath = os.path.join(attachdir, filename)

    if not os.path.isfile(fpath):
        raise ValueError, "Attachment '%s' does not exist!" % filename

    file = open(fpath, 'r')
    content = file.read()
    file.close()

    return content

def delete_attachment(request, pagename, filename):
    if isinstance(filename, unicode):
        filename = filename.encode(config.charset)

    if request.page and pagename == request.page.page_name:
        page = request.page
    else:
        page = Page(request, pagename)

    attachdir = page.getPagePath("attachments", check_create=1)
    fpath = os.path.join(attachdir, filename)

    if not os.path.isfile(fpath):
        raise ValueError, "Attachment '%s' does not exist!" % filename

    os.remove(fpath)

def attachment_list(request, pagename):
    if request.page and pagename == request.page.page_name:
        page = request.page
    else:
        page = Page(request, pagename)

    attach_dir = page.getPagePath("attachments", check_create=1)

    if os.path.isdir(attach_dir):
        files = [fn.decode(config.charset) for fn in os.listdir(attach_dir)]
        files.sort()
    else:
        files = list() 
    return files

def users_in_group(request, group):
    raw = Page(request, group).get_raw_body()
    users = list()

    for line in raw.split("\n"):
        if line.startswith(" * "):
            name = line[3:].rstrip()

            users.append(removelink(name))

    return users

def unicode_form(form):
    new_form = dict()
    for key in form:
        new_form[key.decode('utf8')] = form[key]
    return new_form

def rename_page(request, pagename, newname, comment=""):
    msg = str()

    #rename incoming links
    pagedata = request.graphdata.getpage(pagename)
    linkcomment = "changed links: %s -> %s" % (pagename, newname)

    pages = list()
    for type in pagedata.get('in', {}):
        for linkingpage in pagedata['in'][type]:
            pages.append(linkingpage)

    for linkingpage in pages:
        page = PageEditor(request, linkingpage)
        old_text = page.get_raw_body()
        savetext = old_text.replace(addlink(pagename), addlink(newname))

        msg = page.saveText(savetext, 0, comment=linkcomment, notify=False)

    #rename subpages
    filterfn = re.compile(ur"^%s/.*$" % re.escape(pagename), re.U).match
    subpages = request.rootpage.getPageList(user='', exists=1, filter=filterfn)

    for subpage in subpages:
        newsubname = subpage.replace(pagename, newname, 1)
        success, msg = rename_page(request, subpage, newsubname, comment)
        if not success:
            return success, msg

    #rename page
    page = PageEditor(request, pagename)
    if page.exists():
        success, msg = page.renamePage(newname, comment)
        
        if not success:
            return success, msg
        
    return True, msg 

def delete_page(request, pagename, comment=""):
    msg = str()

    #delete subpages
    filterfn = re.compile(ur"^%s/.*$" % re.escape(pagename), re.U).match
    subpages = request.rootpage.getPageList(user='', exists=1, filter=filterfn)
            
    for subpage in subpages:
        success, msg = delete_page(request, subpage, comment)
        if not success:
            return success, msg

    #delete attachments
    for attachment in attachment_list(request, pagename):
        delete_attachment(request, pagename, attachment)

    #delete page 
    page = PageEditor(request, pagename, do_editor_backup=0)
    if page.exists():
         success, msg = page.deletePage(comment)
         if not success:
             return success, msg

    return True, msg

def pages_in_category(request, category):
    page = request.graphdata.getpage(category)
    pagelist = page.get('in', dict()).get("gwikicategory", list())

    category_pages = list()
    for page in pagelist:
        if not wikiutil.isTemplatePage(request, page):
            category_pages.append(page)

    return category_pages

def page_exists(request, pagename):
    return Page(request, pagename).exists()

def addlink(pagename):
    if not pagename.startswith("[[") and not pagename.endswith("]]"):
        pagename = '[['+pagename+']]'
    return pagename

def removelink(pagename):
    if pagename.startswith("[[") and pagename.endswith("]]"):
        pagename = pagename[2:-2]
    return pagename

def running_pagename(request, parent, excluded=list()):
    number = 0
    pagename = "%s/%.3i" % (parent, number)

    while pagename in excluded or Page(request, pagename).exists():
        number += 1
        pagename = "%s/%.3i" % (parent, number)

    return pagename

def randompage(request, type):
    while True:
        pagename = "%s/%i" % (type, random.randint(10000,99999))
        if not Page(request, pagename).exists():
            return pagename
