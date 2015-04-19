# -*- coding: iso-8859-1 -*-
"""
    MoinMoin - MetaTagCloud

    Based on TagCloud.py "Create tagcloud"
    @copyright: 2007 by Christian Groh

    Adapted for use in Graphingwiki to visualise metakeys
    @copyright: 2007 by Juhani Eronen

"""
from MoinMoin import wikiutil
from graphingwiki.editing import metatable_parseargs
from graphingwiki.util import NO_TYPE, form_escape, url_construct

Dependencies = ["namespace"]


def execute(macro, args):
    mode = 'keys'

    request = macro.request

    # get params
    if args:
        args = [x.strip() for x in args.split(',')]
    else:
        args = []

    kw = {}
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            if key == "metaMaxTags":
                kw[str(key.strip())] = value
            if key == "metaShowMode":
                if value in ['keys', 'values']:
                    mode = value

    args = filter(
        lambda x: x.split('=')[0] not in ["metaMaxTags", "metaShowMode"],
        args
    )

    try:
        maxTags = int(kw["metaMaxTags"])
    except (KeyError, ValueError):
        maxTags = 50

    # [(hits, fontsize), (hits, fontsize), ...]
    levels = [
        (4, "0.65em"),
        (7, "0.75em"),
        (12, "0.9em"),
        (18, "1.0em"),
        (25, "1.05em"),
        (35, "1.1em"),
        (50, "1.15em"),
        (60, "1.2em"),
        (90, "1.25em"),
        (None, "1.3em")
    ]

    tags = []

    if not args:
        args = ''
    else:
        args = ','.join(args)

    pagelist, metakeys, _ = metatable_parseargs(
        macro.request,
        args
    )

    if not hasattr(request.graphdata, 'keys_on_pages'):
        request.graphdata.reverse_meta()

    for name in pagelist:
        page = request.graphdata.getpage(name)
        if mode == 'keys':
            tags.extend(x for x in page.get('meta', {}).keys())
            tags.extend(x for x in page.get('out', {}).keys() if x != NO_TYPE)
        else:
            for key in page.get('meta', {}).keys():
                if key in ['label', 'URL']:
                    continue
                tags.extend(x.strip('"') for x in page['meta'][key])
            for key in page.get('out', {}).keys():
                if key == NO_TYPE:
                    continue
                tags.extend(page['out'][key])

    taglist = frozenset(tags)

    def sort(t):
        return t[1]

    show = []
    for tag in taglist:
        cnt = tags.count(tag)
        show.append((tag, cnt, tag))
    show.sort(key=sort, reverse=True)
    show = show[0:maxTags]
    show.sort()

    html = []

    for tag in show:
        if mode == 'keys':
            data = request.graphdata.keys_on_pages.get(tag[2])
        else:
            data = request.graphdata.vals_on_pages.get(tag[2])

        if not data:
            data = []
        title = '\n'.join(sorted(data, key=unicode.lower))

        pagename = tag[0]
        hits = tag[1]
        url = url_construct(request, {
            "action": ["MetaSearch"],
            "q": [pagename]
        }, request.page.page_name)

        fontsize = "0.1em"
        for _hits, _fontsize in levels:
            if _hits is None or hits < _hits:
                fontsize = _fontsize
                break

        html.append(
            u'<span style="font-size:%s;"><a title="%s" href="%s"> %s</a></span>' % (
                form_escape(fontsize),
                form_escape(title),
                form_escape(url),
                wikiutil.escape(pagename)
            )
        )

    return ''.join(html)
