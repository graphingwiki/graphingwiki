# -*- coding: utf-8 -*-"
"""
    MetaFormEdit action to MoinMoin
     - Editing page metadata usig the pages as forms of sort

    @copyright: 2008 by Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import cgi
import urllib
import re
import StringIO

from urllib import quote as url_quote

from MoinMoin import config
from MoinMoin.Page import Page

from graphingwiki.patterns import GraphData, encode

value_re = re.compile('<input class="metavalue" type="text" ' +
                      'name="(.+?)" value="\s*(.+?)\s*">')

def htmlquote(s):
    return cgi.escape(s, 1)

def urlquote(s):
    if isinstance(s, unicode):
        s = s.encode(config.charset)
    return urllib.quote(s)

def wr(fmt, *args):
    args = tuple(map(htmlquote, args))
    return fmt % args

def execute(pagename, request):
    request.http_headers()
    _ = request.getText

    formpage = '../' * pagename.count('/') + urlquote(pagename)

    request.page = Page(request, pagename)

    # Didn't find a good way to change the parser.
    # One is this, the other is to add a processing
    # instructions line to the start of the
    # request.page._raw_body
    temp_markup = request.page.cfg.default_markup
    # The bad thing about this is that it assumes wiki
    # format to the pages received. Not so bad, then.
    request.page.cfg.default_markup = 'wiki_form'

    # The post-header and pre-footer texts seem to be implemented in themes.
    # Using post-header instead of page msg to avoid breaking header forms.
    temp_footer = request.cfg.page_footer1
    temp_header = request.cfg.page_header2

    frm = wr(u'<form method="POST" action="%s">\n', formpage)+\
          wr(u'<input type="hidden" name="action" value="MetaEdit">\n')
    
    btn = '<div class="saveform"><p class="savemessage">' + \
          request.formatter.text(_("Edit page as form")) + \
          wr('<input type=submit name=saveform value="%s">', _('Save')) + \
          '</p></div>'

    request.cfg.page_header2 += frm + btn
    request.cfg.page_footer1 += btn + '</form>'

    # Here goes code to create page if it does not exist, if so desired?
    # send_page seems to contain the code to check this

    # Extra spaces from formatter need to be removed, that's why the
    # page is not sent as it is
    out = StringIO.StringIO()
    request.redirect(out)
    # It's important not to cache this, as the wiki
    # thinks this is done with its default parser
    request.page.send_page(request, do_cache=0)
    request.redirect()

    graphdata = GraphData(request)
    graphdata.reverse_meta()
    vals_on_keys = graphdata.vals_on_keys

    def repl_subfun(mo):
        pagekey, val = mo.groups()

        msg = ''
        key = url_quote(encode(pagekey.split('!')[1]))
        # Placeholder key key
        if key in vals_on_keys:
            msg = '<select name="%s">' % (pagekey)
            msg += '<option value=" ">None</option>'

            for keyval in vals_on_keys[key]:
                quotedval = htmlquote(keyval)
                if len(quotedval) > 30:
                    showval = quotedval[:27] + '...'
                else:
                    showval = quotedval
                msg += '<option value="%s"%s>%s</option>' % \
                       (quotedval,
                        val == keyval and ' selected' or '',
                        showval)

            msg += '</select>'

        msg += '<input class="metavalue" type="text" ' + \
               'name="%s" value="">' % (pagekey)
        return msg

    data = out.getvalue()
    data = value_re.sub(repl_subfun, data)
    request.write(data)

    request.page.cfg.default_markup = temp_markup 
    request.cfg.page_footer1 = temp_footer
    request.cfg.page_header2 = temp_header
