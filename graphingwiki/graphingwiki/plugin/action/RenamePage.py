# -*- coding: utf-8 -*-"
"""
    Fixes renaming of pages with graphdata
    Note: does not work on some older versions (at least 1.3.5 and earlier)

    @copyright: 2007 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""
from MoinMoin.PageEditor import PageEditor
from MoinMoin import wikiutil
from MoinMoin.action.RenamePage import RenamePage as RenPage

class RenamePage(RenPage):

    def do_action(self):
        """ Rename this page to "pagename" """
        _ = self._
        form = self.form
        newpagename = form.get('newpagename', [u''])[0]
        newpagename = self.request.normalizePagename(newpagename)
        comment = form.get('comment', [u''])[0]
        comment = wikiutil.clean_input(comment)

        # Get graphsaver
        savegraphdata = wikiutil.importPlugin(self.request.cfg,
                                              'action',
                                              'savegraphdata')

        path = self.page.getPagePath()
        # Call savegraphdata with an empty page = clear graphdata on page
        savegraphdata(self.pagename, self.request, "",
                      path, self.page)


        self.page = PageEditor(self.request, self.pagename)
        success, msg = self.page.renamePage(newpagename, comment)
        if not success:
            # If not successful, return graphdata to wiki
            text = self.page.get_raw_body()
            # Call savegraphdata with an empty page = clear graphdata on page
            savegraphdata(self.pagename, self.request, text,
                          path, self.page)

        self.newpagename = newpagename # keep there for finish
        return success, msg

def execute(pagename, request):
    """ Glue code for actions """
    RenamePage(pagename, request).render()
