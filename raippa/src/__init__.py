import random
from MoinMoin import wikiutil
from MoinMoin.Page import Page

forbidden = ['CategoryTaskFlow',
             'CategoryTaskOptions',
             'CategoryQuestionOptions',
             'CategoryAnswer',
             'CategoryHistory']


raippacategories = {"task": "CategoryTask",
                    "taskflow": "CategoryTaskFlow",
                    "taskoptions": "CategoryTaskOptions",
                    "history": "CategoryHistory",
                    "question": "CategoryQuestion",
                    "questionoptions": "CategoryQuestionOptions",
                    "answer": "CategoryAnswer",
                    "timetrack": "CategoryTimetrack",
                    "student": "CategoryStudent"}

def unicode_form(form):
    new_form = dict()
    for key in form:
        new_form[key.encode('utf8')] = form[key]
    return new_form

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

def randompage(request, type):
    while True:
        pagename = "%s/%i" % (type, random.randint(10000,99999))
        if not page_exists(request, pagename):
            return pagename
