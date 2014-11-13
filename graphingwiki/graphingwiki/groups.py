# -*- coding: utf-8 -*-
"""
    Graphingwiki group page editing functions
     - Adding, deleting and renaming group members
     - Supports only Wiki groups

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
from MoinMoin.PageEditor import PageEditor
from MoinMoin.datastruct.backends.wiki_groups import WikiGroup

from editing import _test, _doctest_request

user_re = re.compile('(^ +\*\s*(.+)$\n?)', re.M)


class GroupException(Exception):
    pass


def groups_by_user(request, account, recursive=False):
    _ = request.getText

    if not account:
        raise GroupException(_('No account specified.'))
    if not User(request, name=account).exists():
        raise GroupException(_('User not valid: ') + account)

    wiki_groups = set(group for group in
                      request.groups.groups_with_member(account) if
                      isinstance(request.groups[group], WikiGroup))
    if recursive:
        return wiki_groups
    else:
        return set(gn for gn in wiki_groups if
                   account in request.groups[gn].members)


def groups_by_user_transitive(request, account):
    """
    Returns the groups where the user is a member, as well as the
    groups which in turn have these groups as members.
    """
    real_groups = groups_by_user(request, account, recursive=False)
    recursive_groups = groups_by_user(request, account, recursive=True)
    return real_groups, recursive_groups - real_groups


def users_by_group(request, grouppage, recursive=False):
    _ = request.getText

    success, msg = check_grouppage(request, grouppage, writecheck=False)
    if not success:
        raise GroupException(msg + "(%s)" % (grouppage))

    if recursive:
        return request.groups[grouppage]
    else:
        return request.groups[grouppage].members


def check_grouppage(request, grouppage, writecheck=True, createcheck=True):
    _ = request.getText

    if createcheck:
        if not isGroupPage(grouppage, request.cfg):
            return False, _("Group does not exist.")
    if writecheck:
        if not request.user.may.write(grouppage):
            return False, _("You are not allowed to edit this page.")
    if not isinstance(request.groups[grouppage], WikiGroup):
        return False, _("Invalid group.")

    return True, ''


def check_users(request, accounts):
    _ = request.getText

    if not accounts:
        raise GroupException(_('No accounts specified.'))
    for uname in accounts:
        if not User(request, name=uname).exists():
            raise GroupException(_('User not valid: ') + uname)


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
        pagetext = re.sub('(?m)(^\s+\*\s*(\[\[%s\]\])$\n?)' % user, '',
                          pagetext)
    # empty group pages cannot be saved
    if not pagetext:
        pagetext = u'\n'
    return pagetext


def group_add(request, grouppage, accounts, create=False, usercheck=True):
    _ = request.getText

    success, msg = check_grouppage(request, grouppage, createcheck=not create)
    if not success:
        raise GroupException(msg + "(%s)" % (grouppage))

    if usercheck:
        check_users(request, accounts)

    page = PageEditor(request, grouppage)
    if page.exists():
        members = request.groups[grouppage].members | request.groups[grouppage].member_groups
    elif create:
        members = set([])
    else:
        raise GroupException(_('Group does not exist: ') + grouppage)

    for item in accounts:
        if item in members:
            raise GroupException(item + _(' already in group: ') + grouppage)

    pagetext = page.get_raw_body()
    if not pagetext:
        pagetext = ''
    newtext = _group_add(request, pagetext, accounts)
    msg = page.saveText(newtext, 0,
                        comment="Added to group: " + ', '.join(accounts))

    newmembers = request.groups[grouppage].members | request.groups[grouppage].member_groups
    if not newmembers == members | set(accounts):
        msg = page.saveText(pagetext, 0,
                            comment="Reverting due to problems in group operation.")
        raise GroupException(_('Add unsuccessful for unknown reasons.'))

    return True, msg


def group_del(request, grouppage, accounts):
    _ = request.getText
    
    success, msg = check_grouppage(request, grouppage)
    if not success:
        raise GroupException(msg + "(%s)" % (grouppage))

    members = request.groups[grouppage].members | request.groups[grouppage].member_groups

    for name in accounts:
        if name not in members:
            raise GroupException(name + _(' not in group: ') + grouppage)

    page = PageEditor(request, grouppage)
    pagetext = page.get_raw_body()
    newtext = _group_del(request, pagetext, accounts)
    msg = page.saveText(newtext, 0,
                        comment="Deleted from group: " +
                        ', '.join(accounts))

    newmembers = request.groups[grouppage].members | request.groups[grouppage].member_groups
    if not newmembers == members - set(accounts):
        msg = page.saveText(pagetext, 0,
                            comment="Reverting due to problems in group operation.")
        raise GroupException(_('Delete unsuccessful for unknown reasons.'))

    return True, msg


def group_rename(request, grouppage, accounts):
    _ = request.getText

    success, msg = check_grouppage(request, grouppage)
    if not success:
        raise GroupException(msg + "(%s)" % (grouppage))

    check_users(request, accounts[::2])

    if len(accounts) % 2:
        raise ValueError(_('Wrong number of arguments for rename.'))

    page = PageEditor(request, grouppage)
    if page.exists():
        members = request.groups[grouppage].members
    else:
        raise GroupException(_('Group does not exist: ') + grouppage)

    for uname in accounts[::2]:
        if uname not in members:
            raise GroupException(_('User not in group: ') + uname)

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
        raise GroupException(_('Rename unsuccessful for unknown reasons.'))

    return True, msg

if __name__ == "__main__":
    _test()
