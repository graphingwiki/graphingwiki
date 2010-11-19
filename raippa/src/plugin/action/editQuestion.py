#-*- coding: iso-8859-1 -*-
import random

from raippa.pages import Question, Answer
from raippa.user import User
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

question_options = ("redo", "answertype")
answer_options = ("answer", "tip", "comment", "value")

def sanitize(input):
    input = unicode(input)
    input = input.replace("\r", "")
    input = input.replace("\n", " ")
    return input.strip()

def save_new_question(request, pagename):
    page = PageEditor(request, pagename)
    template = Page(request, "QuestionTemplate").get_raw_body()

    try:
        msg = page.saveText(template, page.get_real_rev())
    except Exception, e:
        return False, unicode(e)

    return True, msg

def execute(pagename, request):
    user = User(request, request.user.name)
    success = False
    if user.is_teacher():
        if request.form.get("newQuestion", [u""])[0]:
            name = request.form.get("pagename", [u""])[0]
            if len(name) > 240:
                name = name[:240]
            success, msg =  save_new_question(request, name)
            
            Page(request, pagename).send_page(msg=msg)
            return

        question_options = {"option":list()} 
        if request.form.get("redo", [u'False'])[0] == u'True':
            question_options["option"].append("redo")

        if request.form.get("shuffle", [u'False'])[0] == u'True':
            question_options["option"].append("shuffle")

        anstype = request.form.get("answertype", [u""])[0]
        question_options["answertype"] = [anstype]
        
        answer_data = dict()
        if anstype != u"file":
            for key in request.form:
                if key.startswith("answer"):
                    try:
                        index = int(key[6:])
                    except (ValueError):
                        continue

                    answer = sanitize(request.form.get(key, [u""])[0])
                    if not answer:
                        continue

                    tip = sanitize(request.form.get("tip%i" % index, [u""])[0])
                    comment = sanitize(request.form.get("comment%i" % index, [u""])[0])
                    value = sanitize(request.form.get("value%i" % index, [u""])[0])
                    answer_options = request.form.get("option%i" % index, [u""])

                    answer_options = [x for x in answer_options if x in ["regexp", "latex"]] 
                    answer_data[index] = {"answer": [answer],
                                          "value" : [value],
                                          "tip" : [tip],
                                          "comment" : [comment],
                                          "option" : answer_options}

        else:
            for key in request.form.keys():
                if key.endswith('__filename__'):
                    if key.startswith("infile"):
                        index = 4
                        test_number = int(key[6:].split("_")[0])
                        file_number = int(key[6:].split("_")[1])
                    elif key.startswith("outfile"):
                        index = 5
                        test_number = int(key[7:].split("_")[0])
                        file_number = int(key[7:].split("_")[1])
                    else:
                        continue

                    filekey = key[:-12]
                    filename = request.form.get(key, unicode())
   
                    file = request.form.get(filekey, list())
                    if len(file) < 1:
                        continue 

                    content = file[1].value

                    if test_number != None and not answer_data.get(test_number, None):
                        answer_data[test_number] = ["", "", "", "", dict(), dict()]

                    answer_data[test_number][index][filename] = content

                elif key.startswith('old_infiles'):
                    test_number = int(key[11:].split("_")[0])

                    if test_number != None and not answer_data.get(test_number, None):
                        answer_data[test_number] = ["", "", "", "", dict(), dict()]

                    for filename in request.form[key]:
                        if answer_data[test_number][4].get(filename, None) == None:
                            answer_data[test_number][4][filename] = None

                elif key.startswith('old_outfiles'):
                    test_number = int(key[12:].split("_")[0])

                    if test_number != None and not answer_data.get(test_number, None):
                        answer_data[test_number] = ["", "", "", "", dict(), dict()]

                    for filename in request.form[key]:
                        if answer_data[test_number][5].get(filename, None) == None:
                            answer_data[test_number][5][filename] = None

                else:
                    test_number = None
                    index = None

                    if key.startswith('name') and request.form[key][0]:
                        test_number = int(key[4:])
                        index = 0
                    elif key.startswith('cmd') and request.form[key][0]:
                        test_number = int(key[3:])
                        index = 1
                    elif key.startswith('input') and request.form[key][0]:
                        test_number = int(key[5:])
                        index = 2
                    elif key.startswith('output') and request.form[key][0]:
                        test_number = int(key[6:])
                        index = 3

                    if test_number != None and not answer_data.get(test_number, None):
                        answer_data[test_number] = ["", "", "", "", dict(), dict()]

                    if test_number != None and index != None:
                        answer_data[test_number][index] = request.form[key][0]

        question = Question(request, pagename)
        success, msg = question.save(answer_data, question_options)
        if success:
            msg = u"Question saved successfully."
        else:
            msg = u"Saving failed!"
    else:
        msg = u"You need to be teacher to edit questions."


    if not success:
        request.theme.add_msg(msg, 'error')
        Page(request, pagename).send_page()
    else:
        Page(request, pagename).send_page(msg=msg)

