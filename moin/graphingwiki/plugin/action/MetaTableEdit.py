"""
    MetaSearch action to MoinMoin
     - Searching pages with certain metadata keys or values

    @copyright: 2007 by Erno Kuusela and Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

action_name = 'MetaTableEdit'

import urllib, cgi

from MoinMoin import wikiutil, caching, config

from graphingwiki.editing import edit_meta

def urlquote(s):
    if isinstance(s, unicode):
        s = s.encode(config.charset)
    return urllib.quote(s)

def url_unquote(s):
    s = urllib.unquote(s)
    if not isinstance(s, unicode):
        s = unicode(s, config.charset)
    return s

def htmlquote(s):
    return cgi.escape(s, 1)

def show_editform(request, pagename, mtcontents):
    def wr(fmt, *args):
        args = tuple(map(htmlquote, args))
        request.write(fmt % args)

    wr(u'<form method="POST" action="%s">\n', urlquote(pagename))
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(u'<table>\n')
    wr(u'<tr><th>Page name<th>Key<th>Value\n')

    for frompage, key, vals in mtcontents:
        frompage, key = url_unquote(frompage), url_unquote(key)

        if not vals:
            default = ''
        else:
            default = url_unquote(vals.pop()).strip('"')
        inputname = frompage + u'!' + key
        wr(u'<tr><td>%s<td>%s<td><input type="text" name="%s" value="%s"></tr>',
           frompage, key, inputname, default)
        #print frompage, key, inputname, default, '<br>'
    wr(u'</table>\n')
    wr(u'<input type="submit" name="save" value="Save">\n')
    wr(u'</form>\n')

def process_editform(request, pagename, mtcontents):
    for keypage, key, vals in mtcontents:
        keypage, key = url_unquote(keypage), url_unquote(key)

        try:
            newval = request.form[keypage + '!' + key][0]
        except KeyError:
            # Something must be wrong as these are abundant
            #request.write(u"<p>Value for %s (for page %s) not supplied" % \
            #              (key, keypage))
            continue
        
        if vals:
            oldval = url_unquote(vals.pop()).strip('"')
        else:
            oldval = ''
        assert isinstance(newval, unicode), newval
        if newval != oldval:
            request.write(u"<p> %s: " % keypage)
            request.write(edit_meta(request, keypage.encode(config.charset),
                                    key, oldval, newval))

def execute(pagename, request):
    request.http_headers()

    # This action generates data using the user language
    request.setContentLanguage(request.lang)

    title = request.getText('Meta table edit')
    wikiutil.send_title(request, title,
                        pagename=pagename)
    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter

    request.write(formatter.startContent("content"))
    
    # TODO synthesize a request to show the page we want to edit, to ensure
    # up to date data in the cache
    # request.requestCLI(pagename)

    ce = caching.CacheEntry(request, request.page, 'MetaTable')
    if request.form.has_key('save'):
        process_editform(request, pagename, eval(ce.content()))
    else:
        show_editform(request, pagename, eval(ce.content()))
        
    # End content
    request.write(formatter.endContent()) # end content div
    # Footer
    wikiutil.send_footer(request, pagename)
