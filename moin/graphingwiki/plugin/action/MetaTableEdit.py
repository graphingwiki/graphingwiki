"""
    MetaSearch action to MoinMoin
     - Searching pages with certain metadata keys or values

    @copyright: 2007 by Erno Kuusela and Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

action_name = 'MetaTableEdit'

from MoinMoin import wikiutil, caching
import urllib, cgi, string

def urlquote(s):
    if isinstance(s, unicode):
        s = s.encode('utf-8')
    return urllib.quote(s)

def htmlquote(s):
    return cgi.escape(s, 1)

def show_editform(request, pagename, mtcontents):
    def wr(fmt, *args):
        args = tuple(map(htmlquote, args))
        request.write(fmt % args)

    wr(u'<form method="POST" action="%s">\n', urlquote(pagename))
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(u'<table>\n')
    for frompage, key, vals in mtcontents:
        inputname = frompage + u'!' + key
        wr(u'<tr><td>%s<td>%s<td><input type="text" name="%s" value="%s"></tr>',
           frompage, key, inputname, vals[0])
    wr(u'</table>\n')
    wr(u'<input type="submit" name="save" value="Save">\n')
    wr(u'</form>\n')

def process_editform(request, pagename, mtcontents):
    for keypage, key, vals in mtcontents:
        try:
            newval = request.form[keypage + '!' + key][0]
        except KeyError:
            request.write(u"<p>Value for %s (for page %s) not supplied" % (keypage, key))
        oldval = vals[0]
        assert isinstance(newval, unicode), newval
        if newval != oldval:
            request.write(u"<p>")
            request.write(edit_meta(keypage, key, newval))

def execute(pagename, request):
    request.http_headers()

    # This action generate data using the user language
    request.setContentLanguage(request.lang)

    wikiutil.send_title(request, request.getText(action_name),
                        pagename=pagename)
    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter

    request.write(formatter.startContent("content"))

    ce = caching.CacheEntry(request, request.page, 'MetaTable')
    print ce.content()
    if request.form.has_key('save'):
        process_editform(request, pagename, eval(ce.content()))
    else:
        show_editform(request, pagename, eval(ce.content()))
        
    # End content
    request.write(formatter.endContent()) # end content div
    # Footer
    wikiutil.send_footer(request, pagename)



from MoinMoin.PageEditor import PageEditor
from MoinMoin.request import RequestCLI
import re

def getpage(name):
    req = RequestCLI(pagename=name)
    page = PageEditor(req, name)
    return page

def edit(pagename, editfun):
    p = getpage(pagename)
    oldtext = p.get_raw_body()
    newtext = editfun(pagename, oldtext)
    msg = p.saveText(newtext, 0)
    return msg

def macro_rx(macroname):
    return re.compile(r'\[\[(%s)\((.*?)\)\]\]' % macroname)

metadata_rx = macro_rx("MetaData")

def edit_meta(pagename, metakey, newmetaval):
    def editfun(pagename, oldtext):
        def subfun(mo):
            old_keyval_pairs = mo.group(2).split(',')
            newargs=[]
            for key, val in zip(old_keyval_pairs[::2], old_keyval_pairs[1::2]):
                key = key.strip()
                if key == metakey:
                    val = newmetaval
                newargs.append('%s,%s' % (key, val))
            return '[[MetaData(%s)]]' % (string.join(newargs, ','))
        return metadata_rx.sub(subfun, oldtext)
        
    return edit(pagename, editfun)
