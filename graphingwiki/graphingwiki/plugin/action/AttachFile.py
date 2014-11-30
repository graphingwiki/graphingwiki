# -*- coding: utf-8 -*-"
"""
    AttachFile action plugin to MoinMoin/Graphingwiki
     - Extends MoinMoin AttachFile action with attachment diffing

    @copyright: 2009 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
from graphingwiki import values_to_form
from MoinMoin.action import AttachFile
from MoinMoin.support.werkzeug.datastructures import CombinedMultiDict, \
    MultiDict

def _do_diff(pagename, request):
    # return attachment list
    _ = request.getText

    form = values_to_form(request.values)

    att1 = form.get('att1', [''])[0]
    att2 = form.get('att2', [''])[0]
    sort = form.get('sort', ['normal'])[0]

    if (not (att1 and att2) or not 
        (AttachFile.exists(request, pagename, att1) and 
         AttachFile.exists(request, pagename, att2))):
        AttachFile.error_msg(pagename, request, 
                             _('Could not diff, attachments not selected or nonexisting'))
        return

    form['target'] = [att1]
    request.values = CombinedMultiDict([MultiDict(form)])
    pagename, filename, fpath = AttachFile._access_file(pagename, request)

    att1data = open(fpath, 'r').read()

    form['target'] = [att2]
    request.values = CombinedMultiDict([MultiDict(form)])
    pagename, filename, fpath = AttachFile._access_file(pagename, request)
    att2data = open(fpath, 'r').read()

    if sort == 'sort':
        att1data = '\n'.join(sorted(att1data.split('\n')))
        att2data = '\n'.join(sorted(att2data.split('\n')))
    elif sort == 'uniq':
        att1data = '\n'.join(sorted(set(att1data.split('\n'))))
        att2data = '\n'.join(sorted(set(att2data.split('\n'))))
    elif sort == 'cnt':
        att1tmp = list()
        for line in sorted(set(att1data.split('\n'))):
            if not line:
                continue
            att1tmp.append("%s %s" % (att1data.count(line), line))
        att2tmp = list()
        for line in sorted(set(att2data.split('\n'))):
            if not line:
                continue
            att2tmp.append("%s %s" % (att2data.count(line), line))
        att1data = '\n'.join(att1tmp)
        att2data = '\n'.join(att2tmp)

    # Use user interface language for this generated page
    request.setContentLanguage(request.lang)
    request.theme.send_title(_('Diff of %s and %s') % (att1, att2), 
                             pagename=pagename)
    request.write('<div id="content">\n') # start content div

    if request.user.show_fancy_diff:
        from MoinMoin.util import diff_html
        request.write(request.formatter.rawHTML(diff_html.diff(request, 
                                                               att1data, 
                                                               att2data)))
    else:
        from MoinMoin.util import diff_text
        lines = diff_text.diff(att1data, att2data)

        request.write(request.formatter.preformatted(1))
        for line in lines:
                if line[0] == "@":
                    request.write(f.rule(1))
                request.write(request.formatter.text(line + '\n'))
        request.write(request.formatter.preformatted(0))

    AttachFile.send_uploadform(pagename, request)
    request.write('</div>\n') # end content div
    request.theme.send_footer(pagename)
    request.theme.send_closing_html()

AttachFile._do_diff = _do_diff

info = AttachFile.info
execute = AttachFile.execute
