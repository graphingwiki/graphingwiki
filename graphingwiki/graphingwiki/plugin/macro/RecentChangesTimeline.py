# -*- coding: utf-8 -*-
"""
    RecentChangesTimeline macro
     - generates SIMILE timeline visualisation

    @copyright: 2008-2009 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
from time import strptime, strftime, localtime

from graphingwiki.util import url_construct

Dependencies = ['metadata']

time_format = "%b %d %Y %H:%M:%S %z"

def execute(macro, args):
    focus = strftime(time_format, localtime())

    urlargs = {'action': [u'recentchangestimeline']}
    if args:
        arglist = [x.strip() for x in args.split(',') if x]

        for arg in arglist:
            if arg.startswith('max_days='):
                urlargs[u'max_days'] = [arg.split('=')[1]]
            if arg.startswith('focus='):
                try:
                    focus = strptime(time_format, arg.split('=')[1])
                except ValueError:
                    pass

    source_url = url_construct(macro.request, urlargs)

    return """
    <div id="recentchangestimeline" style="height: 400px; margin: 2em;">
      <script type="text/javascript" src="%s/gwikicommon/simile/recentchangestimeline.js"></script>

      <input type="hidden" id="recentchangestimelinefocus" value="%s" />
      <input type="hidden" id="recentchangestimelinesource" value="%s" />

      <noscript>
        <p>No JavaScript</p>
      </noscript>
    </div>
""" % (macro.request.cfg.url_prefix_static, focus, source_url)
