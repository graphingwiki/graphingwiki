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


from MoinMoin.wikimacro import Macro
from MoinMoin.parser.plain import Parser
def metatable_search():
    macro = Macro(Parser)

    all_pages = []
    
    keyspec = []

    # Regex preprocessing
    for arg in (x.strip() for x in args.split(',')):
        # Regexp, move on
        if '=' in arg:
            arglist.append(arg)
            continue

        # key spec, move on
        if arg.startswith('||') and arg.endswith('||'):
            # take order, strip empty ones
            keyspec = [encode(x) for x in arg.split('||') if x]
            continue

        # Normal pages, encode and move on
        if not regexp_re.match(arg):
            arglist.append(url_quote(encode(arg)))
            continue

        # if there's something wrong with the regexp, ignore it and move on
        try:
            page_re = re.compile("%s" % arg[1:-1])
        except:
            continue
        # Check which pages match to the supplied regexp
        for page in all_pages:
            if page_re.match(page):
                arglist.append(url_quote(encode(page)))

    globaldata = GraphData(macro.request).globaldata

    pages = set([])
    metakeys = set([])
    limitregexps = {}

    for arg in arglist:
        if arg.startswith('Category'):
            if not globaldata['in'].has_key(arg):
                # no such category
                continue
            for newpage in globaldata['in'][arg]:
                if not (newpage.endswith('Template') or
                        newpage.startswith('Category')):
                    pages.add(newpage)
        elif '=' in arg:
            data = arg.split("=")
            key = encode(data[0])
            val = encode('='.join(data[1:]))
            # If val starts and ends with /
            if val[::len(val)-1] == '//':
                val = val[1:-1]
            limitregexps.setdefault(key, set()).add(re.compile(val))
        elif arg:
            pages.add(arg)

    # If no pages specified, get all non-system pages
    if not pages:
        def filter(name):
            return not wikiutil.isSystemPage(macro.request, name)
        pages = set(macro.request.page.getPageList(filter=filter))

    pagelist = set([])

    for page in pages:
        clear = True
        # Filter by regexps (if any)
        if limitregexps:
            for key in limitregexps:
                if not clear:
                    break

                data = ', '.join(globaldata['meta'].get(page, {}).get(key, ""))

                # If page does not have the required key, do not add page
                if not data:
                    clear = False
                    break

                # If the found key does not match, do not add page
                for re_limit in limitregexps[key]:
                    if not re_limit.search(data):
                        clear = False
                        break

        # Add page if all the regexps have matched
        if clear:
            pagelist.add(page)

    out = '\n' + macro.formatter.table(1)

    if not keyspec:
        for page in pagelist:
            for key in globaldata['meta'].get(page, {}).keys():
                metakeys.add(key)

        metakeys = sorted(metakeys, key=str.lower)
    else:
        metakeys = keyspec
        
    # Give a class to headers to make it customisable
    out = out + macro.formatter.table_row(1, {'rowclass': 'meta_header'})
    out = out + t_cell(macro, '')
    for key in metakeys:
        out = out + t_cell(macro, key)
    out = out + macro.formatter.table_row(0)

    pagelist = sorted(pagelist)

    for page in pagelist:
        out = out + macro.formatter.table_row(1)
        out = out + t_cell(macro, page, head=1)
        for key in metakeys:
            data = ', '.join(globaldata['meta'].get(page, {}).get(key, ""))
            out = out + t_cell(macro, data)
            
        out = out + macro.formatter.table_row(0)

    out = out + macro.formatter.table(0)

    return out

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
