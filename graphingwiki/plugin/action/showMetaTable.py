import MoinMoin.wikiutil as wikiutil

from graphingwiki import values_to_form

def execute(pagename, request):
    silent = False

    form = values_to_form(request.values)

    if "gwikisilent" in form:
        silent = True

    editlink = True
    if "noeditlink" in form:
        editlink = False

    args = form.get('args', [""])[0]

    macro = wikiutil.importPlugin(request.cfg, "macro", "MetaTable","do_macro")
    request.write(macro(request, args, silent=silent, editlink=editlink))
