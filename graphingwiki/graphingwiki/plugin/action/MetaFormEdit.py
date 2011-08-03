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

from graphingwiki import actionname, SEPARATOR
from graphingwiki.util import encode, format_wikitext, form_unescape
from graphingwiki.util import form_writer as wr

from graphingwiki.editing import get_properties

from savegraphdata import parse_text

value_re = re.compile('(<dt>.+?</dt>\s*<dd>\s*)<input class="metavalue" type="text" ' +
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

def execute(pagename, request):
    _ = request.getText

    if not request.user.may.write(pagename):
        request.reset()
        backto = request.form.get('backto', [None])[0]
        if backto:
            request.page = Page(request, backto)
        
        request.theme.add_msg(_('You are not allowed to edit this page.'), 
                              "error")
        request.page.send_page()
        return

    formpage = '../' * pagename.count('/') + pagename

    frm = wr(u'<form method="POST" enctype="multipart/form-data" action="%s">\n',
             actionname(request, pagename))+\
          wr(u'<input type="hidden" name="action" value="MetaEdit">\n')+\
          wr(u'<input type="hidden" name="gwikiseparator" value="%s">\n', SEPARATOR)
    
    btn = '<div class="saveform"><p class="savemessage">' + \
          wr('<input type=submit name=saveform value="%s">',
             _(request.form.get('saveBtnText', ['Save Changes'])[0])) + \
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
    request.sent_headers = True
    newreq.page.send_page()
    newreq.redirect()

    graphdata = request.graphdata
    vals_on_keys = graphdata.get_vals_on_keys()

    # If we're making a new page based on a template, make sure that
    # the values from the evaluated template are included in the form editor
    if newpage:
        data = parse_text(newreq, newreq.page, newreq.page.get_raw_body())
        for page in data:
            pagemeta = graphdata.get_meta(page)
            for key in pagemeta:
                for val in pagemeta[key]:
                    vals_on_keys.setdefault(key, set()).add(val)

    # Form types
    def form_selection(request, pagekey, curval, values, description=''):
        msg = wr('<select name="%s">', pagekey)
        msg += wr('<option value=""> </option>')
        
        for keyval, showval in values:
            msg += wr('<option value="%s"%s>%s</option>',
                      keyval, curval == keyval and ' selected' or '',
                      showval)

        msg += '</select>'

        return msg

    def form_checkbox(request, pagekey, curval, values, description=''):
        msg = ''

        for keyval, showval in values:
            msg += wr(
                '<input type="checkbox" name="%s" value="%s"%s>',
                pagekey, keyval, curval == keyval and ' checked' or '') + \
                '<label>' + format_wikitext(request, showval) +'</label>'

        return msg

    def form_radio(request, pagekey, curval, values, description=''):
        msg = ''

        for keyval, showval in values:
            msg += wr(
                '<input type="radio" name="%s" value="%s"%s>',
                pagekey, keyval, curval == keyval and ' checked' or '') + \
                '<label>' + format_wikitext(request, showval) +'</label>'

        return msg

    def form_textbox(request, pagekey, curval, values, description=''):
        return wr('<textarea name="%s">%s</textarea>',
                  pagekey, curval)

    def form_date(request, pagekey, curval, values, description=''):
        return wr('<input type="text" class="date" name="%s" value="%s">',
                pagekey, curval)

    def form_file(request, pagekey, curval, values, description=''):
        if curval:
            return wr('<input class="file" type="text" name="%s" value="%s" readonly>',
                  pagekey, curval)
        else:
            return wr('<input class="file" type="file" name="%s%s0" value="" readonly>',
                  pagekey, SEPARATOR)

    formtypes = {'selection': form_selection,
                 'checkbox': form_checkbox,
                 'textbox': form_textbox,
                 'textarea': form_textbox,
                 'radio': form_radio,
                 'date': form_date,
                 'file': form_file} 
    #, 'textarea']

    def repl_subfun(mo):
        dt, pagekey, val = mo.groups()

        pagekey = form_unescape(pagekey)
        msg = dt
        key = pagekey.split(SEPARATOR)[1]

        properties = get_properties(request, key)

        if properties.get('hidden'):
            return ""

        values = list()

        # Placeholder key key
        if key in vals_on_keys:
            for keyval in sorted(vals_on_keys[key]):
                keyval = keyval.strip()
                if len(keyval) > 30:
                    showval = keyval[:27] + '...'
                else:
                    showval = keyval

                values.append((keyval, showval))

        formtype = properties.get('hint')
        constraint = properties.get('constraint')
        desc = properties.get('description')
        default = properties.get('default', '')
        hidden = False

        if formtype == "hidden":
            hidden = True

        if not formtype in formtypes:
            formtype = "selection"

        if (not formtype == "radio" and
            not (formtype == "checkbox" and constraint == "existing")):
            cloneable = "true"
        else:
            cloneable = "false"
       
        if desc:
            msg = msg.replace('</dt>', ' %s</dt>'% request.formatter.icon('info'))
            msg = msg.replace('<dt>', wr('<dt class="mt-tooltip" title="%s" rel="%s">', key, desc))

        msg = msg.replace('<dd>', wr('<dd class="metaformedit" data-cloneable="%s" data-default="%s">',  cloneable, default))

        msg += formtypes[formtype](request, pagekey, val, values)


        if (not constraint == 'existing' and 
            not formtype in ['textbox', 'textarea', 'file', 'date']):
            msg += wr('<textarea name="%s"></textarea>', pagekey)

        if hidden:
            msg = request.formatter.div(1, css_class='comment') + msg + request.formatter.div(0)
        return msg

    data = out.getvalue()
    data = value_re.sub(repl_subfun, data)
    newreq.write(data)

    # Cleanup, avoid littering requests
    del newreq.page
    del newreq.theme
    del newreq.cfg
    del newreq
