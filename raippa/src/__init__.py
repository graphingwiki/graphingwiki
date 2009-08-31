import random
from MoinMoin import wikiutil
from MoinMoin.Page import Page

forbidden = ['CategoryTaskFlow',
             'CategoryTaskOptions',
             'CategoryQuestionOptions',
             'CategoryAnswer',
             'CategoryHistory',
             'CategoryDeadline']


raippacategories = {"task": "CategoryTask",
                    "taskflow": "CategoryTaskFlow",
                    "taskoptions": "CategoryTaskOptions",
                    "history": "CategoryHistory",
                    "question": "CategoryQuestion",
                    "questionoptions": "CategoryQuestionOptions",
                    "answer": "CategoryAnswer",
                    "timetrack": "CategoryTimetrack",
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

def unicode_form(form):
    new_form = dict()
    for key in form:
        new_form[key.decode('utf8')] = form[key]
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
