from MoinMoin import wikiutil

def execute(pagename, request):
    sfname = "gwikishapefile"
    outlinks = request.graphdata.get_out(pagename)
    if not outlinks.get(sfname):
        request.write("no shapefile")
    else:
        AttachFile = wikiutil.importPlugin(request.cfg, "action", "AttachFile")
        sf_wikilink = outlinks[sfname][0].split('/')[-1]
        sf_wikilink = sf_wikilink.rstrip('}').rstrip(']]')
        request.form['target'] = [sf_wikilink]
        request.form['do'] = ['get']
        AttachFile(pagename, request)
