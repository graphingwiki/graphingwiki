import os
import StringIO
from urllib import quote as url_quote
from urllib import unquote as url_unquote
from tempfile import mkstemp
from MoinMoin import wikiutil
from MoinMoin import config
from MoinMoin.action import AttachFile

from graphingwiki.editing import metatable_parseargs, getvalues
from graphingwiki.patterns import encode

cairo_found = True
try:
    import cairo
except ImportError:
    cairo_found = False
    pass

Dependencies = ['metadata']

def execute(macro, args):
    formatter = macro.formatter
    macro.request.page.formatter = formatter
    request = macro.request
    _ = request.getText

    if not args:
        args = url_quote(encode(request.page.page_name))

    topology = args

    # Get all containers
    args = 'CategoryContainer, %s=/.+/' % (args)

    request.write(args)

    # Note, metatable_parseargs deals with permissions
    globaldata, pagelist, metakeys, _ = metatable_parseargs(request, args,
                                                            get_all_keys=True)
    
    coords = dict()
    images = dict()
    aliases = dict()

    for page in pagelist:
        coords[page] = [x.split(', ') for x,y in getvalues(request, globaldata, page, topology)][0]

        images[page] = AttachFile.getFilename(request,
                                              page, u'shapefile.png')

        alias = getvalues(request, globaldata, page, 'tia-name')
        if alias:
            aliases[page] = [x for x,y in getvalues(request, globaldata, page, 'tia-name')][0]

    allcoords = coords.values()
    max_x = max([int(x[0]) for x in allcoords])
    min_x = min([int(x[0]) for x in allcoords])
    max_y = max([int(x[1]) for x in allcoords])
    min_y = min([int(x[1]) for x in allcoords])

    surface_y = max_y - min_y
    surface_x = max_x - min_x

    # Setup Cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 surface_x, surface_y)
    request.write(repr([surface_x, surface_y]))
    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)

    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.rectangle(0, 0, surface_x, surface_y)
    ctx.fill()

    for page in pagelist:
        x, y = [int(x) for x in coords[page]]
#         request.write('<br>' + repr(getvalues(request, globaldata, page, 'tia-name')) + '<br>')
#         request.write(repr(coords[page]) + '<br>')
#         request.write(str(x-min_x) + '<br>')
#         request.write(str(y-min_y) + '<br>')

        if not images.has_key(page):
            ctx.set_source_rgb(0, 0, 0)
            ctx.rectangle(x-min_x, y-min_y, 10, 10)
        else:
            sf_temp = cairo.ImageSurface.create_from_png(images[page])
            w = sf_temp.get_height()
            h = sf_temp.get_width()
            ctx.set_source_surface(sf_temp, x-min_x, y-min_y)
            ctx.rectangle(x-min_x, y-min_y, w, h)

        ctx.fill()
        if page in aliases:
            ctx.set_source_rgb(0, 0, 0)
            ctx.move_to(x-min_x, y-min_y)
            ctx.show_text(aliases[page])

    # Output a PNG file
    tmp_fileno, tmp_name = mkstemp()
    surface.write_to_png(tmp_name)
    surface.finish()
    
    f = file(tmp_name)
    data = f.read()
    os.close(tmp_fileno)
    os.remove(tmp_name)

    return '<img src="data:image/png,%s">' % (url_quote(data))
