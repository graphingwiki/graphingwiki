import time
from datetime import datetime

from MoinMoin.Page import Page
from graphingwiki import values_to_form
from graphingwiki.editing import set_metas

def write_timestamps(request, pagename, meta_keys):
    timestamp = datetime(*time.gmtime()[:6]).strftime("%Y-%m-%d %H:%M:%SZ")
    cleared = {}
    metas = {}

    for key in meta_keys:
        old = cleared.setdefault(pagename, set())
        old.add(key)

        new = metas.setdefault(pagename, dict())
        new[key] = [timestamp]

    success, msg = set_metas(request, cleared, {}, metas)
    if not success:
        return False, u"Timestamping failed. Try again or contact administrator."
    return True, ""

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

    params = values_to_form(request.values)
    meta_keys = params.get("meta_key", list())
    if not meta_keys or not meta_keys[0]:
        return_page(request, pagename, 
            "Timestamping failed. Missing meta_key", "error")
        return

    success, msg = write_timestamps(request, pagename, meta_keys)
    if success:
        return_page(request, pagename)
    else:
        return_page(request, pagename, msg, "error")
