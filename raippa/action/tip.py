from MoinMoin.Page import Page
from graphingwiki.editing import getmetas
from graphingwiki.patterns import getgraphdata

tipcategory = "CategoryTip"
generictip = u'This is generic tip. Et vaan osaa!'
noanswer = u'You should answer all the questions.'
penalty = u'Your answer was incorrect and now you have do extra penalty task.'

def execute(pagename, request):
    tip = None
    for key in request.form:
        if key != "action":
            tip = key
            break
    
    if tip == "noanswer":
        tiptext = noanswer
    elif tip == "penalty":
        tiptext = penalty
    elif tip:
        tippagename = "Tip/" + tip
        tippage = Page(request, tippagename)
        if tippage.exists():
            globaldata = getgraphdata(request)
            metas = getmetas(request, globaldata, tippagename, ["WikiCategory", "tip"], checkAccess=False)
            try:
                category = metas["WikiCategory"][0][0]
                if category == tipcategory:
                    tiptext = metas["tip"][0][0]
            except:
                tiptext = generictip
        else:
            tiptext = generictip
    else:
        tiptext = generictip

    tip = u'{{{\nTip: %s\n}}}' % tiptext

    page = Page(request, pagename)
    page.set_raw_body(tip+page.get_raw_body(), modified=1)
    page.send_page()
