# -*- coding: utf-8 -*-"
"""
    CL macro plugin to MoinMoin
     - Draws configurable classification markings

    @copyright: 2011 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from MoinMoin.action import cache

from graphingwiki.util import form_escape, cache_key, cache_exists
from graphingwiki import cairo_found, plot_error

from ST import plot_box, CAIRO_BOLD

DEFAULT = [('COMPANY CONFIDENTIAL', CAIRO_BOLD)]

class MarkingError(Exception):
    pass

def execute(macro, args):
    request = macro.request
    error = False

    if not args:
        key = DEFAULT
    elif not hasattr(request.cfg, 'gwiki_markings'):
        error = True
        key = 'No gwiki_markings in configuration'
    else:
        try:
            val = request.cfg['gwiki_markings'][args]
            key = list()
            for line in val:
                if not isinstance(line, unicode):
                    raise MarkingError
                key.append((line, CAIRO_BOLD))
        except KeyError:
            key = 'Marking not in gwiki_markings'
            error = True
        except MarkingError:
            key = 'Marking misconfiguration (not a tuple of unicode strings)'
            error = True

    if not cairo_found:
        error = True
        key = "Cairo not found"

    level_text = form_escape(' '.join(x[0] for x in key))
    ckey = cache_key(request, (macro.name, key))

    if not cache_exists(request, ckey):
        if not error:
            data = plot_box(key)
        else:
            data = plot_error(request, key)

        cache.put(request, ckey, data, content_type='image/png')

    return u'<div class="CM"><img src="%s" alt="%s"></div>' % \
        (cache.url(request, ckey), level_text)
