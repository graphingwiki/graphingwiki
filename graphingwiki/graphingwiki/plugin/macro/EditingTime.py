# -*- coding: iso-8859-1 -*-
"""
    EditingTime macro plugin to MoinMoin
    - Shows how much time people have spend editing page using user
      supplied idleThreshold

    @copyright: 2007 by Mika Seppänen
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

from MoinMoin.PageEditor import PageEditor
from MoinMoin.logfile import editlog
from MoinMoin import wikiutil

THRESHOLD = 60*5

def parseArgs(args):
    if not args:
        return THRESHOLD

    args = args.strip()
    if len(args) == 0:
        return THRESHOLD

    try:
        key, value = args.split("=")
    except:
        return THRESHOLD

    if key not in ["idleThreshold", "idlethreshold"]:
        return THRESHOLD

    try:
        value = int(value) * 60
    except:
        return THRESHOLD

    return value

def execute(macro, args):
    page = macro.formatter.page
    request = macro.formatter.request

    threshold = parseArgs(args)
    logfile = editlog.EditLog(request, page.getPagePath('edit-log', cherck_create=0, isfile=1))

    data = dict()
    users = dict()

    while True:
        try:
            entry = logfile.next()
            timestamp = entry.ed_time_usecs / (10**6)
            editor = entry.getEditor(request)
            id, value = entry.getInterwikiEditorData(request)
            if id == "ip":
                users["Anonymous"] = "Anonymous"
                editList = data.setdefault("Anonymous", list())
                editList.append(timestamp)
            else:
                users[entry.userid] = editor
                editList = data.setdefault(entry.userid, list())
                editList.append(timestamp)

        except StopIteration:
            break

    output = ""
    output += macro.formatter.table(1)

    output += macro.formatter.table_row(1)
    for i in ('Used time', "Editor"):
        output += macro.formatter.table_cell(1)
        output += macro.formatter.strong(1)
        output += macro.formatter.text(i)
        output += macro.formatter.strong(0)
        output += macro.formatter.table_cell(0)

    output += macro.formatter.table_row(0)

    outputList = list()

    for editor, editList in data.iteritems():
        usedTime = 0
        lastEdit = 0

        editList.sort()
        while True:
            try:
                timestamp = editList.pop(0)

                if lastEdit == 0:
                    lastEdit = timestamp
                    usedTime += threshold 
                    continue
    
                if (timestamp - lastEdit) < threshold:
                    usedTime += (timestamp - lastEdit)
                    lastEdit = timestamp
                else:
                    usedTime += threshold
                    lastEdit = timestamp
                    
            except IndexError:
                break


        outputList.append((usedTime, users[editor]))


    outputList.sort(reverse=True)
    for usedTime, editor in outputList:
        output += macro.formatter.table_row(1)
        output += macro.formatter.table_cell(1)
        output += macro.formatter.text("%.2f minutes" % (usedTime / 60.0))
        output += macro.formatter.table_cell(0)

        output += macro.formatter.table_cell(1)
        output += macro.formatter.rawHTML(editor)
        output += macro.formatter.table_cell(0)
        output += macro.formatter.table_row(0)

    output += macro.formatter.table(1)
    #output += macro.formatter.text("Idle threshold %d minutes." % (threshold / 60))
    return output 
