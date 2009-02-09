# -*- coding: utf-8 -*-"
"""
    MetaFormEdit action to MoinMoin
     - Editing page metadata usig the pages as forms of sort

    @copyright: 2008 by Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import re
import StringIO

from copy import copy

from MoinMoin import config
from MoinMoin import wikiutil
from MoinMoin.PageEditor import PageEditor
from MoinMoin.Page import Page

from graphingwiki.util import encode, actionname, form_escape, SEPARATOR

from savegraphdata import parse_text

value_re = re.compile('<input class="metavalue" type="text" ' +
                      'name="(.+?)" value="\s*(.*?)\s*">')

# Override Page.py to change the parser. This method has the advantage
# that it works regardless of any processing instructions written on
# page, including the use of other parsers
class FormPage(Page):

    def __init__(self, request, page_name, **keywords):
        # Cannot use super as the Moin classes are old-style
        apply(Page.__init__, (self, request, page_name), keywords)

    # It's important not to cache this, as the wiki thinks we are
    # using the default parser
    def send_page_content(self, request, body, format_args='',
                          do_cache=0, **kw):
        kw['format'] = 'wiki_form'
        kw['format_args'] = format_args
        kw['do_cache'] = 0
        apply(Page.send_page_content, (self, request, body), kw)

def wr(fmt, *args):
    args = tuple(map(form_escape, args))
    return fmt % args

def execute(pagename, request):
    _ = request.getText

    formpage = '../' * pagename.count('/') + pagename

    frm = wr(u'<form method="POST" action="%s">\n',
             actionname(request, pagename))+\
          wr(u'<input type="hidden" name="action" value="MetaEdit">\n')
    
    btn = '<div class="saveform"><p class="savemessage">' + \
          wr('<input type=submit name=saveform value="%s">',
             _('Save Changes')) + \
             wr('<input type=submit name=cancel value="%s">',
                _('Cancel')) +'</p></div>'

    # Template to use for any new pages
    template = request.form.get('template', [''])[0]
    if template:
        frm += '<input type="hidden" name="template" value="%s">' % template
    # Where to after saving page
    backto = request.form.get('backto', [''])[0]
    if backto:
        frm += '<input type="hidden" name="backto" value="%s">' % backto

    # Copying the request used to print the form. I do this to avoid
    # leaving modified requests running eg. when using
    # mod_python. Race conditions or interruptions/followups could
    # result in single or multiple aave buttons to appear at this
    # point.
    newreq = copy(request)
    newreq.cfg = copy(request.cfg)

    # The post-header and pre-footer texts seem to be implemented in themes.
    # Using post-header instead of page msg to avoid breaking header forms.
    newreq.cfg.page_header2 += frm + btn
    newreq.cfg.page_footer1 += btn + '</form>'

    newreq.page = FormPage(newreq, pagename)
    newreq.theme = copy(request.theme)
    newreq.theme.request = newreq
    newreq.theme.cfg = newreq.cfg

    error = ''
    newpage = False
    # If the page does not exist but we'd know how to construct it, 
    # replace the Page content with template and pretend it exists
    if template and not newreq.page.exists():
        template_page = wikiutil.unquoteWikiname(template)
        if newreq.user.may.read(template_page):
            editor = PageEditor(newreq, template_page)
            editor.user = newreq.user
            text = editor.get_raw_body()
            editor.page_name = pagename
            newreq.page.set_raw_body(editor._expand_variables(text))
            newreq.page.exists = lambda **kw: True
            newreq.page.lastEditInfo = lambda: {}
            newpage = True
        else:
            error = '<div class="saveform"><p class="savemessage">' + \
                    _("Cannot read template") + '</p></div>'

    elif not template and not newreq.page.exists():
        error = '<div class="saveform"><p class="savemessage">' + \
                _("No template specified, cannot edit") + '</p></div>'


    if error:
        newreq.cfg.page_header2 = request.cfg.page_header2 + error
        newreq.cfg.page_footer1 = request.cfg.page_footer1

    # Extra spaces from formatter need to be removed, that's why the
    # page is not sent as it is
    out = StringIO.StringIO()
    newreq.redirect(out)
    newreq.page.send_page()
    newreq.redirect()

    graphdata = request.graphdata
    graphdata.reverse_meta()
    vals_on_keys = graphdata.vals_on_keys

    # If we're making a new page based on a template, make sure that
    # the values from the evaluated template are included in the form editor
    if newpage:
        data = parse_text(newreq, newreq.page, newreq.page.get_raw_body())
        for page in data:
            for key in data[page].get('meta', dict()):
                for val in data[page]['meta'][key]:
                    vals_on_keys.setdefault(key, set()).add(val)

            for key in data[page].get('lit', dict()):
                for val in data[page]['lit'][key]:
                    vals_on_keys.setdefault(key, set()).add(val)

    def repl_subfun(mo):
        pagekey, val = mo.groups()

        msg = ""
        key = pagekey.split(SEPARATOR)[1]

        # Placeholder key key
        if key in vals_on_keys:
            msg += wr('<select name="%s">', pagekey)
            msg += wr('<option value=" ">%s</option>', _("None"))

            for keyval in sorted(vals_on_keys[key]):
                keyval = keyval.strip()
                if len(keyval) > 30:
                    showval = keyval[:27] + '...'
                else:
                    showval = keyval
                msg += wr('<option value="%s"%s>%s</option>',
                          keyval, val == keyval and ' selected' or '',
                          showval)

            msg += '</select>'

        msg += wr('<input class="metavalue" type="text" ' + \
                      'name="%s" value="">', pagekey)

        return msg

    data = out.getvalue()
    data = value_re.sub(repl_subfun, data)
    newreq.write(data)

    # Cleanup, avoid littering requests
    del newreq.page
    del newreq.theme
    del newreq.cfg
    del newreq
