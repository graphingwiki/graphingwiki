# -*- coding: utf-8 -*-"
"""
    metaRadarDiagram plugin to MoinMoin/Graphingwiki
     - Shows a spider graph of metakeys and values

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
import cairo
import math

from urllib import unquote as url_unquote
from tempfile import mkstemp

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.parser.wiki import Parser
from MoinMoin.util import MoinMoinNoFooter
from MoinMoin.request import RequestModPy

from graphingwiki.editing import metatable_parseargs, getvalues, ordervalue
from graphingwiki.patterns import encode

WIDTH, HEIGHT = 1000, 1000
CENTER = (500, 500)
RADIUS = 450

def add_to_center(coords):
    return CENTER[0] + coords[0], CENTER[1] + coords[1]

def spider_coords(radius, angle):
    x = radius * round(math.sin(angle), 2)
    y = -radius * round(math.cos(angle), 2)

    return x, y

# Draw a path between a set of points
def draw_path(ctx, endpoints):
    ctx.move_to(*endpoints[-1])
    for coord in endpoints:
        ctx.line_to(*coord)

    return ctx

# Draw a radar diagram at a certain radious
def spider_radius(ctx, radius, sectors):
    angle = 2*math.pi/sectors
    endpoints = list()
    ctx.set_line_width(1)

    for i in range(sectors):
        ctx.move_to(*CENTER)

        x, y = spider_coords(radius, i*angle)

        endpoints.append(add_to_center((x, y)))

        ctx.rel_line_to(x, y)

    ctx.stroke()

    ctx.set_line_width(0.5)
    draw_path(ctx, endpoints)
    ctx.stroke()

    return ctx, endpoints

def execute(pagename, request):
    _ = request.getText

    # Setup Cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)
    ctx.select_font_face("Times-Roman", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(12)

    args = ', '.join(x for x in request.form.get('arg', []))

    # Note, metatable_parseargs deals with permissions
    globaldata, pagelist, metakeys = metatable_parseargs(request, args,
                                                         get_all_keys=True)

    # If no keys, print nothing
    if not pagelist:
        return u''

    # Populate data to the radar chart
    data = dict().fromkeys(metakeys, set())

    for page in pagelist:
        for key in metakeys:
            data[key].update(x for x, y in
                             getvalues(request, globaldata, page, key))

    globaldata.closedb()

    # Get values for the chart axes
    values = set([])
    data_per_axis = dict()
    for axis, (key, val) in enumerate(data.iteritems()):
        data_per_axis[axis] = key
        # Opportunistic parsing of values
        values.update(ordervalue(x) for x in val)
    values = sorted(values)

    per_value = RADIUS / len(values)

    sectors = len(data)
    angle = 2*math.pi/sectors

    # Make the base grid
    for x in range(per_value, RADIUS, per_value):
        ctx, gridpoints = spider_radius(ctx, x, sectors)

    # Apply ink from strokes so far
    ctx.stroke()

    # Now start to make chart on top of the base
    ctx.set_source_rgb(50/255.0,137/255.0,37/255.0)
    ctx.set_line_width(5)

    endpoints = list()

    # Find coords for each value
    for i in range(sectors):
        val = data[data_per_axis[i]].pop()
        # Opportunistic parsing of values
        val = ordervalue(val)
        radius = values.index(val)
        x, y = spider_coords(radius * per_value, i*angle)

        endpoints.append(add_to_center((x, y)))

    draw_path(ctx, endpoints)

    # Draw path filling the contents
    ctx.stroke_preserve()
    ctx.set_source_rgba(150/255.0,190/255.0,13/255.0, 0.2)
    ctx.fill()

    # Write axis names on top of it all
    for point, axis in zip(gridpoints, data_per_axis.keys()):
        text = url_unquote(data_per_axis[axis])

        ctx.set_source_rgba(1, 1, 1, 0.9)
        width, height = ctx.text_extents(text)[2:4]

        x, y = point[0] - 0.1 * width, point[1] + 0.1 * height
        ctx.rectangle(x, y, width * 1.2, -height * 1.2)
        ctx.fill()

        ctx.set_source_rgb(0, 0, 0)
        ctx.move_to(*point)
        ctx.show_text(text)

    # Output a PNG file
    tmp_fileno, tmp_name = mkstemp()
    surface.write_to_png(tmp_name)
    f = file(tmp_name)
    data = f.read()
    os.close(tmp_fileno)
    os.remove(tmp_name)

    if isinstance(request, RequestModPy):
        request.setHttpHeader('Content-type: image/png')
        del request.mpyreq.headers_out['Vary']
    else:
        request.write("Content-type: image/png\n\n")
        
    request.write(data)
    raise MoinMoinNoFooter
