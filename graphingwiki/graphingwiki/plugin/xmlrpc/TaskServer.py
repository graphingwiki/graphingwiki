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
import cPickle

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

def get_targets(request, metas):
    check_meta = metas.get('gwikitargetmeta', list())


    if metas.get('gwikitarget', list()):
        targets = list()
        for target in metas['gwikitarget']:
            pagelist, _, _ = \
                metatable_parseargs(request, target)

            if check_meta:
                for page in pagelist:
                    temp_meta = get_metas(request, page, check_meta)
                    for temp in check_meta:
                        if not temp_meta.get(temp, list()):
                            targets.append(page)

            else:
                targets.extend(pagelist)
        metas['gwikitarget'] = targets

    log.flush()
    log.close()

    return metas

def execute(xmlrpcobj, agentid, oper='get',
            page='', status=('', ''), data=''):
    try:
        result, attach = cPickle.loads(data)
    except EOFError:
        result, attach = dict(), dict()

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

            metas = get_targets(request, metas)

            code = Page(request, page).get_raw_body()

            code = code.split('}}}', 1)[0]
            code = code.split('{{#!', 1)

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

    if oper == 'close' and not result[page].get('status', str()):
        result[page]['status'] = ['closed']

    stdout, stderr = status
    if stderr or stdout:
        if stderr:
            ret = save_attachment(request, page, 'stderr.txt', stderr, True)
#            result[page]['stderr'] = ["inline:stderr.txt"]

        if stdout:
            ret = save_attachment(request, page, 'stdout.txt', stdout, True)
#            result[page]['stdout'] = ["inline:stdout.txt"]

        # If saving attachments fails for some reason or the other, bail out
        if not ret == True:
            return ret

    if oper in ['change', 'close']:
        for page in result:
            respage = result[page]
            att = attach.get(page, dict())

            ret = save_meta(xmlrpcobj, page, respage, action='repl')

            for name in att:
                ret = save_attachment(request, page,
                                      name, att[name], True)

    else:
        return xmlrpclib.Fault(2, _("Error: No such operation '%s'!" % (oper)))

    if not isinstance(ret, xmlrpclib.Fault):
        return ret
    else:
        return xmlrpclib.Fault(3, _("Error: Could not save status!"))
