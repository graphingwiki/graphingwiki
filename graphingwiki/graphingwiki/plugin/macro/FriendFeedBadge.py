# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - FriendFeedBadge macro Version 0.1
               Displays an emended object with the wanted FriendFeed content
    Example: <<FriendFeedBadge(janikenttala)>>
    @copyright: 2009 by Jani Kenttala
    @license: GNU GPL, see COPYING for details.

    Based on YouTube.py
    @copyright: 2008 by MarcelHäfner (www.heavy.ch)
"""

import re, StringIO
from MoinMoin import wikiutil
_sysmsg = '<p><strong class="%s">%s</strong></p>'

def execute(macro, args):
    if not args:
       return (_sysmsg % ('error', 'Missing FriendFeed ID!',))

    link = "%s" % (wikiutil.escape(args),)

    html= '''
<script type="text/javascript" src="http://friendfeed.com/embed/widget/%s?v=3&amp;hide_logo=1&amp;hide_comments_likes=1&amp;width=200"></script><noscript><a href="http://friendfeed.com/%s"><img alt="View my FriendFeed" style="border:0;" src="http://friendfeed.com/embed/widget/%s?v=3&amp;hide_logo=1&amp;hide_comments_likes=1&amp;width=200&amp;format=png"/></a></noscript>
''' % ( link,link, link )

    return macro.formatter.rawHTML(html)

