# -*- coding: utf-8 -*-"
"""
    MetaMap macro plugin to MoinMoin/Graphingwiki
     - Draws pages on the world map

    @copyright: 2009 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import os
import math

cairo_found = True
try:
    import cairo
except ImportError:
    cairo_found = False
    pass

geoip_found = True
try:
    import GeoIP
except ImportError:
    geoip_found = False
    pass

from MoinMoin.action import cache

import graphingwiki

from graphingwiki.plugin.action.metasparkline import write_surface, plot_error
from graphingwiki.editing import metatable_parseargs, get_metas
from graphingwiki.util import form_escape, make_tooltip

Dependencies = ['meta']

DEFAULT_MAP = "world_map.png"

def getCoordinates(GEO_IP, host):
    if host is None:
        return None

    octets = [int(x) for x in host.split('.') if x]
    for octet in octets:
        if (octet > 255) or (octet < 0):
            return None

    try:
        gir = GEO_IP.record_by_name(host)
    except:
        return None
    
    if gir is None:
        return None
    
    y = (-gir["latitude"] + 90) / 180.0
    x = (gir["longitude"] + 180) / 360.0
    return x, y

def execute(macro, args):
    request = macro.request
    _ = request.getText

    if not args:
        args = ''

    key = "MetaMap(%s)" % (args)

    # Find map location. Default is DEFAULT_MAP in url_prefix_static
    map_path = getattr(request.cfg, 'gwiki_map_path', DEFAULT_MAP)
    
    # If map path is not a absolute, prepend graphingwiki path
    if not map_path.startswith('/'):
        for path in graphingwiki.__path__:
            map_path = os.path.join(path, map_path)
            if os.path.exists(map_path):
               break 

    GEO_IP_PATH = getattr(request.cfg, 'gwiki_geoip_path', None)

    ctx = None

    if not cairo_found:
        data = plot_error(request, 
                          "ERROR: Cairo Python extensions not installed.")
    elif not geoip_found:
        data = plot_error(request, 
                          "ERROR: GeoIP Python extensions not installed.")
    elif not GEO_IP_PATH:
        data = plot_error(request, "ERROR: GeoIP data file not found.")
    elif not os.path.exists(map_path):
        data = plot_error(request, "ERROR: World map not found.")
    else:
        GEO_IP = GeoIP.open(GEO_IP_PATH, GeoIP.GEOIP_STANDARD)

    #    try:
        map_sf = cairo.ImageSurface.create_from_png(map_path)
        map_width = map_sf.get_height()
        map_height = map_sf.get_width()

        ctx = cairo.Context(map_sf)
        ctx.set_source_rgb(1.0, 0.0, 0.0)
        ctx.fill()

        args = '/^([0-9][0-9]?[0-9]?\.){3}[0-9][0-9]?[0-9]?$/'

        # Note, metatable_parseargs deals with permissions
        pagelist, metakeys, styles = metatable_parseargs(request, args,
                                                         get_all_keys=True)

        areas = dict()

        for name in pagelist:
            coords = getCoordinates(GEO_IP, name)

            if not coords:
                continue

            x, y = coords
            x, y = x*map_height, y*map_width
            radius = 2

            pagedata = request.graphdata.getpage(name)
            text = make_tooltip(request, pagedata)

            areas["%s,%s,%s" % (int(x), int(y), radius)] = \
                [name, text, 'circle']

            ctx.arc(x,y,2,0,radius*math.pi)
            ctx.fill()

        data = write_surface(map_sf)

#    except cairo.Error:
#        data = plot_error(request, key)

    cache.put(request, key, data, content_type='image/png')

    # If we have cairo context, i.e. if drawing the map succeeded
    map_text = str()
    if ctx:
        map_text = 'usemap="#%s" ' % (id(ctx))
    
    div = u'<div class="MetaMap">\n' + \
        u'<img %ssrc="%s" alt="%s">\n</div>\n' % \
        (map_text, cache.url(request, key), _('meta map'))

    map = str()
    if map_text:
        map = u'<map id="%s" name="%s">\n' % (id(ctx), id(ctx))
        for coords in areas:
            name, text, shape = areas[coords]
            pagelink = request.getScriptname() + u'/' + name

            tooltip = "%s\n%s" % (name, text)

            map += u'<area href="%s" shape="%s" coords="%s" title="%s">\n' % \
                (form_escape(pagelink), shape, coords, tooltip)
        map += u'</map>\n'

    return div + map
