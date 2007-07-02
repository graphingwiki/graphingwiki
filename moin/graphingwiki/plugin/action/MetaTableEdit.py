"""
    MetaSearch action to MoinMoin
     - Searching pages with certain metadata keys or values

    @copyright: 2007 by Erno Kuusela and Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

action_name = 'MetaTableEdit'

import cgi
import urllib

from MoinMoin import wikiutil
from MoinMoin import config

from graphingwiki.patterns import GraphData
from graphingwiki.editing import edit_meta, getmetavalues, metatable_parseargs

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

def show_queryform(request, pagename):
    def wr(fmt, *args):
        args = tuple(map(htmlquote, args))
        request.write(fmt % args)

    wr(u'<form method="GET" action="%s">\n', urlquote(pagename))
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(u'<input type="text" name="args">\n')

    wr(u'</table>\n')
    wr(u'<input type="submit" name="show" value="Edit table">\n')
    wr(u'</form>\n')

def show_editform(request, pagename, args):
    def wr(fmt, *args):
        args = tuple(map(htmlquote, args))
        request.write(fmt % args)

    wr(u'<form method="POST" action="%s">\n', urlquote(pagename))
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(u'<table>\n')
    wr(u'<tr><th>Page name<th>Key<th>Value\n')

    globaldata, pagelist, metakeys = metatable_parseargs(request, args)

    for frompage in sorted(pagelist):
        for key in metakeys:
            wr(u'<tr><td>%s<td>%s', url_unquote(frompage), url_unquote(key))
            inputname = url_unquote(frompage) + u'!' + url_unquote(key)

            default = getmetavalues(globaldata, frompage, key)
            default.append('')

            for val in default:
                wr(u'<td><input type="text" name="%s" value="%s">',
                   url_unquote(inputname), val)

            wr(u'</tr>\n')
            #print frompage, key, inputname, default, '<br>'

    wr(u'</table>\n')
    wr(u'<input type="submit" name="save" value="Save">\n')
    wr(u'</form>\n')

    globaldata.closedb()

## Test case: Ääää Päää new value, General Public changed value,
## Customer change multiple values (2)

#http://localhost/cgi-bin/moin.cgi/Lis%C3%A4%C3%A4%20l%C3%A4hde%20seurattavaksi?action=MetaTableEdit&args=||%C3%A4%C3%A4%C3%A4%C3%A4%20%C3%A4%C3%A4%C3%A4%C3%A4%7C|needs||

#Changes: {'General%20public': {'needs': {'new': [u'Not to be bothered by IT'], 'old': [u'Not to be bothered by IP problems']}}, 'Customer': {'needs': {'new': [u'Make money \xe4\xf6\xf6', u'Protect reputation \xe4\xf6\xf6', u'Keep customers happy'], 'old': [u'Make money', u'Protect reputation', u'Keep customers happy']}}, '%C3%84%C3%A4%C3%A4P%C3%A4%C3%A4': {'%C3%A4%C3%A4%C3%A4%C3%A4%20%C3%A4%C3%A4%C3%A4%C3%A4': {'new': [u'Uusi'], 'old': [u'']}}}



def process_editform(request, pagename):
    request.write(repr(request.form) + '<br>')

    globaldata = GraphData(request)

    changes = {}

    for input in request.form:
        # At least the key 'save' will be there and should be ignored
        if not '!' in input:
            continue
        
        newvals = request.form[input]

        keypage, key = [urlquote(x) for x in input.split('!')]

        oldvals = getmetavalues(globaldata, keypage, key)

        request.write("%s %s %s %s<br>\n" % (keypage, key,
                                          repr(newvals), repr(oldvals)))

        if oldvals != newvals:
            changes.setdefault(keypage, {})
            if not oldvals:
                changes[keypage].setdefault(key, {})['old'] = [u'']
            else:
                changes[keypage].setdefault(key, {})['old'] = oldvals
                
            changes[keypage].setdefault(key, {})['new'] = newvals

    request.write('<br>Changes: ' + repr(changes))

    # Done reading, will start writing now
    globaldata.closedb()

    for keypage in changes:
        for key in changes[keypage]:
            for i in range(len(changes[keypage][key]['old'])):
                request.write('<pre>')
                request.write(edit_meta(request,
                                        keypage.encode(config.charset),
                                        url_unquote(key),
                                        changes[keypage][key]['old'][i],
                                        changes[keypage][key]['new'][i]))
                request.write('</pre>')

#         if vals:
#             oldval = url_unquote(vals.pop()).strip('"')
#         else:
#             oldval = ''
#         assert isinstance(newval, unicode), newval
#         if newval != oldval:
#             request.write(u"<p> %s: " % keypage)
#             request.write(edit_meta(request, keypage.encode(config.charset),
#                                     key, oldval, newval))



def execute(pagename, request):
    request.http_headers()

    # This action generates data using the user language
    request.setContentLanguage(request.lang)

    title = request.getText('Metatable editor')
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

    if request.form.has_key('save'):
        process_editform(request, pagename)
    elif request.form.has_key('args'):
        args = ', '.join(request.form['args'])
        show_editform(request, pagename, args)
    else:
        show_queryform(request, pagename)

    # End content
    request.write(formatter.endContent()) # end content div
    # Footer
    wikiutil.send_footer(request, pagename)
