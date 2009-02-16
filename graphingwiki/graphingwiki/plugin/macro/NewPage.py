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

def macro_NewPage(macro, template=u'', button_label=u'', parent_page=u'', 
                  name_template=u'%s', edit_action=''):

    newpage = NewPage(macro, template, button_label,
                      parent_page, name_template)
    macrotext = newpage.renderInPage()

    if edit_action:
        macrotext = macrotext.replace('<input', actioninput % edit_action, 1)

    return macrotext

def execute(macro, *args):
    NewPage.arguments.append('edit_action')

    macro_NewPage(macro, *args)
