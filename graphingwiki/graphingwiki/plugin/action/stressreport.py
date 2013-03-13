import time

from MoinMoin.Page import Page
from graphingwiki import values_to_form
from graphingwiki.editing import set_metas

def save_report(request, control, activity):
    second = time.time()
    isotime = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(int(second)))
    second *= 10**6
    timestamp = isotime + ".%06d" % (second % (10**6),)
    pagename = "Stress-%s" % timestamp

    cleared = {pagename: set(["in control", "activity", "time"])}
    metas = {"gwikicategory": ["CategoryStress"],
             "in control": [control],
             "activity": [activity],
             "time": [isotime]}

    success, msg = set_metas(request, cleared, {}, {pagename: metas})
    if not success:
        return False, u"Reporting failed. Try again or contact administrator."

    return True, u"Thank you for reporting."

def return_page(request, pagename, msg=None, msg_type="info"):
    request.reset()
    request.page = Page(request, pagename)  

    if msg is not None:
        request.theme.add_msg(msg, msg_type)
    request.page.send_page()

def execute(pagename, request):
    if request.environ["REQUEST_METHOD"] != "POST":
        return_page(request, pagename)
        return

    for key in values_to_form(request.values):
        if len(key) == 10 and key.startswith("stress_"):
            try:
                control = {"0":"yes", "1":"no"}[key[7]]
                activity = {"0":"low","1":"medium","2":"high"}[key[9]]
            except IndexError:
                continue

            success, msg = save_report(request, control, activity)
            if success:
                return_page(request, pagename, msg)
            else:
                return_page(request, pagename, msg, "error")
            return
        
    return_page(request, pagename)

