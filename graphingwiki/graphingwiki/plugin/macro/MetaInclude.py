# -*- coding: utf-8 -*-"
"""
    MetaInclude macro plugin to MoinMoin/Graphingwiki
     - Shows in pages that match give metatable arguments
     - Uses MoinMoin's include
     - just add a ",," after metatable arguments and the rest of the
       arguments will be passed to moin's include

    @copyright: 2008 therauli <therauli@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""

from urllib import unquote as url_unquote

from MoinMoin import Page
from MoinMoin.macro import Include as moinInclude


from graphingwiki.editing import metatable_parseargs

def make_pagelist(pagelist):
    return "^" + "|".join(pagelist)

def execute(macro, args):
    # parse arguments
    if args is None:
        args = ''
        
    args = [x.strip() for x in args.split(',')]
    metatableargs = ''
    includeargs = ''

    split = None
    try:
        split = args.index('')
    except ValueError:
        metatableargs = ','.join(args)
        pass

    if split:
        metatableargs = ','.join(args[:split])
        includeargs = ','.join(args[split + 1:])
    

    #get pages
    pagelist, metakeys, styles = metatable_parseargs(macro.request, metatableargs, get_all_keys=True)

    #use MoinMoin's include to print the pages
    return moinInclude.execute(macro, make_pagelist(pagelist)+includeargs)
