from graphingwiki.editing import edit_meta

from MoinMoin.Page import Page

from raippa import FlowPage
from raippa import Question
from raippa import addlink

socialcategory = u'CategorySocial'

def execute(pagename, request):
    currentpage = FlowPage(request)
    flow = currentpage.getflow()
    userdict = dict()

    for taskpoint, questionpage in flow:
        question = Question(request, questionpage)
        historylist = question.gethistories()
        targetuser = question.question

        for answer in historylist:
            useranswer = answer[2].keys()[0] 
            user = answer[0]
            taskpage = Page(request, answer[4])
            taskparent = taskpage.getParentPage().page_name
            linkname = u'%s: %s' % (taskparent, useranswer)
            userpage = u'%s/S%s' %  (pagename, user)
            targetpage = u'%s/S%s' % (pagename, targetuser)
            if not targetuser in userdict:
                userdict[targetuser] = {u'label': [targetuser]}
            if not user in userdict:
                userdict[user] = {"label":[user]}
                userdict[user][linkname] = [addlink(targetpage)]
            else:
                if not linkname in userdict[user]:
                    userdict[user][linkname] = [addlink(targetpage)]
                else:
                    userdict[user][linkname].append(addlink(targetpage))

    for user in userdict:
        page = "%s/S%s" % (pagename, user)
        edit_meta(request, page, {}, userdict[user], True, [socialcategory])

    url = u'%s/%s?action=ShowGraph&depth=%s&graph=Create' % (request.getBaseURL(), userpage, str(len(flow)))
    request.http_redirect(url)
