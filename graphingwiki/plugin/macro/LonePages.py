# -*- coding: utf-8 -*-"
"""
    Shows a list of pages that are not connected.

    Show all pages that are not connected:

    <<LonePages>>

    Filter away pages that are part of hierarchy:

    <<LonePages(omit_hierarchical=True)>>

    Show only first 10 matches:

    <<LonePages(limit=10)>>

    @copyright: 2009 by Juhani Eronen <exec@iki.fi>
                2015 by Mika Seppänen <mika.seppanen@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""


def macro_LonePages(macro, omit_hierarchical=False, limit=0):
    f = macro.formatter
    request = macro.request

    out = f.div(1, **{"class": "lonepages"})
    out += f.number_list(1, **{"class": "lonelist"})

    count = 0

    for page in request.graphdata:
        if not request.user.may.read(page):
            continue

        if omit_hierarchical:
            if '/' in page:
                continue

        if limit:
            if count >= limit:
                break

        pageobj = request.graphdata.getpage(page)
        if (pageobj.get("saved") and
           not pageobj.get("out") and
           not pageobj.get("include") and
           not pageobj.get("in")):
            count += 1
            out += (f.listitem(1, **{"class": "loneitem"}) +
                    f.pagelink(1, page) + f.text(page) + f.pagelink(0) +
                    f.listitem(0))

    out += f.number_list(0)
    out += f.div(0)

    return out
