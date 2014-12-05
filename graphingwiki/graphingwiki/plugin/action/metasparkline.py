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
from cStringIO import StringIO

from graphingwiki import cairo


def image_headers(request):
    request.content_type = 'image/png'

def cairo_not_found(request):
    error = request.getText(
        "ERROR: Cairo Python extensions not installed. " +
        "Not performing layout."
    )
    request.content_type = 'text/plain'
    request.write(error)

def write_surface(surface):
    # Output a PNG file
    stringio = StringIO()
    surface.write_to_png(stringio)
    surface.finish()
    return stringio.getvalue()

# Draw a path between a set of points
def draw_path(ctx, endpoints):
    ctx.move_to(*endpoints[-1])
    for coord in endpoints:
        ctx.line_to(*coord)

    return ctx

def calculate_textlen(text):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)

    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)

    # Calculate surface size so that texts will fit
    text_len = ctx.text_extents(text)[4]

    return text_len

def plot_error(request, text="No data"):
    # Just return an error message
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                 calculate_textlen(text), 25)

    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)
    ctx.set_line_width(0.6)

    ctx.set_source_rgb(0, 0, 0)
    ctx.move_to(0, 20)
    ctx.show_text(request.getText(text))
    data = write_surface(surface)

    return data
