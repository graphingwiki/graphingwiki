# -*- coding: utf-8 -*-"
"""
    NewPage macro to MoinMoin/Graphingwiki
     - Extends the original MoinMoin macro

    @copyright: 2008 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
from MoinMoin.macro.NewPage import NewPage

Dependencies = ["language"]

actioninput = '<input type="hidden" name="editfunc" value="%s">\n<input'

def execute(macro, args):
    NewPage.arguments.append('editAction')

    newpage = NewPage(macro, args)
    macrotext = newpage.renderInPage()

    # Editaction allows for arbitrary action to be used for editing target page
    editfunc = newpage.args.get('editAction', '')

    macrotext = macrotext.replace('<input', actioninput % editfunc, 1)

    return macrotext
