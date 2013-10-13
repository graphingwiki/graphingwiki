# -*- coding: utf-8 -*-"
"""
    IOCList macro plugin to MoinMoin/Graphingwiki
     - Make a wiki page with metas on indicators of compromise
     - Currently supports IPv4 and IPv6 addresses

    @copyright: 2013 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

def execute(macro, args):
    f = macro.formatter
    macro.request.page.formatter = f
    request = macro.request
    _ = request.getText

    args = [x.strip() for x in args.split(',')]
    allow_overlap = 'no'
    if len(args) == 2:
        template, overlap = args
        if overlap in ['no', 'yes']:
            allow_overlap = overlap 
    elif len(args) == 1:
        template = args[0]
    else:
        template = 'IOCListTemplate'

    html = [
        u'<form class="macro" method="POST" action="%s"><div>' % \
            (request.href(f.page.page_name)),
        u'<input type="hidden" name="action" value="ioclist">',
        u'<input type="hidden" name="allow_overlap" value="%s">' % \
            (allow_overlap), 
        u'<input type="hidden" name="template" value="%s">' % (template),
        u'<textarea rows=10 cols=80 name="ips"></textarea>',
        u'<input type="text" name="name">',
        u'<input type="submit" value="%s">' % _("Create IOCList"),
        u'</div></form>',
        ]

    return macro.formatter.rawHTML('\n'.join(html))
