 # -*- coding: iso-8859-1 -*-
import time

from MoinMoin import user
from MoinMoin.Page import Page
from MoinMoin.wikiutil import get_unicode

from graphingwiki.editing import get_keys, get_metas

Dependencies = ['metadata']
generates_headings = False

def get_comments(request, pagename):
    if not Page(request, pagename).exists():
        return dict()
    else:
        keys = get_keys(request, pagename)
        metas = get_metas(request, pagename, keys, checkAccess=False)

        comments = dict()

        for commenttime, commentlist in metas.iteritems():
            if valid_time(commenttime):
                comments[commenttime] = list()
                for comment in commentlist:
                    try:
                        sender = comment[comment.rindex("--")+3:]
                        comment = comment[:comment.rindex("--")]
                    except ValueError:
                        sender = "Anonymous"

                    comments[commenttime].append((comment, sender))

        return comments

def valid_time(commenttime):
    try:
        time.strptime(commenttime, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False

    return True

def comment_gui(request, f, commentpage, comments):
    result = list()
    result.append(f.rawHTML('<form method="post">'))
    result.append(f.rawHTML('<input type="hidden" name="action" value="comments">'))
    result.append(f.rawHTML('<input type="hidden" name="commentpage" value="%s">' % commentpage))
    result.append(f.rawHTML('<textarea rows="10" cols="60" name="comment"></textarea><br>'))
    result.append(f.rawHTML('<input type="submit" name="submit" value="Submit">'))
    result.append(f.rawHTML('</form>'))

    return result

def macro_Comments(macro, commentpage):
    request = macro.request
    formatter = macro.formatter
    page = macro.request.page
    pagename = macro.request.page.page_name
    page = macro.request.page

    commentpage = get_unicode(request, commentpage)
    if not commentpage:
        commentpage = "%s/comments" % pagename

    comments = get_comments(request, commentpage)

    result = list()
    result.extend(comment_gui(request, formatter, commentpage, comments))

    result.append(formatter.table(1))
    for commenttime in sorted(comments.keys()):
        commentlist = comments[commenttime]

        for comment, sender in commentlist:
            if sender.startswith('[[') and sender.endswith(']]'):
                sender = sender[2:-2]

            result.append(formatter.table_row(True))
            result.append(formatter.table_cell(True))

            result.append(formatter.text(commenttime+" "))

            if user.User(request, user.getUserId(request, sender)).exists():
                result.append(formatter.pagelink(True, sender))
                result.append(formatter.text(sender))
                result.append(formatter.pagelink(False, sender))
            else:
                result.append(formatter.text('Anonymous'))

            result.append(formatter.bullet_list(True))
            result.append(formatter.listitem(True))
            result.append(formatter.text(comment))
            result.append(formatter.listitem(False))
            result.append(formatter.bullet_list(False))

            result.append(formatter.table_cell(False))
            result.append(formatter.table_row(False))

    result.append(formatter.table(False))

    return "".join(result) 
