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
from MoinMoin.action.AttachFile import add_attachment, AttachmentAlreadyExists
from MoinMoin.macro.Include import _sysmsg

from graphingwiki import actionname, SEPARATOR
from graphingwiki.editing import get_metas, set_metas, editable_p
from graphingwiki.editing import metatable_parseargs, edit_meta, save_template
from graphingwiki.util import form_escape, form_unescape, decode_page, enter_page
from graphingwiki.util import exit_page, delete_moin_caches

def fix_form(form):
    # Decode request form's keys using the config's charset
    # (Moin 1.5 request.form has its values - but not keys - decoded
    # into unicode, which tends to lead to hilarious situational
    # comedy).
    return dict([(form_unescape(decode_page(key)), value) 
                 for (key, value) in form.items()])

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
    _ = request.getText

    msgs = list()
    keys = dict()
    pages = dict()
    files = dict()

    # Key changes
    for oldKey, newKeys in form.iteritems():
        if oldKey.endswith("__filename__"):
            oldKey = oldKey[:-12]
            values = form.get(oldKey, None)
            if not values or len(values) < 3:
                continue

            fileobj = values[-1]
            if type(fileobj) != file:
                continue

            page, key = oldKey.split(SEPARATOR, 1)
            files.setdefault(page, dict())[key] = (newKeys, fileobj)
            continue

        if not newKeys or not oldKey.startswith(':: '):
            continue

        newKey = newKeys[0].strip()
        oldKey = oldKey[3:].strip()
        if oldKey == newKey:
            continue

        keys[oldKey] = newKey

    # Value changes
    for pageAndKey, newValues in form.iteritems():
        if pageAndKey.endswith("__filename__"):
            continue

        # At least the key 'save' may be there and should be ignored
        if not SEPARATOR in pageAndKey:
            continue

        # Form keys not autodecoded from utf-8
        page, oldKey = pageAndKey.split(SEPARATOR, 1)

        # Decoding pagename
        page = url_unquote(page)
        newKey = keys.get(oldKey, oldKey)

        if not request.user.may.write(page):
            err = '%s: ' % page + _('You are not allowed to edit this page.')
            if not err in msgs:
                msgs.append(err)
            continue

        oldMeta, newMeta = pages.setdefault(page, (dict(), dict()))

        if oldKey:
            oldMetas = get_metas(request, page, [oldKey], 
                                 abs_attach=False, includeGenerated=False)
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

    for page in files:
        metas = pages.get(page, (dict(), dict()))[1]
        for key in files[page]:
            filename, descriptor = files[page][key]
            values = metas.get(key, list())
            try:
                index = values.index(descriptor)
                values[index] = "[[attachment:%s]]" % filename
            except ValueError:
                values.append("[[attachment:%s]]" % filename)

    return pages, msgs, files

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

    # Note that metatable_parseargs handles read permission checks
    pagelist, metakeys, _ = metatable_parseargs(request, args,
                                                get_all_keys=True)

    uneditable_pages = list()
    # See that the user can write each page
    for page in pagelist:
        if not request.user.may.write(page):
            uneditable_pages.append(page)
    for page in uneditable_pages:
        pagelist.remove(page)

    _ = request.getText

    if uneditable_pages:
        reason = _("No save permission to some pages (%s)" % 
                   ','.join(uneditable_pages))
        wr(_sysmsg % ('warning', reason))

    if not pagelist:
        reason = _("No pages to edit.")
        wr(_sysmsg % ('error', reason))
        return

    wr(u'<form method="POST" action="%s" enctype="multipart/form-data">\n',
       actionname(request, pagename))
    wr(u'<input type="hidden" name="action" value="%s">\n', action_name)
    wr(formatter.table(1))
    wr(formatter.table_row(1, {'rowclass': 'meta_header'}))
    wr(formatter.table_cell(1, {'class': 'meta_page'}))

    template = request.form.get('template', [''])[0]
    if template:
        wr('<input type="hidden" name="template" value="%s">', template)

    # Filter out uneditables, such as inlinks
    metakeys = editable_p(metakeys)

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

            keydata = get_metas(request, frompage, [key], 
                                abs_attach=False, includeGenerated=False)

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
                wr(u'<textarea class="metavalue dynamic"  name="%s">%s</textarea>',
                   inputname, val)

                #print frompage, key, inputname, values, '<br>'
            wr(formatter.table_row(0))

        wr(formatter.table_row(1))
        wr(formatter.table_cell(1, {'class': 'meta_cell'}))
        for key in metakeys + ['']:
            inputname = frompage + SEPARATOR + key

            if len(values[frompage][key]) >= (i + 1):
                val = values[frompage][key][i]
            else:
                val = ''

            # Skip default labels
            if key == 'label' and val == frompage:
                val = ''

            wr(formatter.table_cell(1))
            wr(u'<input class="metavalue" type="file" name="%s">\n', inputname)

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

    if uneditable_pages:
        reason = _("No save permission to some pages (%s)" % 
                   ','.join(uneditable_pages))
        wr(_sysmsg % ('warning', reason))

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
        
        request.theme.add_msg(_('Edit was cancelled.'), "error")
        request.page.send_page()
    elif form.has_key('save') or form.has_key('saveform'):
        if request.request_method != 'POST':
            request.page.send_page()
            return

        template = form.get('template', [None])[0]

        # MetaFormEdit is much closer to set_meta in function
        if form.has_key('saveform'):
            added, discarded = {pagename: dict()}, {pagename: dict()}

            # Pre-create page if it does not exist, using the template specified
            if template:
                added[pagename]['gwikitemplate'] = template

            # Ignore form clutter
            ignore = set()
            files = dict()
            for key in form:
                if key.endswith("__filename__"):
                    ignore.add(key)
                    ignore.add(key[:-12])
                    filename = form.get(key, None)
                    fileobj = form.get(key[:-12], [None])[-1]
                    if not filename and not fileobj:
                        continue

