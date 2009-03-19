# -*- coding: utf-8 -*-"
"""
    TLL macro plugin to MoinMoin
     - draws a proper Finnish legistlation security stamp

    @copyright: 2009 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
cairo_found = True
try:
    import cairo
except ImportError:
    cairo_found = False
    pass

from MoinMoin import caching
from MoinMoin.action import cache

from graphingwiki.util import encode_page, form_escape
from graphingwiki.plugin.action.metasparkline import \
    draw_path, cairo_not_found, write_surface, plot_error

LEVELS = {'2': 'SALAINEN',
          '3': 'LUOTTAMUKSELLINEN',
          '4': 'SALASSA PIDETTÄVÄ'}

LEVELSROMAN = {'4': 'IV', '3': 'III', '2': 'II'}

LAW = u"JulkL (621/1999) 24.1 \xa7:n %s k"

def plot_tll(level='4', text='7'):
    if not level in LEVELS:
        level = '4'

    leveltxt = LEVELS[level]

    # Make a context to calculate font sizes with
    # There must be a better way to do this, I just don't know it!
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)

    ctx = cairo.Context(surface)
    ctx.select_font_face("Times", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)

    # Calculate surface size so that texts will fit
    text_len = ctx.text_extents(leveltxt)[4]

    # Make the actual surface
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 268, 76)

    ctx = cairo.Context(surface)
    ctx.select_font_face("Times", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(15)
    ctx.set_line_width(0.6)

    # Fill surface with white
    width, height = surface.get_width(), surface.get_height()

    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()

    ctx.set_line_width(10)
    ctx.set_source_rgb(1.0, 0, 0)
    ctx.rectangle(0, 0, width, height)
    ctx.stroke()

    curpos = 5
    texts = ['Turvaluokiteltu %s' % (LEVELSROMAN[level]),
             LEVELS[level],
             LAW % (text)]

    for text in texts:
        curpos = curpos + 18
        text_len = ctx.text_extents(text)[4] + 4
        ctx.move_to(134-(text_len/2), curpos)
        ctx.show_text(text)
    
    data = write_surface(surface)
    
    return data

def execute(macro, args):
    request = macro.request

    # Handle GET arguments
    level = '4'
    level_text = '7'
    error = False

    if not args:
        args = ''

    arglist = [x.strip() for x in args.split(',') if x]

    key = "TLL(%s)" % (','.join(arglist))

    if not cairo_found:
        error = True
        key = "Cairo not found"

    key = "%s_%s" % (key, cache.key(request, content=key))

    if not cache.exists(request, key):
        if len(arglist) == 1:
            level = args[0]
        elif len(arglist):
            level = args[0]
            level_text = ','.join(arglist[1:])
            if len(level_text) > 11:
                level_text = level_text[:11]
            # html injection prevention
            level_text = form_escape(level_text)

        if not error:
            data = plot_tll(level, level_text)
        else:
            data = plot_error(request, key)

        cache.put(request, key, data, content_type='image/png')

    return u'<div class="TLL"><img src="%s" alt="%s"></div>' % \
       (cache.url(request, key), LAW % level_text)
