from MoinMoin.PageEditor import PageEditor

try:
    import simplejson as json
except ImportError:
    import json

def sendfault(request, msg):
    request.write(json.dumps(dict(status="error", errmsg=msg)))

def execute(pagename, request):
    request.emit_http_headers(["Content-Type: text/plain; charset=ascii"])
    if request.environ['REQUEST_METHOD'] != 'POST':
        return

    form = request.values.to_dict(flat=False)

    content = form.get('content', [None])[0]
    if not content:
        sendfault(request,  "Missing page content")
        return

    if not request.user.may.write(pagename):
        sendfault(request, "You are not allowed to edit this page")
        return

    page = PageEditor(request, pagename)
    if page.exists():
        sendfault(request, "Page already exists.")
        return

    msg = ""
    try:
        msg = page.saveText(content, 0)
    except page.SaveError, msg:
        sendfault(request, "Failed to save page: %s" % pagename)
        return

    # Update pagelinks cache
    page.getPageLinks(request)
    request.write(json.dumps(dict(status="ok", msg=msg)))
