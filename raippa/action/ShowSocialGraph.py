from graphingwiki.editing import getmetas
from graphingwiki.editing import process_edit
from graphingwiki.editing import order_meta_input
from graphingwiki.patterns import GraphData, encode

from MoinMoin.Page import Page
from MoinMoin import wikiutil

historycategory = u'CategoryHistory'
socialcategory = u'CategorySocial'

def addlink(pagename):
    return '[['+pagename+']]'

def getflow(request, task):

    globaldata = GraphData(request)
    meta = getmetas(request, globaldata, encode(task), ["start"], checkAccess=False)
    start = encode(meta["start"][0][0])

    flow = list()

    meta = getmetas(request, globaldata, encode(start), ["question", "next"], checkAccess=False)
    question = encode(meta["question"][0][0])
    next = encode(meta["next"][0][0])
    flow.append((start, question))

    while next != "end":
        meta = getmetas(request, globaldata, encode(next), ["question", "next"], checkAccess=False)
        question = encode(meta["question"][0][0])
        flow.append((next, question))
        next = encode(meta["next"][0][0])

    globaldata.closedb()
    return flow

#TODO: aekkoset ei skullaa kunnol
#TODO: tarkista etta kysymys on sosial tyyppia
#TODO: ei omaa nimea kysymyslistaan, Raippa macrossa
#TODO: ei muita kysymystyyppyja samaan taskiin
def execute(pagename, request):
    flow = getflow(request, pagename)

    for taskflowpoint, question in flow:
        globaldata = GraphData(request)
        metas = getmetas(request, globaldata, encode(question), ["question"], checkAccess=False)
        target = encode(metas["question"][0][0])

        page = globaldata.getpage(question)
        linking_in = page.get("in", {})
        historylist = linking_in["question"]
        globaldata.closedb()

        for answer in historylist:
            pagetemp = Page(request, answer)
            categorylist = wikiutil.filterCategoryPages(request, pagetemp.parsePageLinks(request))
            if historycategory in categorylist:
                globaldata = GraphData(request)
                metas = getmetas(request, globaldata, encode(answer), ["true", "user", "task"])
                globaldata.closedb()
                useranswer = encode(metas["true"][0][0])
                user = encode(metas["user"][0][0])
                task = encode(metas["task"][0][0])
                taskpage = Page(request, task)
                taskparent = taskpage.getParentPage().page_name
                linkname = u'%s: %s' % (taskparent, useranswer)

                userpage = u'%s/S%s' %  (pagename, user)
                targetpage = u'%s/S%s' % (pagename, target)
                page = Page(request, targetpage)
                if not page.exists():
                    metadata = {u'label': [target]}
                    input = order_meta_input(request, targetpage, metadata, "add")
                    process_edit(request, input, True, {targetpage:[socialcategory]})

                metadata = {linkname: [addlink(targetpage)], u'label': [user]}
                input = order_meta_input(request, userpage, metadata, "add")
                process_edit(request, input, True, {userpage:[socialcategory]})

    url = u'%s/%s?action=ShowGraph&depth=%s&graph=Create' % (request.getBaseURL(), userpage, str(len(flow)))
    request.http_redirect(url)
