# -*- coding: utf-8 -*-"
"""
    CL macro plugin to MoinMoin
     - Draws configurable classification markings

    @copyright: 2011 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from MoinMoin.action import cache

from graphingwiki import cairo_found
from graphingwiki.util import parameter_escape, cache_key, cache_exists

if cairo_found:
    from ST import plot_box, CAIRO_BOLD

    DEFAULT = [('COMPANY CONFIDENTIAL', CAIRO_BOLD)]


def execute(macro, args):
    request = macro.request

    if not cairo_found:
        return "Cairo not found."

    if not args:
        key = DEFAULT
    elif not hasattr(request.cfg, 'gwiki_markings'):
        return "No gwiki_markings in configuration."
    else:
        try:
            val = request.cfg['gwiki_markings'][args]
            key = list()
            for line in val:
                if not isinstance(line, unicode):
                    return ("Marking misconfiguration " +
                            "(not a tuple of unicode strings)")
                key.append((line, CAIRO_BOLD))
        except KeyError:
            return "Marking not in gwiki_markings."

    level_text = ' '.join(x[0] for x in key)
    ckey = cache_key(request, (macro.name, key))

    if not cache_exists(request, ckey):
        data = plot_box(key)
        cache.put(request, ckey, data, content_type='image/png')

    return u'<div class="CM"><img src="{0}" alt="{1}"></div>'.format(
           cache.url(request, ckey), parameter_escape(level_text))
