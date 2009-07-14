# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - TwitterBadge macro Version 0.1
               Displays an emended object with the wanted twitter content
    Example: <<TwitterBadge(janikenttala)>>
    @copyright: 2008 by MarcelHäfner (www.heavy.ch)
    @copyright: 2009 by Jani Kenttala
    @license: GNU GPL, see COPYING for details.

    Based on YouTube.py
"""

import re, StringIO
from MoinMoin import wikiutil
_sysmsg = '<p><strong class="%s">%s</strong></p>'

def execute(macro, args):
    if not args:
       return (_sysmsg % ('error', 'Missing Twitter ID!',))

    link = "%s" % (wikiutil.escape(args),)

    html= '''
<div id="twitter_div">
<ul id="twitter_update_list"></ul>
<a href="http://twitter.com/%s/" id="twitter-link" style="display:block;text-align:right;">follow %s on Twitter</a>
</div>
<script type="text/javascript" src="http://twitter.com/javascripts/blogger.js"></script>
<script type="text/javascript" src="http://twitter.com/statuses/user_timeline/%s.json?callback=twitterCallback2&amp;count=5"></script>
''' % ( link,link, link )

    return macro.formatter.rawHTML(html)

