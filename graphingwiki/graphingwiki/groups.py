# -*- coding: utf-8 -*-
"""
    Graphingwiki group page editing functions
     - Adding, deleting and renaming group members

    @copyright: 2014 by Juhani Eronen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import re

if __name__ == '__main__':
    # We need to import contexts before importing User, because otherwise
    # the relative imports in MoinMoin will fail.
    import MoinMoin.web.contexts

from MoinMoin.user import User
from MoinMoin.wikiutil import isGroupPage
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from editing import _test, _doctest_request

user_re = re.compile('(^ +\*\s*(.+)$\n?)', re.M)

def check_grouppage(request, grouppage):
    _ = request.getText

    if not isGroupPage(grouppage, request.cfg):
        return _('Not a valid group page: ') + grouppage
    if not request.user.may.write(grouppage):
        return _('You are not allowed to edit this page.')

    return ''

def check_users(request, accounts):
    _ = request.getText

    if not accounts:
        return _('No accounts specified.')
    for uname in accounts:
        if not User(request, name=uname).exists():
            return _('User not valid: ') + uname

    return ''    

def _group_add(request, pagetext, userlist):
    """
    >>> request = _doctest_request()
    >>> s = u"= @PAGE@ =\\n" + \
        u" * [[user2]]\\n" + \
        u" * [[user1]]\\n"

    >>> _group_add(request, s, ['user3'])
    u'= @PAGE@ =\\n * [[user3]]\\n * [[user2]]\\n * [[user1]]\\n'

    >>> s = u"#acl user:read,write,delete,revert,admin All:read\\n\\n" + \
        u" * [[user2]]\\n" + \
        u" * [[user1]]\\n"
    >>> _group_add(request, s, ['user3'])
    u'#acl user:read,write,delete,revert,admin All:read\\n\\n * [[user3]]\\n * [[user2]]\\n * [[user1]]\\n'

    >>> s = u''
    >>> _group_add(request, s, ['user3', 'user2'])
    u' * [[user2]]\\n * [[user3]]\\n'

    >>> s = u'This is a group page\\n'
    >>> _group_add(request, s, ['user3', 'user2'])
    u'This is a group page\\n * [[user2]]\\n * [[user3]]\\n'
    """
    if not userlist:
        return pagetext
    # Empty pages with only whitespace
    if not re.sub('\s', '', pagetext):
        pagetext = ''
    # 
    if not user_re.findall(pagetext):
        pagetext += u' * [[%s]]\n' % userlist[0]
        userlist = userlist[1:]
    for user in userlist:
        pagetext = user_re.subn(r' * [[%s]]\n\1' % user, pagetext, 1)[0]

    return pagetext

def _group_rename(request, pagetext, userlist):
    """
    >>> request = _doctest_request()
    >>> s = u"= @PAGE@ =\\n" + \
        u" * [[user2]]\\n" + \
        u" * [[user1]]\\n"

    Rename needs even-sized lists
    >>> _group_rename(request, s, ['user2'])
    u'= @PAGE@ =\\n * [[user2]]\\n * [[user1]]\\n'

    >>> _group_rename(request, s, ['user2', 'user3'])
    u'= @PAGE@ =\\n * [[user3]]\\n * [[user1]]\\n'
    >>> _group_rename(request, s, ['user1', 'user3'])
    u'= @PAGE@ =\\n * [[user3]]\\n * [[user2]]\\n'
    >>> _group_rename(request, s, ['user1', 'user3', 'user2', 'user4'])
    u'= @PAGE@ =\\n * [[user4]]\\n * [[user3]]\\n'

    >>> s = u"= @PAGE@ =\\n * [[user2]]\\n * [[user1]]\\n * [[user1]]\\n"
    >>> _group_rename(request, s, ['user1', 'user3'])
    u'= @PAGE@ =\\n * [[user3]]\\n * [[user2]]\\n'
    >>> s = u" * [[user2]]\\n"
    >>> _group_rename(request, s, ['user2', 'user3'])
    u' * [[user3]]\\n'
    """
    if not len(userlist) % 2:
        for user1, user2 in zip(userlist[::2], userlist[1::2]):
            pagetext = _group_del(request, pagetext, [user1])
            pagetext = _group_add(request, pagetext, [user2])

    return pagetext

def _group_del(request, pagetext, userlist):
    """
    >>> request = _doctest_request()
    >>> s = u"= @PAGE@ =\\n" + \
        u" * [[user2]]\\n" + \
        u" * [[user1]]\\n"

    Basic functions
    >>> _group_del(request, s, ['user2'])
    u'= @PAGE@ =\\n * [[user1]]\\n'
    >>> _group_del(request, s, ['user3'])
    u'= @PAGE@ =\\n * [[user2]]\\n * [[user1]]\\n'

    Double users might cause problems
    >>> s += u" * [[user1]]\\n"
    >>> _group_del(request, s, ['user1'])
    u'= @PAGE@ =\\n * [[user2]]\\n'

    >>> s = u" * [[user1]]\\n"
    >>> _group_del(request, s, ['user1'])
    u'\\n'
    """
    for user in userlist:
        pagetext = re.sub('(^\s+\*\s*(\[\[%s\]\])$\n?)' % user, '',
                          pagetext, flags=re.M)
    # empty group pages cannot be saved
    if not pagetext:
        pagetext = u'\n'
    return pagetext

def group_add(request, grouppage, accounts, create=False):
    _ = request.getText

    err = check_grouppage(request, grouppage)
    if err:
        return False, err
    err = check_users(request, accounts)
    if err:
        return False, err

    page = PageEditor(request, grouppage)
    if page.exists():
        members = request.groups[grouppage].members
    elif create:
        members = []
    else:
        return False, _('Group does not exist: ') + grouppage

    for uname in accounts:
        if uname in members:
            return False, _('User already in group: ') + uname
    pagetext = page.get_raw_body()
    if not pagetext:
        pagetext = ''
    newtext = _group_add(request, pagetext, accounts)
    msg = page.saveText(newtext, 0,
                        comment="Added to group: " + ', '.join(accounts))

    newmembers = request.groups[grouppage].members
    if not newmembers == members | set(accounts):
        msg = page.saveText(pagetext, 0,
                            comment="Reverting due to problems in group operation.")
        return False, _('Add unsuccessful for unknown reasons.')

    return True, msg

def group_del(request, grouppage, accounts):
    _ = request.getText

    err = check_grouppage(request, grouppage)
    if err:
        return False, err
    err = check_users(request, accounts)
    if err:
        return False, err

    page = PageEditor(request, grouppage)
    if page.exists():
        members = request.groups[grouppage].members
    else:
        return False, _('Group does not exist: ') + grouppage

    for uname in accounts:
        if uname not in members:
            return False, _('User not in group: ') + uname

    page = PageEditor(request, grouppage)
    pagetext = page.get_raw_body()
    newtext = _group_del(request, pagetext, accounts)
    msg = page.saveText(newtext, 0,
                        comment="Deleted from group: " + 
                        ', '.join(accounts))

    newmembers = request.groups[grouppage].members
    if not newmembers == members - set(accounts):
        msg = page.saveText(pagetext, 0,
                            comment="Reverting due to problems in group operation.")
        return False, _('Delete unsuccessful for unknown reasons.')

    return True, msg

def group_rename(request, grouppage, accounts):
    _ = request.getText

    err = check_grouppage(request, grouppage)
    if err:
        return False, err
    err = check_users(request, accounts)
    if err:
        return False, err

    if len(accounts) % 2:
        return False, _('Wrong number of arguments for rename.')

    page = PageEditor(request, grouppage)
    if page.exists():
        members = request.groups[grouppage].members
    else:
        return False, _('Group does not exist: ') + grouppage

    for uname in accounts[::2]:
        if uname not in members:
            return False, _('User not in group: ') + uname

    page = PageEditor(request, grouppage)
    pagetext = page.get_raw_body()
    newtext = _group_rename(request, pagetext, accounts)
    msg = page.saveText(newtext, 0,
                        comment="Changed group members: " + 
                        ' -> '.join(accounts))

    newmembers = request.groups[grouppage].members
    testmembers = members.copy()
    for user1, user2 in zip(accounts[::2], accounts[1::2]):
        testmembers.remove(user1)
        testmembers.add(user2)
    if testmembers != newmembers:
        msg = page.saveText(pagetext, 0,
                            comment="Reverting due to problems in group operation.")
        return False, _('Rename unsuccessful for unknown reasons.')

    return True, msg

if __name__ == "__main__":
    _test()