#                    if type(fileobj) != file:
#                        continue

                    banana = key.split(SEPARATOR)
                    keys = files.setdefault(banana[0], dict())
                    values = keys.setdefault(banana[1], list())
                    values.append((filename, fileobj))

            keys = list()
            for key in form:
                if key not in ignore and SEPARATOR in key:
                    keys.append(key.split(SEPARATOR)[1])
#            keys = [x.split(SEPARATOR)[1] for x in form if SEPARATOR in x]

            old = get_metas(request, pagename, keys, includeGenerated=False)
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

            msgs = list()
            # Add attachments
            for pname in files:
                for key in files[pname]:
                    for value in files[pname][key]:
                        name = value[0]
                        try:
                            t, s = add_attachment(request, pname, name, value[1])
                            added.setdefault(pname, dict()).setdefault(key, list()).append("[[attachment:%s]]" % name)
                        except AttachmentAlreadyExists:
                            msgs = ["Attachment '%s' already exists." % name]
                            

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
                msgs.append(save_template(request, pagename, template))

            _, msgss = set_metas(request, dict(), discarded, added)
            msgs.extend(msgss)

        else:
            # MetaEdit
            pages, msgs, files = parse_editform(request, form)

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
                    pages, newmsgs, files = parse_editform(request, form)

                for page, (oldMeta, newMeta) in pages.iteritems():
                    msgs.append('%s: ' % page + 
                                edit_meta(request, page, oldMeta, newMeta))

                for page in files:
                    for key in files[page]:
                        name, content = files[page][key]
                        t, s = add_attachment(request, page, name, content) 
            else:
                msgs.append(request.getText('No pages changed'))

        msg = ''
        for line in msgs:
            msg += line + request.formatter.linebreak(0)

        request.reset()
        delete_moin_caches(request, request.page)
        backto = form.get('backto', [None])[0]
        if backto:
            request.page = Page(request, backto)
        
        request.theme.add_msg(msg)
        request.page.send_page()
    elif form.has_key('args'):
        enter_page(request, pagename, 'Metatable editor')
        formatter = request.page.formatter
        
        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit metatable")))
        request.write(formatter.heading(0, 2))
        args = ', '.join(form['args'])
        show_editform(wr, request, pagename, args)

        exit_page(request, pagename)
    else:
        enter_page(request, pagename, 'Metatable editor')
        formatter = request.page.formatter

        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit current page")))
        request.write(formatter.heading(0, 2))
        show_editform(wr, request, pagename, pagename)

        request.write(formatter.heading(1, 2))
        request.write(formatter.text(_("Edit metatable")))
        request.write(formatter.heading(0, 2))
        show_queryform(wr, request, pagename)

        exit_page(request, pagename)

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
