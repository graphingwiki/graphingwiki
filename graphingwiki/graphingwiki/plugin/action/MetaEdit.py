# -*- coding: utf-8 -*-"
"""
    MetaEdit action to MoinMoin
     - Editing pages with certain metadata keys or values

    @copyright: 2007 by Erno Kuusela and Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

action_name = 'MetaEdit'

from urllib import unquote as url_unquote

from MoinMoin import wikiutil
from MoinMoin.Page import Page

from graphingwiki.editing import get_metas, set_metas
from graphingwiki.editing import metatable_parseargs, edit_meta, save_template
from graphingwiki.util import actionname, form_escape, SEPARATOR, \
    decode_page

def fix_form(form):
    # Decode request form's keys using the config's charset
    # (Moin 1.5 request.form has its values - but not keys - decoded
    # into unicode, which tends to lead to hilarious situational
    # comedy).
    return dict([(decode_page(key), value) for (key, value) in form.items()])

def parse_editform(request, form):
    r"""
    >>> from graphingwiki.editing import _doctest_request
    >>> request = _doctest_request()

    >>> parse_editform(request, {"Test-gwikiseparator-" : ["1", "2"], ":: " : ["a"]})
    {'Test': ({}, {'a': ['1', '2']})}

    >>> request = _doctest_request({"Test" : {"meta" : {"a" : ["x"]}}})
    >>> parse_editform(request, {"Test-gwikiseparator-a" : ["1", "2"], ":: a" : ["a"]})
    {'Test': ({'a': ['x']}, {'a': ['1', '2']})}

    >>> request = _doctest_request({"Test" : {"meta" : {"a" : ["x"]}}})
    >>> parse_editform(request, {"Test-gwikiseparator-a" : ["x"], ":: a" : [""]})
    {'Test': ({'a': ['x']}, {'a': ['']})}

    >>> request = _doctest_request({"Test" : {"meta" : {"a" : ["1", "2"]}}})
    >>> parse_editform(request, {"Test-gwikiseparator-a" : ["1"], ":: a" : ["a"]})
    {'Test': ({'a': ['1', '2']}, {'a': ['1', '']})}
    """

    keys = dict()
    pages = dict()

    # Key changes
    for oldKey, newKeys in form.iteritems():
        if not newKeys or not oldKey.startswith(':: '):
            continue

        newKey = newKeys[0].strip()
        oldKey = oldKey[3:].strip()
        if oldKey == newKey:
            continue

        keys[oldKey] = newKey

    # Value changes
    for pageAndKey, newValues in form.iteritems():
        # At least the key 'save' may be there and should be ignored
        if not SEPARATOR in pageAndKey:
            continue

        # Form keys not autodecoded from utf-8
        page, oldKey = pageAndKey.split(SEPARATOR, 1)

        # Decoding pagename
        page = url_unquote(page)
        newKey = keys.get(oldKey, oldKey)

        if not request.user.may.write(page):
            continue

        oldMeta, newMeta = pages.setdefault(page, (dict(), dict()))

        if oldKey:
            oldMetas = get_metas(request, page, [oldKey], abs_attach=False)
            oldValues = oldMetas[oldKey]

            oldMeta.setdefault(oldKey, list()).extend(oldValues)

            if newKey != oldKey:
                # Remove the corresponding values
                newMeta.setdefault(oldKey, list()).extend([""] * len(oldValues))

        if newKey:
            missing = 0
            if oldKey:
                missing = len(oldValues) - len(newValues)

            newMeta.setdefault(newKey, list()).extend(newValues)
            newMeta.setdefault(newKey, list()).extend([""] * missing)

    # Prune
    for page, (oldMeta, newMeta) in list(pages.iteritems()):
        for key in list(newMeta):
            if key not in oldMeta:
                continue
            if oldMeta[key] != newMeta[key]:
                continue
            del oldMeta[key]
            del newMeta[key]

        if not (oldMeta or newMeta):
            del pages[page]

    return pages

def show_queryform(wr, request, pagename):
    _ = request.getText

    wr(u'<form method="GET" action="%s">\n',
       actionname(request, pagename))
    wr(u'<input type="text" size=50 name="args">\n')

    wr(u'<input type="submit" name="show" value="%s">\n', _("Edit table"))
    wr(u'</form>\n')

def show_editform(wr, request, pagename, args):
    formatter = request.formatter

    formpage = '../' * pagename.count('/') + pagename

    wr(u'<form method="POST" action="%s">\n',
       actionname(request, pagename))
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(formatter.table(1))
    wr(formatter.table_row(1, {'rowclass': 'meta_header'}))
    wr(formatter.table_cell(1, {'class': 'meta_page'}))

    template = request.form.get('template', [''])[0]
    if template:
        wr('<input type="hidden" name="template" value="%s">', template)

    # Note that metatable_parseargs handles permission issues
    pagelist, metakeys, _ = metatable_parseargs(request, args,
                                                get_all_keys=True)
    _ = request.getText

    for key in metakeys + ['']:
        wr(formatter.table_cell(1, {'class': 'meta_header'}))
        wr(u'<input class="metakey" type="text" name="%s" value="%s">',
           u':: %s' % key, key)
    wr(formatter.table_row(0))

    values = dict()
    valnos = dict()
    
    for frompage in pagelist:
        values[frompage] = dict()

        for key in metakeys + ['']:
            values[frompage][key] = list()
            # If the page has no values for this key, it'll
            # have one in the table to add a value
            if not valnos.has_key(frompage):
                valnos[frompage] = 1

            keydata = get_metas(request, frompage, [key], abs_attach=False)
                               

            for i, val in enumerate(keydata[key]):
                values[frompage][key].append(val)
                # Enumerate starts from 0: #values++ 
                # One to add a value: #values++ 
                if valnos[frompage] < i + 2:
                    valnos[frompage] = i + 2

            values[frompage][key].append('')


    for frompage in pagelist:
        wr(formatter.table_row(1))
        wr(formatter.table_cell(1, {'class': 'meta_page',
                                    'rowspan': str(valnos[frompage])}))
        wr(u'%s', frompage)

        for i in range(valnos[frompage]):
            # Add <tr>:s for additional values also
            if i > 0:
                wr(formatter.table_row(1))

            for key in metakeys + ['']:
                inputname = frompage + SEPARATOR + key

                if len(values[frompage][key]) >= (i + 1):
                    val = values[frompage][key][i]
                else:
                    val = ''

                # Skip default labels
                if key == 'label' and val == frompage:
                    val = ''
                
                wr(formatter.table_cell(1, {'class': 'meta_cell'}))
                wr(u'<input class="metavalue" type="text" name="%s" value="%s">',
                   inputname, val)

                #print frompage, key, inputname, values, '<br>'
            wr(formatter.table_row(0))

# Proto JS code to warn on leaving an empty key name
# <script language="JavaScript" type="text/javascript">
#    function myvalid(me) {
#      if (me.form.subject.value == "") {
#        if (confirm("Empty subject, send anyway?"))
#          return true;
#        else
#          return false;
#      }
#      return true;
#    }
# </script>
# <input type="submit" name="send" value="Send" class="button1"tabindex="7" onClick="return myvalid(this);" />

    wr(formatter.table(0))
    wr(u'<input type="submit" name="save" value="%s">\n', _('Save'))
    wr(u'<input type="submit" name="cancel" value="%s">\n', _('Cancel'))
    wr(u'</form>\n')

def _enter_page(request, pagename):
    _ = request.getText

    request.emit_http_headers()

    title = _('Metatable editor')
    request.theme.send_title(title,
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
    request.theme.send_footer(pagename)
    request.theme.send_closing_html()

def execute(pagename, request):
    _ = request.getText

    def wr(fmt, *args):
        args = tuple(map(form_escape, args))
        request.write(fmt % args)

    # This action generates data using the user language
    request.setContentLanguage(request.lang)
    form = fix_form(request.form)

    if form.has_key('cancel'):
        request.reset()
        backto = form.get('backto', [None])[0]
        if backto:
            request.page = Page(request, backto)
        
        request.page.send_page()
    elif form.has_key('save') or form.has_key('saveform'):
        template = form.get('template', [None])[0]

        # MetaFormEdit is much closer to set_meta in function
        if form.has_key('saveform'):
            added, discarded = {pagename: dict()}, {pagename: dict()}

            # Pre-create page if it does not exist, using the template specified
            if template:
                added[pagename]['gwikitemplate'] = template

            # Ignore form clutter
            keys = [x.split(SEPARATOR)[1] for x in form if SEPARATOR in x]

            old = get_metas(request, pagename, keys)

            for key in keys:
                oldkey = pagename + SEPARATOR + key
                oldvals = old.get(key, list())
                if not oldvals:
                    vals = [x.strip() for x in form[oldkey]
                            if x.strip()]
                    if vals:
                        added.setdefault(pagename, dict()).setdefault(key, list()).extend(vals)
                else:
                    discarded.setdefault(pagename, dict()).setdefault(key, list()).extend(oldvals)
                    added.setdefault(pagename, dict()).setdefault(key, list()).extend(form[oldkey])

            # Delete unneeded page keys in added/discarded
            pagenames = discarded.keys()
            for pagename in pagenames:
                if pagename in discarded and not discarded[pagename]:
                    del discarded[pagename]

            pagenames = added.keys()
            for pagename in pagenames:
                if pagename in added and not added[pagename]:
                    del added[pagename]

            # Save the template if needed
            if not Page(request, pagename).exists() and template:
                msgs = save_template(request, pagename, template)

            _, msgs = set_metas(request, dict(), discarded, added)

        else:
            # MetaEdit
            msgs = list()
            pages = parse_editform(request, form)

            if pages:
                saved_templates = False

                for page, _ in pages.iteritems():
                    # Save the template if needed
                    if not Page(request, page).exists() and template:
                        msgs.append(save_template(request, page, template))
                        saved_templates = True

                # If new pages were changed we need to redo parsing
                # the form to know what we really need to edit
                if saved_templates:
                    pages = parse_editform(request, form)

                for page, (oldMeta, newMeta) in pages.iteritems():
                    msgs.append('%s: ' % page + 
                                edit_meta(request, page, oldMeta, newMeta))
            else:
                msgs.append(request.getText('No pages changed'))
            
        msg = ''
        for line in msgs:
            msg += line + request.formatter.linebreak(0)

        request.reset()
        backto = form.get('backto', [None])[0]
        if backto:
            request.page = Page(request, backto)
        
        request.page.send_page(msg=msg)
    elif form.has_key('args'):
        _enter_page(request, pagename)
        formatter = request.page.formatter
        
        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit metatable")))
        request.write(formatter.heading(0, 2))
        args = ', '.join(form['args'])
        show_editform(wr, request, pagename, args)

        _exit_page(request, pagename)
    else:
        _enter_page(request, pagename)
        formatter = request.page.formatter

        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit current page")))
        request.write(formatter.heading(0, 2))
        show_editform(wr, request, pagename, pagename)

        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit metatable")))
        request.write(formatter.heading(0, 2))
        show_queryform(wr, request, pagename)

        _exit_page(request, pagename)

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
