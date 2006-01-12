# method _write_file in MoinMoin.PageEditor is the function
# responsible for writing the page to a file, and shall be edited to
# save graph structure pickles.

# import custom util in the beginning, line 20 or so

### custom util for handling graph data

import MoinMoin.util.graphdata

# The change will be evident around line 805 of PageEditor.py

util.graphdata.saveGraphData(text, pagedir)

# Make a new MoinMoin/util/graphdata.py

import re

def saveGraphData(text, pagedir):

    gfn = os.path.join(pagedir,'graphdata.pickle')
    f = open(gfn, 'wb')

    punct_pattern = re.escape(u'''"\'}]|:,.)?!''')
    attachment_schemas = ["attachment", "inline", "drawing"]

    url_pattern = (u'http|https|ftp|nntp|news|mailto|telnet|wiki|file|' +
                   u'|'.join(attachment_schemas))
    
    url_rule = ur'%(url_guard)s(%(url)s)\:([^\s\<%(punct)s]|([%(punct)s][^\s\<%(punct)s]))+' % {
        'url_guard': u'(^|(?<!\w))',
        'url': url_pattern,
        'punct': punct_pattern,}
    
    url_format_rules = """
    (\[((%(url)s)\:|#|\:)[^\s\]]+(\s[^\]]+)?\])
    (%(url_rule)s)
    """ % { 'url' : url_pattern,
            'url_rule': url_rule,}

    url_re = re.compile(url_format_rules, r.UNICODE)

    urls = repr(url_re.findall(text))

    f.write(urls)
    f.close()

# formatting note, example on when to start a table:
# if we're not already in a table

# and if the first two charcters after indentation are "||"

# and if the last two characters of the line are "||", followed by an
# enter, which is converted into space in non-<pre> -mode to aid
# paragraph forming anyway

# and if there's more to the line than this
# -> we should start a table

if (not self.in_table and line[indlen:indlen + 2] == "||"
    and line[-3:] == "|| " and len(line) >= 5 + indlen):

# url matching full: (from parser/wiki.py)

    punct_pattern = re.escape(u'''"\'}]|:,.)?!''')
    attachment_schemas = ["attachment", "inline", "drawing"]

    url_pattern = (u'http|https|ftp|nntp|news|mailto|telnet|wiki|file|' +
            u'|'.join(attachment_schemas) +
            (config.url_schemas and u'|' + u'|'.join(config.url_schemas) or ''))
    url_rule = ur'%(url_guard)s(%(url)s)\:([^\s\<%(punct)s]|([%(punct)s][^\s\<%(punct)s]))+' % {
        'url_guard': u'(^|(?<!\w))',
        'url': url_pattern,
        'punct': punct_pattern,
    }

url_format_rules = """
(?P<url_bracket>\[((%(url)s)\:|#|\:)[^\s\]]+(\s[^\]]+)?\])
(?P<url>%(url_rule)s)
""" % { 'url': url_pattern,
        'url_rule': url_rule}

# related functions (parser/wiki.py): _url_repl, _url_bracket_repl

formatters:

    formatter.interwikilink
    formatter.url
    formatter.pagelink
