import re, os, codecs
from MoinMoin import config
from MoinMoin.parser.wiki import Parser

# does not work correctly with headers, at least!

def execute(pagename, request, text, pagedir):

    gfn = os.path.join(pagedir,'graphdata.pickle')
    #    f = open(gfn, 'wb')
    f = codecs.open(gfn, 'wb', config.charset)

    url_format_rules = """(?P<interwiki>[A-Z][a-zA-Z]+\:[^\s'\"\:\<\|]([^\s%(punct)s]|([%(punct)s][^\s%(punct)s]))+)
(?P<word>%(word_rule)s)
(?P<url_bracket>\[(?:(?:%(url)s)\:|#|\:)[^\s\]]+(?:\s[^\]]+)?\])
(?P<url>%(url_rule)s)
(?P<wikiname_bracket>\[".*?"\])""" % { 'punct': Parser.punct_pattern,
                               'url' : Parser.url_pattern,
                               'url_rule': Parser.url_rule,
                               'word_rule': Parser.word_rule,}

    rules = url_format_rules.replace('\n', '|')

    url_re = re.compile(rules, re.UNICODE)
    eol_re = re.compile(r'\r?\n', re.UNICODE)
    lines = eol_re.split(text)

    outstr = u""

    for line in lines:
        if line[0:2] == "##":
            continue
        for match in url_re.finditer(line):
            k = match.groupdict()
            for i in k.keys():
                if k[i] is not None:
                    outstr = outstr + i + " " + k[i] + "\n"

    f.write(outstr)
    f.close()
