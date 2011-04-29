from MoinMoin import wikiutil

def execute(pagename, request):
    sfname = "gwikishapefile"
    outlinks = request.graphdata.get_out(pagename)
    if not outlinks.get(sfname):
        request.write("no shapefile")
    else:
        AttachFile = wikiutil.importPlugin(request.cfg, "action", "AttachFile")
        x = outlinks[sfname][0].rsplit('/', 1)
        if len(x) == 1:
            sf_wikilink = x[0]
        elif len(x) == 2:
            sf_wikilink = x[1]
            pagename = x[0].strip('{').strip('[[').strip('attachment:')
        sf_wikilink = sf_wikilink.rstrip('}').rstrip(']]')
        request.form['target'] = [sf_wikilink]
        request.form['do'] = ['get']
        AttachFile(pagename, request)
