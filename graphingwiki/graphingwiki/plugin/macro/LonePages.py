# -*- coding: utf-8 -*-"
"""
    LonePages macro plugin to MoinMoin
     - Shows a list of pages that are not connected and not part of a hierarchy

    @copyright: 2009 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
def macro_LonePages(macro, hier=False, docnumber=0):
    f = macro.formatter
    request = macro.request
    _ = request.getText

    out = '<div class="LonePages">' + _('Lone pages')

    out += f.number_list(1, **{'class': 'lonelist'})

    no = 0
    # Look through pages
    for page in request.graphdata:
        # Hier = omit hierarchical
        if hier:
            if '/' in page:
                continue

        if docnumber:
            if no == docnumber:
                break

        pageobj = request.graphdata.getpage(page)
        if (pageobj.get('saved') and
            not pageobj.get('out', dict()) and 
            not pageobj.get('include', dict()) and
            not pageobj.get('in', dict())):
            no += 1
            out += f.listitem(1, **{'class': 'loneitem'}) + \
                f.pagelink(1, page) + f.text(page) + f.pagelink(0) + \
                f.listitem(0)

    out += f.number_list(0)
    out += '</div>'

    return out
