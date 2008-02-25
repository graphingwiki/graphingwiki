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
from copy import copy

from MoinMoin import config
from MoinMoin.Page import Page

from graphingwiki.patterns import GraphData, encode, actionname

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

    frm = wr(u'<form method="POST" action="%s">\n',
             actionname(request, pagename))+\
          wr(u'<input type="hidden" name="action" value="MetaEdit">\n')
    
    btn = '<div class="saveform"><p class="savemessage">' + \
          request.formatter.text(_("Edit page as form")) + \
          wr('<input type=submit name=saveform value="%s">', _('Save')) + \
          '</p></div>'

    # Copying the request used to print the form. I do this to avoid
    # leaving modified requests running eg. when using
    # mod_python. Race conditions or interruptions/followups could
    # result in single or multiple aave buttons to appear at this
    # point.
    newreq = copy(request)
    newreq.cfg = copy(request.cfg)

    # Didn't find a good way to change the parser. One is this, the
    # other is to add a processing instructions line to the start of
    # the request.page._raw_body. The bad thing about this is that it
    # assumes wiki format to the pages received. Not so bad, then.
    newreq.cfg.default_markup = 'wiki_form'

    # The post-header and pre-footer texts seem to be implemented in themes.
    # Using post-header instead of page msg to avoid breaking header forms.
    newreq.cfg.page_header2 += frm + btn
    newreq.cfg.page_footer1 += btn + '</form>'

    newreq.page = Page(newreq, pagename)
    newreq.theme = copy(request.theme)
    newreq.theme.request = newreq
    newreq.theme.cfg = newreq.cfg

    # FIXME: what to do when the parser is overridden on the page with
    # processing instructions?

    # Here goes code to create page if it does not exist, if so desired?
    # send_page seems to contain the code to check this

    # Extra spaces from formatter need to be removed, that's why the
    # page is not sent as it is
    out = StringIO.StringIO()
    newreq.redirect(out)
    # It's important not to cache this, as the wiki
    # thinks this is done with its default parser
    newreq.page.send_page(newreq, do_cache=0)
    newreq.redirect()

    graphdata = GraphData(newreq)
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
    newreq.write(data)

    # Cleanup, avoid littering requests
    del newreq.page
    del newreq.theme
    del newreq.cfg
    del newreq
