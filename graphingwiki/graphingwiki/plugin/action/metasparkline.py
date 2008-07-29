# -*- coding: utf-8 -*-"
"""
    sparkline action plugin to MoinMoin
     - Draws numeric metadata in the revision history as small graphs

    Loosely based on example code by Joe Grigario
    (http://bitworking.org/news/Sparklines_in_data_URIs_in_Python).
    Sparklines originally conceived by Edward Tufte
    (http://www.edwardtufte.com).

    @copyright: 2008 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""
import os
import urllib

cairo_found = True
try:
    import cairo
except ImportError:
    cairo_found = False
    pass

from tempfile import mkstemp

from MoinMoin import config
from MoinMoin.Page import Page
from MoinMoin.util import MoinMoinNoFooter
from MoinMoin.request import RequestModPy

from graphingwiki.editing import get_revisions, getmetas

def image_headers(request):
    if isinstance(request, RequestModPy):
        request.setHttpHeader('Content-type: image/png')
        del request.mpyreq.headers_out['Vary']
    else:
        request.write("Content-type: image/png\n\n")

def cairo_not_found():
    request.setHttpHeader('Content-type: text/plain')
    request.write(_("ERROR: Cairo Python extensions not installed. " +\
                       "Not performing layout."))
    raise MoinMoinNoFooter

def write_surface(surface):
    # Output a PNG file
    tmp_fileno, tmp_name = mkstemp()
    surface.write_to_png(tmp_name)
    surface.finish()
    
    f = file(tmp_name)
    data = f.read()
    os.close(tmp_fileno)
    os.remove(tmp_name)

    return data

# Draw a path between a set of points
def draw_path(ctx, endpoints):
    ctx.move_to(*endpoints[-1])
    for coord in endpoints:
        ctx.line_to(*coord)

    return ctx

# Draw a path between a set of points
def draw_line(ctx, endpoints):
    ctx.move_to(*endpoints[0])
    for coord in endpoints[1:]:
        ctx.line_to(*coord)

    return ctx

def scale_results(data):
    # Scale data to the range [0, 100]
    min_d = min(data)
    max_d = max(data)
    scale = (max_d - min_d) / 100.0

    data = [(x - min_d) / scale for x in data]
    return data

def plot_sparkdots(results):
    # Create surface
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 len(results)*2, 15)

    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)
    ctx.set_line_width(1)

    width, height = surface.get_width(), surface.get_height()

    # Fill with white
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()

    # Scale results if needed
    max_val = max(results)
    min_val = min(results)

    if max_val > 100 or min_val < 0:
        results = scale_results(results)

    # Draw points, with red if they're above 50% and black otherwise
    for (r, i) in zip(results, range(0, len(results)*2, 2)):
        if r > 50:
            ctx.set_source_rgb(1, 0.0, 0.0)
        else:
            ctx.set_source_rgb(0, 0, 0)
            
        color = (r > 50) and "red" or "gray"
        # FAQ: to light up single pixels sharply, go to pixel + 0.5
        ctx.move_to(i + 0.5, height-r/10-4)
        ctx.line_to(i + 0.5, (height-r/10))

        ctx.stroke()
        
    data = write_surface(surface)
    return data

def plot_sparkline(results, text=True):
    # Scale results if needed
    max_val = max(results)
    min_val = min(results)
    last_val = results[-1]

    if max_val > 100 or min_val < 0:
        results = scale_results(results)

    text_len = 0
    if text:
        # Make a context to calculate font sizes with
        # There must be a better way to do this, I just don't know it!
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)

        ctx = cairo.Context(surface)
        ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                             cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(12)
        ctx.set_line_width(0.5)

        max_val = str(max_val)
        min_val = str(min_val)
        last_val = str(last_val)

        # Calculate surface size so that texts will fit
        text_len = ctx.text_extents(max_val)[4] + \
            ctx.text_extents(min_val)[4] + \
            ctx.text_extents(last_val)[4] + 6

    # Make the actual surface
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 len(results)+text_len, 20)

    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)
    ctx.set_line_width(0.6)

    # Fill surface with white
    width, height = surface.get_width(), surface.get_height()

    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()

    # Coordinates for the sparkline, 2pxs left for marigins
    # +0.5 for extra sharpness again (Cairo FAQ)
    coords = zip([x + 0.5 for x in range(2, len(results)+2)], 
                 [15 - y/10 for y in results])


    # Draw the sparkline
    ctx.set_source_rgb(0, 0, 0)
    ctx = draw_line(ctx, coords)
    ctx.stroke()

    # Draw max, min and texts
    max_pt = coords[results.index(max(results))]
    ctx.set_source_rgb(1.0, 0, 0)
    ctx.rectangle(max_pt[0]-2.5, max_pt[1]-2.5, 3, 3)
    ctx.fill()

    if text:
        ctx.move_to(len(results)+2, 20)
        ctx.show_text(max_val)

    min_pt = coords[results.index(min(results))]
    ctx.set_source_rgb(0, 0, 1.0)
    ctx.rectangle(min_pt[0]-2.5, min_pt[1]-2.5, 3, 3)
    ctx.fill()

    if text:
        text_len = ctx.text_extents(max_val)[4] + 4
        ctx.move_to(len(results)+text_len, 20)
        ctx.show_text(min_val)

        text_len += ctx.text_extents(min_val)[4] + 2
        ctx.set_source_rgb(0, 0, 0)
        ctx.move_to(len(results)+text_len, 20)
        ctx.show_text(last_val)
    
    data = write_surface(surface)
    
    return data

def plot_error():
    # Just return an error message
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 56, 20)

    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)
    ctx.set_line_width(0.6)

    
    ctx.set_source_rgb(0, 0, 0)
    ctx.move_to(0, 20)
    ctx.show_text("No data")
    data = write_surface(surface)
    
    return data

def execute(pagename, request):
    if not cairo_found:
       cairo_not_found()

    image_headers(request)

    # Handle GET arguments
    params = {'page': '', 'key': '', 'points': 0, 'style': ''}

    for attr in ['page', 'key', 'points', 'style']:
        if request.form.has_key(attr):
            val = ''.join([x for x in request.form[attr]])

            if attr == 'points':
                try:
                    val = int(val)
                except ValueError:
                    val = 0

            params[attr] = val

    # Show error if args on page and key are not passed
    if not params['page'] or not params['key']:
        request.write(plot_error())
        raise MoinMoinNoFooter

    # Get revision data
    page = Page(request, params['page'])
    globaldata, pagelist, metakeys = get_revisions(request, page)

    # Show error if no data on key
    if not params['key'] in metakeys:
        request.write(plot_error())
        raise MoinMoinNoFooter

    # If number of data points to graph are limited
    end_pts = 0
    if params['points']:
        end_pts = len(pagelist) - params['points']

    # Pagelist is reversed, go from history to current
    data = []
    key = params["key"]
    for page in pagelist[-1:end_pts:-1]:
        metas = getmetas(request, globaldata, page,
                         metakeys, display=False,
                         checkAccess=False)
        val = ''.join([x for x, y in metas.get(key, ('', ''))])
        try:
            val = float(val)
            data.append(val)
        except ValueError:
            pass

    # Show error if no valid data
    if not data:
        request.write(plot_error())
        raise MoinMoinNoFooter

    if params['style'] == 'dot':
        request.write(plot_sparkdots(data))
    elif params['style'] == 'line':
        request.write(plot_sparkline(data, text=False))
    else:
        request.write(plot_sparkline(data))
    raise MoinMoinNoFooter
