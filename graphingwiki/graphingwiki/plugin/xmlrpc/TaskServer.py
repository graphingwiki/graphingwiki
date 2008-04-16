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

from graphingwiki.editing import metatable_parseargs, getmetas, getvalues
from SetMeta import execute as save_meta

def get_pagelist(request, status, globaldata=None):
    globaldata, pagelist, metakeys, _ = \
                metatable_parseargs(request,
                                    'CategoryTask, status=%s' % (status),
                                    globaldata)

    return globaldata, pagelist, metakeys

def execute(xmlrpcobj, agentid, oper='get',
            page='', result={}):
    request = xmlrpcobj.request
    _ = request.getText

    curtime = time()

    if oper == 'get':
        # First, get timed tasks, TBD
        pagelist = list()

        if not pagelist:
            # Then, get from pending tasks with overdue heartbeat
            globaldata, pages, metakeys = \
                        get_pagelist(request, 'pending')
            for page in pages:
                for val, typ in getvalues(request, globaldata,
                                          page, 'heartbeat'):
                    try:
                        val = float(val) + (10 * 60)
                        if val < curtime:
                            pagelist.append(page)
                    except ValueError:
                        pass

        if not pagelist:
            # Finally, get from open tasks
            globaldata, pagelist, metakeys = \
                        get_pagelist(request, 'open', globaldata)

        # Nothing to do...
        if not pagelist:
            globaldata.closedb()
            return ''
        
        random.shuffle(pagelist)
        for page in pagelist:
            stuff = getmetas(request, globaldata, page,
                             metakeys, display=False)
            metas = dict()
            for key in stuff:
                metas[key] = [x for x, y in stuff[key]]
            
            code = Page(request, page).get_raw_body()
            code = code.split('}}}', 1)[0]
            code = code.split('{{#!', 1)

            ret = save_meta(xmlrpcobj, page,
                            {'agent': [agentid], 'status': ['pending'],
                             'heartbeat': [str(curtime)]},
                            action='repl')

            if len(code) > 1 and not isinstance(ret, xmlrpclib.Fault):
                break

        globaldata.closedb()

        if not isinstance(ret, xmlrpclib.Fault):
            lang, code = code[-1].split('\n', 1)
            return page, metas, lang, code

        return xmlrpclib.Fault(3, _("Error: Could not save status!"))

#    a = file('/tmp/k', 'a')
#    a.write(repr(result))
#    a.flush()
#    a.close()

    # Page argument needed for actions beyond this point
    if not page:
        return xmlrpclib.Fault(1, _("Error: Page not specified!"))

    elif oper == 'change':
        result['heartbeat'] = [str(curtime)]
        ret = save_meta(xmlrpcobj, page, result, action='repl')

    elif oper == 'close':
        if result:
            metas, template = result
        else:
            metas = {page: {}}
            template = ''

        metas.setdefault(page, {})
        metas[page]['status'] = ['closed']
        metas[page]['heartbeat'] = [str(curtime)]
        for page in metas:
            ret = save_meta(xmlrpcobj, page, metas[page],
                            action='repl', template=template)

    else:
        return xmlrpclib.Fault(2, _("Error: No such operation '%s'!" % (oper)))

    if not isinstance(ret, xmlrpclib.Fault):
        return ret
    else:
        return xmlrpclib.Fault(3, _("Error: Could not save status!"))
