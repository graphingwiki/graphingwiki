#! -*- coding: utf-8 -*-"
"""
    HasDone.py -- Tells if user has done a given task/question
"""
import urllib
 
from raippa.user import User
from raippa.pages import Task, Question
from graphingwiki.editing import get_metas
from raippa import raippacategories as rc

def execute(xmlrpcobj, username, pagename):
    request = xmlrpcobj.request
    _ = request.getText
    
    metas = get_metas(request, pagename, ['gwikicategory'])
    
    user = User(request, username)

    if rc['question'] in metas['gwikicategory']:
        page = Question(request, pagename)

        return user.hasdone(user, page)
    elif rc['task']:
        page = Task(request, pagename)
        return user.hasdone(user, page)

    return None, None
