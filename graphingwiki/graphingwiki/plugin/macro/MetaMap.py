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
from MoinMoin.macro.Include import _sysmsg

import graphingwiki

from graphingwiki.plugin.action.metasparkline import write_surface
from graphingwiki.editing import metatable_parseargs, get_metas
from graphingwiki.util import form_escape, make_tooltip, \
    url_parameters, url_construct, cache_key, cache_exists, latest_edit

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

    # Currently, the key is just based on args and the latest wiki edit
    key = cache_key(request, (macro.name, args, latest_edit(request)))

    # Find map location. Default is DEFAULT_MAP in url_prefix_static
    map_path = getattr(request.cfg, 'gwiki_map_path', DEFAULT_MAP)
    
    # If map path is not a absolute, prepend graphingwiki path
    if not map_path.startswith('/'):
        for path in graphingwiki.__path__:
            map_path = os.path.join(path, map_path)
            if os.path.exists(map_path):
               break 

    GEO_IP_PATH = getattr(request.cfg, 'gwiki_geoip_path', None)

    if not cairo_found:
        return _sysmsg % ('error', 
                          _("ERROR: Cairo Python extensions not installed."))
    elif not geoip_found:
        return _sysmsg % ('error', 
                          _("ERROR: GeoIP Python extensions not installed."))
    elif not GEO_IP_PATH:
        return _sysmsg % ('error', 
                          _("ERROR: GeoIP data file not found."))
    elif not os.path.exists(map_path):
        return _sysmsg % ('error', 
                          _("ERROR: World map not found."))
    elif not cache_exists(request, key):
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
                                                         get_all_keys=True,
                                                         include_unsaved=True)

        areas = dict()
        allcoords = dict()

        for name in pagelist:
            coords = getCoordinates(GEO_IP, name)

            if not coords:
                continue

            x, y = coords
            x, y = x*map_height, y*map_width

            allcoords.setdefault((x, y), list()).append(name)

        for coord in allcoords:
            x, y = coord
            radius = 1.5 + 0.4*(len(allcoords[coord]))

            for name in allcoords[coord]:

                pagedata = request.graphdata.getpage(name)
                text = make_tooltip(request, pagedata)

                area_key = "%s,%s,%s" % (int(x), int(y), radius)

                areas.setdefault(area_key, list()).append((name, text, 
                                                           'circle'))

                ctx.arc(x,y,radius,0,radius*math.pi)
                ctx.fill()

        data = write_surface(map_sf)

#    except cairo.Error:
#        data = plot_error(request, key)

        cache.put(request, key, data, content_type='image/png')

        mappi = ''

        for coordlist in areas:
            href = ''
            tooltip = ''

            # Only make pagelink if there are no overlapping nodes
            if len(areas[coordlist]) == 1:
                pagelink = request.getScriptname() + u'/' + name
                href = ' href="%s"' % (form_escape(pagelink))
            else:
                pages = [x[0] for x in areas[coordlist]]
                args = {'action': ['ShowGraph'], 
                        'otherpages': pages, 'noorignode': '1'}
                href = ' href="%s"' % url_construct(request, args, 
                                                    request.page.page_name)

            # When overlapping nodes occur, add to tooltips
            for coords in areas[coordlist]:
                name, text, shape = coords

                tooltip += "%s\n%s" % (name, text)

            mappi += u'<area%s shape="%s" coords="%s" title="%s">\n' % \
                (href, shape, coordlist, tooltip)

        cache.put(request, key + '-map', mappi, content_type='text/html')

    else:
        mappifile = cache._get_datafile(request, key + '-map')
        mappi = mappifile.read()
        mappifile.close()

    map_text = 'usemap="#%s" ' % (key)
    
    div = u'<div class="MetaMap">\n' + \
        u'<img %ssrc="%s" alt="%s">\n</div>\n' % \
        (map_text, cache.url(request, key), _('meta map'))

    map = u'<map id="%s" name="%s">\n' % (key, key)
    map += mappi
    map += u'</map>\n'

    return div + map
