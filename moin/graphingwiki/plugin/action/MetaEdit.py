# -*- coding: utf-8 -*-"
"""
    MetaEdit action to MoinMoin
     - Editing pages with certain metadata keys or values

    @copyright: 2007 by Erno Kuusela and Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

action_name = 'MetaEdit'

import cgi
import urllib

from MoinMoin import wikiutil
from MoinMoin import config

from graphingwiki.editing import process_edit, getvalues
from graphingwiki.editing import metatable_parseargs

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
    _ = request.getText

    def wr(fmt, *args):
        args = tuple(map(htmlquote, args))
        request.write(fmt % args)

    wr(u'<form method="GET" action="%s">\n', urlquote(pagename))
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(u'<input type="text" name="args">\n')

    wr(u'</table>\n')
    wr(u'<input type="submit" name="show" value="%s">\n', _("Edit table"))
    wr(u'</form>\n')

def show_editform(request, pagename, args):
    _ = request.getText

    def wr(fmt, *args):
        args = tuple(map(htmlquote, args))
        request.write(fmt % args)

    formpage = '../' * pagename.count('/') + urlquote(pagename)

    wr(u'<form method="POST" action="%s">\n', formpage)
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(u'<table>\n')
    wr(u'<tr><th>%s<th>%s<th>%s\n', _('Page name'), _('Key'), _('Value'))

    # Note that metatable_parseargs handles permission issues
    globaldata, pagelist, metakeys = metatable_parseargs(request, args,
                                                         globaldata=None,
                                                         all_keys=True)

    for frompage in sorted(pagelist):

        for key in metakeys:
            wr(u'<tr><td>%s<td>%s', url_unquote(frompage), url_unquote(key))
            inputname = url_unquote(frompage) + u'!' + url_unquote(key)

            default = list()
            for val, typ in getvalues(request, globaldata, frompage,
                                      key, display=False):
                default.append(val)

            default.append('')

            for val in default:
                wr(u'<td><input type="text" name="%s" value="%s">',
                   url_unquote(inputname), val)

            wr(u'</tr>\n')
            #print frompage, key, inputname, default, '<br>'

    wr(u'</table>\n')
    wr(u'<input type="submit" name="save" value="%s">\n', _('Save'))
    wr(u'</form>\n')

    globaldata.closedb()

def _enter_page(request, pagename):
    _ = request.getText
    
    title = _('Metatable editor')
    wikiutil.send_title(request, title,
                        pagename=pagename)
    # Start content - IMPORTANT - without content div, there is no
    # direction support!
    if not hasattr(request, 'formatter'):
        formatter = HtmlFormatter(request)
    else:
        formatter = request.formatter
    request.page.formatter = formatter

    request.write(request.page.formatter.startContent("content"))

def _exit_page(request, pagename):
    # End content
    request.write(request.page.formatter.endContent()) # end content div
    # Footer
    wikiutil.send_footer(request, pagename)

def execute(pagename, request):
    request.http_headers()
    _ = request.getText
    
    # This action generates data using the user language
    request.setContentLanguage(request.lang)

    if request.form.has_key('save'):
        msgs = process_edit(request, request.form)
        msg = ''

        for line in msgs:
            msg += line + request.formatter.linebreak(0)

        request.reset()
        request.page.send_page(request, msg=msg)
    elif request.form.has_key('args'):
        _enter_page(request, pagename)
        formatter = request.page.formatter
        
        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit metatable")))
        request.write(formatter.heading(0, 2))
        args = ', '.join(request.form['args'])
        show_editform(request, pagename, args)

        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        formatter = request.page.formatter

        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit current page")))
        request.write(formatter.heading(0, 2))
        show_editform(request, pagename, pagename)

        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit metatable")))
        request.write(formatter.heading(0, 2))
        show_queryform(request, pagename)

        _exit_page(request, pagename)
