#!/usr/bin/env python

from pyparsing import *
import sys, re, cPickle

# placeholder for data from another index, as the Wheeler data might
# be missing some rfc status stuff that is present in rfc-index.txt

refdata = {}

# keywords: Obsoletes, Obsoleted by, Updates, Updated by, See Also
#           Refs, Ref'ed By
#           S, DS, PS, I, E, H (- jos Obsoleted by)

stdlabels = {'STANDARD': 'S', 'DRAFT STANDARD': 'DS',
             'PROPOSED STANDARD': 'PS', 'INFORMATIONAL': 'I',
             'EXPERIMENTAL': 'E', 'HISTORIC': 'H'}

# Num STD Title of RFC, Author 1, .. Author N, Issue date (#pp)
# (.txt=nnnn .ps=nnnn) (FYI-#) (STD-#) (BCP-#) (RTR-#) (Obsoletes ##)
# (Updates ##) (Refs ##) (protocol) (was draft)

rfc = None
def rfcformat():
    global rfc
    if rfc is None:
        number = Word(nums).setResultsName('number')
        status = (Optional('-') +
                  Optional(oneOf('S DS PS I E H') +
                           FollowedBy(White())).setResultsName('Status'))

        name = SkipTo(',').setResultsName('Name')
        authors = SkipTo((Word(nums, exact=4) + "/")).suppress()
        year = Word(nums).setResultsName('Year') + SkipTo('(')

        pages = Optional(Literal('(') + Word(nums) + Literal('pp)')).suppress()
        format = Optional(Literal('(') +
                  delimitedList(oneOf('.txt= .ps= .pdf= .tar= .hastabs.txt=') +
                  Word(nums)) + Literal(')')).suppress()

        standard = Optional(Suppress('(') +
                            Word(alphas).setResultsName('Standard type') +
                            (Literal('-') + Word(nums) +
                             Literal(')')).suppress())

        refs = (Suppress('(Refs') +
                delimitedList(Word(nums)).setResultsName('Reference') +
                Suppress(')'))
        refed = (Suppress('(Ref\'ed') + Suppress('By') +
                 delimitedList(Word(nums)).setResultsName('ReferenceFrom') +
                 Suppress(')'))

        obs = (Suppress('(Obsoletes') +
               delimitedList(Word(nums)).setResultsName('Obsolete') +
               Suppress(')'))
        obsby = (Suppress('(Obsoleted') + Suppress('by') + 
                 delimitedList(Word(nums)).setResultsName('ObsoleteFrom') +
                 Suppress(')'))

        upd = (Suppress('(Updates') +
               delimitedList(Word(nums)).setResultsName('Update') +
               Suppress(')'))
        updby = (Suppress('(Updated') + Suppress('by') +
                 delimitedList(Word(nums)).setResultsName('UpdateFrom') +
                 Suppress(')'))

        seealso = (Suppress('(See') + Suppress('Also') +
                   delimitedList(Word(nums)).setResultsName('seealso') +
                   Suppress(')'))

        protocol = Optional(Suppress('(') +
                            Word(alphanums+'-/').setResultsName('Protocol') +
                            Suppress(')'))

        notissued = (number.suppress() + Suppress('Not') + Suppress('Issued'))
    
        rfc = (( number + status + name + authors + year + pages +
                 format + standard + ZeroOrMore(obsby | obs | updby | upd |
                 seealso | refs | refed) + protocol ) | notissued )

    return rfc

def makemapentry(data):
    map = {}
    for i in data.keys():
        # unclutter lists (ParseResults is a messy structure)
        if type(data[i]) == ParseResults:
            map[i] = []
            for j in data[i]:
                map[i].append(j)
        # strip extra line feeds and spaces from name
        elif i == 'Name':
            map[i] = re.compile("\s+").sub(" ", data[i])
        else:
            map[i] = data[i]

    # If the Wheeler data misses status but rfc-index.txt has
    # it,insert it.

    if not map.has_key('Status'):
        if refdata.has_key(map['number']):
            map['Status'] = refdata[map['number']]

    return map

# proc to get reference rfc data from rfc-index.txt

def getrefdata():
    global refdata

    reffile = file(sys.argv[1])
    rawdata = reffile.read()
    dd = rawdata.split("---------\n   \n\n\n")
    data = dd[1].split("\n\n")

    stdmatch = (Word(nums).setResultsName('number') +
                SkipTo('(Status:', include=True).suppress() +
                SkipTo(')').setResultsName('Status'))
    notissued = (Word(nums).suppress() + Suppress('Not') +
                 Literal('Issued').setResultsName('Status'))
    
    matchstr = stdmatch | notissued

    for i in data:
        match = matchstr.parseString(i)
        status = re.sub('\s+', ' ', match['Status'])
        if stdlabels.has_key(status):
            refdata[match['number']] = stdlabels[status]

def main():
    if len(sys.argv) > 1:
        getrefdata()
        
    data = sys.stdin.read()
    testdata = data.split("\n\n")
    results = {}
    format = rfcformat()
    for i in testdata:
        if len(i) > 0:
            res = format.parseString(i)
            if len(res) > 0:
                results[res['number']] = makemapentry(res)
    print cPickle.dumps(results)

if __name__ == "__main__":
    main()
