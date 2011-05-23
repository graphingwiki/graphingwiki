import MoinMoin.wikiutil as wikiutil

def execute(pagename, request):
    request.emit_http_headers()

    silent = False
    if "gwikisilent" in request.form:
        silent = True

    editlink = True
    if "noeditlink" in request.form:
        editlink = False

    args = request.form.get('args', [""])[0]

    macro = wikiutil.importPlugin(request.cfg, "macro", "MetaTable","do_macro")
    macro(request, args, silent, editlink)
