# -*- coding: iso-8859-1 -*-
"""
    MetaData macro plugin to MoinMoin
     - Formats the semantic data visually

    @copyright: 2006 by Juhani Eronen <exec@iki.fi>
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
Dependencies = []

def execute(macro, args):
    arglist = args.split(',')
    showtype = 'list'
    
    if len(arglist) % 2:
        # Hidden values
        if arglist[-1].strip() == 'hidden':
            return ''
        if arglist[-1].strip() == 'embed':
            showtype = 'raw'

    result = []

    if showtype == 'list':
        if macro.formatter.in_p:
            result.append(macro.formatter.paragraph(0))

    # Failsafe for mismatched key, value pairs
    while len(arglist) > 1:
        key, val = arglist[:2]

        if showtype == 'list':
            result.extend([macro.formatter.definition_term(1),
                           macro.formatter.text(key),
                           macro.formatter.definition_term(0),
                           macro.formatter.definition_desc(1),
                           macro.formatter.text(val),
                           macro.formatter.definition_desc(0)])
        else:
            result.extend([macro.formatter.strong(1),
                           macro.formatter.text(key),
                           macro.formatter.strong(0),
                           macro.formatter.text(val)])

        arglist = arglist[2:]

    return u'\n'.join(result)
