"""
>>> import sockserver
>>> c = sockserver.GraphChat(None, sockserver.MockDB())
>>> c.handle_request({'op': 'setitem', 'name': 'foo', 'value': 42})
{'status': 'ok'}
>>> c.handle_request({'op': 'setattr', 'name': 'foo', 'value': 42})
{'status': 'bad request, no such op: setattr'}
>>> c.handle_request({'op': 'getitem', 'name': 'foo', 'value': 42})
{'status': "bad arguments: getitem() got an unexpected keyword argument 'value'"}
>>> c.handle_request({'op': 'getitem', 'name': 'foo'})
{'status': 'ok', 'name': 'foo', 'value': 42}
>>> c = sockserver.GraphChat(None, sockserver.MockDB())
>>> c.handle_request({'op': 'setitem', 'name': 'foo', 'value': 42})
{'status': 'ok'}
>>> c.db.dbdict
{'foo': 42}
>>> c.handle_request({'op': 'begin'})
{'status': 'ok'}
>>> c.handle_request({'op': 'setitem', 'name': 'foo', 'value': 24})
{'status': 'ok'}
>>> c.db.dbdict
{'foo': 24}
>>> c.handle_request({'op': 'abort'})
{'status': 'ok'}
>>> c.db.dbdict
{'foo': 42}
>>> c.handle_request({'op': 'begin'})
{'status': 'ok'}
>>> c.handle_request({'op': 'setitem', 'name': 'foo', 'value': 24})
{'status': 'ok'}
>>> c.handle_request({'op': 'delitem', 'name': 'foo'})
{'status': 'ok', 'name': 'foo'}
>>> c.handle_request({'op': 'commit'})
{'status': 'ok'}
>>> c.handle_request({'op': 'commit'})
{'status': 'transaction stack empty'}
>>> c.handle_request({'op': 'abort'})
{'status': 'transaction stack empty'}
>>> c.handle_request({'op': 'delitem', 'name': 'foo'})
{'status': 'not-found', 'name': 'foo'}
"""


import doctest
if __name__ == '__main__':
    doctest.testmod()
