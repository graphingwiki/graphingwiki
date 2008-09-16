from MoinMoin.Page import Page
from graphingwiki.editing import getmetas
from graphingwiki.patterns import getgraphdata, encode

tipcategory = "CategoryTip"
generictip = u'Your answer was incorrect.'
checkboxgeneric = u"Your answer was incorrect or you didn't select all the correct answers."
noanswer = u'You should answer all the questions.'
recap = u'Your answer was incorrect. Here is some questions to help you out.'

def execute(pagename, request):
    tip = None
    for key in request.form:
        if key != "action":
            tip = key
            break
    
    if tip == "noanswer":
        tiptext = noanswer
    elif tip == "recap":
        tiptext = recap
    elif tip:
        tippagename = "Tip/" + tip
        tippage = Page(request, tippagename)
        if tippage.exists():
            if not hasattr(request, 'graphdata'):
                getgraphdata(request)
            metas = getmetas(request, request.graphdata, tippagename, ["WikiCategory", "tip"], checkAccess=False)
            try:
                category = metas["WikiCategory"][0][0]
                if category == tipcategory:
                    tiptext = metas["tip"][0][0]
            except:
                tiptext = generictip
        else:
            tiptext = generictip
    else:
        if not hasattr(request, 'graphdata'):
            getgraphdata(request)
        metas = getmetas(request, request.graphdata, encode(pagename), ["question"], checkAccess=False)
        tiptext = generictip
        if metas["question"]:
            questionpage = encode(metas["question"][0][0])
            metas = getmetas(request, request.graphdata, encode(questionpage), ["answertype"], checkAccess=False)
            for type, metatype in metas["answertype"]:
               if type == "checkbox":
                   tiptext = checkboxgeneric
                   break

    tip = u'{{{\nTip: %s\n}}}' % tiptext

    page = Page(request, pagename)
    page.set_raw_body(tip+page.get_raw_body(), modified=1)
    page.send_page()
