# -*- coding: utf-8 -*-"
"""
    showMetasJson
      - Shows meta values in a metatable kind a fasion in JSON 

    @copyright: 2008  <lauri.pokka@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use, copy,
    modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

"""

from MoinMoin.Page import Page
from raippa.pages import Question, Answer, Course, Task
from raippa import pages_in_category, to_json
from raippa.user import User

def question_stats(request, question):
    revisions = question.history_revisions()

    #total time and total try count
    stats = {"total": [0.0, 0]}

    for historypage in revisions:
        if not revisions.get(historypage, dict()):
            continue

        for rev_number in revisions[historypage]:
            rev = revisions[historypage][rev_number]
            students = rev[0]
            overallvalue = rev[1]
            right = rev[2]
            wrong = rev[3]
            date = rev[4]
            used_time = rev[5]

            for student in students:
                if student not in stats.keys():
                    #total time and total try count
                    stats[student] = {"total": [0.0, 0]}

                stats[student][date] = [overallvalue, right, wrong, used_time]
                stats[student]["total"][0] += used_time
                stats[student]["total"][1] += 1
                stats["total"][0] += used_time
                stats["total"][1] += 1

    return stats

def search_metas(request, keyword):
    """Searches for values and keys that match given argument and
        returns a list of dicts including matches as {key, value, page}
    """
    
    result = list()

    graphdata = request.graphdata
    graphdata.reverse_meta()
    keys_on_pages = graphdata.keys_on_pages
    vals_on_pages = graphdata.vals_on_pages

    return result

def search_pages(request, page):
    result = list()
    return result

def list_questions(request, search, all):
    result = list()
    questions =  pages_in_category(request, "CategoryQuestion")
    for qpage in questions:
        question = Question(request,qpage)
        title = question.title()
        task = question.task()
        incomplete = True

        if task:
            if not all:
                continue
            task = task.pagename

        if Page(request, qpage + '/options').exists():
            incomplete = False

        if not search and title or search and title.find(search) >= 0:
            result.append({"title": title, "page" : qpage, "incomplete" : incomplete, "task" : task})

    return result

def list_tasks(request, search, all):
    result = dict()
    course = Course(request, request.cfg.raippa_config)
    result["selected"] = course.flow.fullflow()
    result["free"] = dict()
    tasks = pages_in_category(request, "CategoryTask")
    for tpage in tasks:
        task = Task(request, tpage)
        title = task.title()
        result["titles"][tpage] = title
        if tpage not in result["selected"]:
            result["free"][tpage] = []


    return result

def search_meta_value(request, search):
    graphdata = request.graphdata
    graphdata.reverse_meta()
    vals_on_pages = graphdata.vals_on_pages
    pages = list(vals_on_pages.get(search, set([])))
    return pages

def has_done(request, search):
    user = User(request, request.user.name)
    instance = Question(request, search)
    checked = False
    done, status =  user.has_done(instance)
    if status not in [None, "picked", "pending"]:
        checked  = True
    return { "done" : done, "status" : status, "checked" : checked }

def execute(pagename, request):
    request.emit_http_headers()
    _ = request.getText

    search = request.form.get('s', [None])[0]
    args = request.form.get('args', [None])[0]

    if search and not args:
        pages = search_meta_value(request, search)
        request.write(to_json(pages))

    elif args == "questions":
        request.write(to_json(list_questions(request, search, True)))
    
    elif args == "tasks":
        request.write(to_json(list_tasks(request, search, True)))
    
    elif args == "has_done" and search:
        request.write(to_json(has_done(request, search)))

    elif args == "question_stats":
        request.write(to_json(question_stats(request, Question(request, pagename))))

    else:
        request.write(to_json(""))
    
    return