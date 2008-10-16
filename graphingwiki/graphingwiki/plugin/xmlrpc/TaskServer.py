#! -*- coding: utf-8 -*-"
"""
    TaskServer xmlrpc plugin to MoinMoin/Graphingwiki
     - "M" who hands out tasks to unsuspecting OpenCollab Agents and
       upkeeps task information

    @copyright: 2008 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import xmlrpclib
import random

from time import time

from MoinMoin.Page import Page

from graphingwiki.patterns import decode_page
from graphingwiki.editing import metatable_parseargs, get_metas

from AttachFile import save as save_attachment
from SetMeta import execute as save_meta

def get_pagelist(request, status):
    pagelist, metakeys, _ = \
        metatable_parseargs(request, 'CategoryTask, status=%s' % (status))

    return pagelist, metakeys

def execute(xmlrpcobj, agentid, oper='get',
            page='', status=('', ''), result={}, attach={}):
    request = xmlrpcobj.request
    _ = request.getText

    curtime = time()

    if oper == 'get':
        # First, get timed tasks, TBD
        pagelist = list()

        if not pagelist:
            # Then, get from pending tasks with overdue heartbeat
            pages, metakeys = get_pagelist(request, 'pending')
            for page in pages:
                pagehb = get_metas(request, page, ['heartbeat'])
                for val in pagehb.get('heartbeat', list()):
                    try:
                        val = float(val) + (10 * 60)
                        if val < curtime:
                            pagelist.append(page)
                    except ValueError:
                        pass

        if not pagelist:
            # Finally, get from open tasks
            pagelist, metakeys = get_pagelist(request, 'open')

        # Nothing to do...
        if not pagelist:
            return ''
        
        random.shuffle(pagelist)
        for page in pagelist:
            metas = get_metas(request, page, metakeys)

            code = Page(request, page).get_raw_body()

#            log = file('/tmp/log', 'a')
#            log.write('\n' + repr(code) + '\n')

            code = code.split('}}}', 1)[0]
#            log.write('\n' + repr(code) + '\n')
            code = code.split('{{#!', 1)
#            log.write('\n' + repr(code) + '\n')
#            log.flush()
#            log.close()

            ret = save_meta(xmlrpcobj, page,
                            {'agent': [agentid], 'status': ['pending'],
                             'heartbeat': [str(curtime)]},
                            action='repl')

            if len(code) > 1 and not isinstance(ret, xmlrpclib.Fault):
                break

        if not isinstance(ret, xmlrpclib.Fault):
            lang, code = code[-1].split('\n', 1)
            return page, metas, lang, code

        return xmlrpclib.Fault(3, _("Error: Could not save status!"))

    # Page argument needed for actions beyond this point
    if not page:
        return xmlrpclib.Fault(1, _("Error: Page not specified!"))

    result.setdefault(page, dict())
    result[page]['heartbeat'] = [str(curtime)]

    if oper == 'close':
        result[page]['status'] = ['closed']

    stdout, stderr = status
    if stderr or stdout:
        if stderr:
            ret = save_attachment(request, page, 'stderr.txt', stderr, True)
            result[page]['stderr'] = ['inline:stderr.txt']

        if stdout:
            ret = save_attachment(request, page, 'stdout.txt', stdout, True)
            result[page]['stdout'] = ['inline:stdout.txt']

        # If saving attachments fails for some reason or the other, bail out
        if not ret == True:
            return ret

    if oper in ['change', 'close']:
        for page in result:
            respage = result[page]
            attach = result[page].get('gwikiattachment', dict())
            if attach:
                del result[page]['gwikiattachment']

            ret = save_meta(xmlrpcobj, page, metas,
                            action='repl', template=template)

            for name in attach:
                ret = save_attachment(request, page,
                                      name, attach[name], True)

    else:
        return xmlrpclib.Fault(2, _("Error: No such operation '%s'!" % (oper)))

    if not isinstance(ret, xmlrpclib.Fault):
        return ret
    else:
        return xmlrpclib.Fault(3, _("Error: Could not save status!"))
