import MoinMoin.wikiutil as wikiutil

def execute(pagename, request):
    silent = False

    form = request.values.to_dict(flat=False)

    if "gwikisilent" in form:
        silent = True

    editlink = True
    if "noeditlink" in form:
        editlink = False

    args = form.get('args', [""])[0]

    macro = wikiutil.importPlugin(request.cfg, "macro", "MetaTable","do_macro")
    request.write(macro(request, args, silent=silent, editlink=editlink))
