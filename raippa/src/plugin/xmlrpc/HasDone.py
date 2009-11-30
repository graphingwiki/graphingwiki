#! -*- coding: utf-8 -*-"
"""
    HasDone.py -- Tells if user has done a given task/question
"""
import xmlrpclib

from MoinMoin.Page import Page
from MoinMoin.user import getUserId

from raippa.user import User as RaippaUser
from raippa.pages import Task, Question
from raippa import raippacategories as rc

from graphingwiki.editing import get_metas


def execute(xmlrpcobj, username, pagename):
    request = xmlrpcobj.request
    _ = request.getText

    if not Page(request, pagename).exists():
        return xmlrpclib.Fault(1, _('No such page %s' % pagename))

    if not getUserId(request, username):
        return xmlrpclib.Fault(1, _('No such user %s' % username))    
    
    user = RaippaUser(request, username)

    metas = get_metas(request, pagename, ['gwikicategory'])

    if rc['question'] in metas['gwikicategory']:
        page = Question(request, pagename)
    elif rc['task']:
        page = Task(request, pagename)
    else:
        return  xmlrpclib.Fault(1, _('Page %s not in question or task category' % pagename))

    return user.has_done(page)
