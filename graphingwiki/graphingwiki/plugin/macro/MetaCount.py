# -*- coding: utf-8 -*-"
"""
    Counts how many matches there are for given metatable query

    Show how many people there are:

    <<MetaCount(CategoryPerson)>>

    -> "2 matches for 'CategoryPerson'".

    If you want only the number, you can use "gwikisilent" argument.

    There are <<MetaCount(CategoryPerson, gwikisilent)>> people.

    -> "There are 2 people."

    @copyright: 2008 by therauli <therauli@ee.oulu.fi>
                2015 by Mika Seppänen <mika.seppanen@iki.fi>
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
from graphingwiki.util import text_escape
from graphingwiki.editing import metatable_parseargs

Dependencies = ['metadata']


def execute(macro, args):
    _ = macro.request.getText
    silent = False

    if args is None:
        args = ''
    else:
        args = args.strip().split(',')
        if args[-1].strip() == 'gwikisilent':
            silent = True
            args = args[:-1]

        args = ','.join(args)

    pagelist, metakeys, styles = metatable_parseargs(macro.request, args,
                                                     get_all_keys=True)

    if silent:
        return "{0}".format(len(pagelist))

    if not pagelist:
        return _("No matches for") + " '{0}'".format(text_escape(args))

    return "{0} {1} '{2}'".format(len(pagelist), _("matches for"),
                                  text_escape(args))
