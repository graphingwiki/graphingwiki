import os
import sys
import xmlrpclib
import doctest

import shutil
import tempfile
import time

utils = """# -*- coding: latin-1 -*-
import subprocess

def runProgram(myInput="", myFile='ratkaisu.py', printReturnValue = False, parameters = []):
    p = subprocess.Popen(["python", myFile] + parameters, shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin = subprocess.PIPE)
    result = p.communicate(myInput)
    if printReturnValue:
        return result + (p.returncode,) 

    return result
"""

def error(msg):
    print "[error] %s" % msg

def info(msg):
    print "[info] %s" % msg

def stripLink(input):
    return input.lstrip("[").rstrip("]")

def stripFormat(input):
    lines = input.split("\n")
    if lines[0].startswith("#FORMAT"):
        return "\n".join(lines[1:])
    return input

name = "bot"
password = "f029hgh="
wikiurl = "http://www.raippa.fi/"

course = "Course/521141P_Autumn2008"

wiki = xmlrpclib.ServerProxy(wikiurl + "?action=xmlrpc2", allow_none=True)
authToken = wiki.getAuthToken(name, password)

while True:
    mc = xmlrpclib.MultiCall(wiki)
    mc.applyAuthToken(authToken)
    mc.GetMeta("CategoryHistory, overallvalue=pending, course=%s" % course, False)

    picked = None

    for result in mc():
        if result == "SUCCESS":
            continue

        header = result[0]
        pages = result[1:]
        info("Found %d history pages waiting for checking" % len(pages))

        for page in pages:
            pagename = page[0]
            metaList = page[1:]
            metas = dict()

            for key, values in zip(header, metaList):
                metas[key] = values

            picked = (pagename, metas)

    if picked is None:
        time.sleep(10)
        continue

    info("Picked %s." % picked[0])

    mc = xmlrpclib.MultiCall(wiki)
    mc.applyAuthToken(authToken)

    metas2 = dict()
    metas2["overallvalue"] = ["picked"]
    mc.SetMeta(picked[0], metas2, "repl", True)

    try:
        results = [r for r in mc()]
    except xmlrpclib.Fault, fault:
        if fault.faultString.find("You did not change") == -1:
            sys.exit(str(fault))
    
    for result in results:
        if result == "SUCCESS":
            continue

        info(repr(result))

    files = metas["file"]
    if len(files) != 1:
        error("Found %d solution files" % len(files))
        continue
    else:
        file = stripLink(files[0])

    questions = metas["question"]
    if len(questions) != 1:
        error("Found %d questions" % len(questions))
        continue
    else:
        question = stripLink(questions[0])

    info("Fetching solution from %s" % file)
    mc = xmlrpclib.MultiCall(wiki)
    mc.applyAuthToken(authToken)
    mc.getPage(file)

    for result in mc():
        if result == "SUCCESS":
            continue

        solution = stripFormat(result)

    info("Fetching right answer from %s" % question)
    mc = xmlrpclib.MultiCall(wiki)
    mc.applyAuthToken(authToken)
    mc.GetMeta("CategoryAnswer, question=%s" % question, False)

    for result in mc():
        if result == "SUCCESS":
            continue

        header = result[0]
        pages = result[1:]
        if len(pages) != 1:
            error("Found %d answer pages" % len(pages))
            sys.exit(1)

        for page in pages:
            pagename = page[0]
            metaList = page[1:]
            metas = dict()

            for key, values in zip(header, metaList):
                metas[key] = values

            trues = metas["true"]
            if len(trues) != 1:
                error("Found %d true metakeys from %s" % (len(trues), pagename))
                sys.exit(1)

            tests = stripLink(trues[0])

    info("Fetching doctests from %s" % file)
    mc = xmlrpclib.MultiCall(wiki)
    mc.applyAuthToken(authToken)
    mc.getPage(tests)

    for result in mc():
        if result == "SUCCESS":
            continue

        tests = stripFormat(result)

    path = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(path)
    sys.path.append(path)
    info("Created tempdir %s" % path)

    open(os.path.join(path, "ratkaisu.py"), "w").write(solution)
    open(os.path.join(path, "tests.txt"), "w").write(tests)
    open(os.path.join(path, "tarkistaUtils.py"), "w").write(utils)

    reportPath = os.path.join(path, "report.txt")
    orginal = sys.stdout
    sys.stdout = open(reportPath, "w")

    doctest.master = None
    result = doctest.testfile("tests.txt")
    sys.stdout.close()
    sys.stdout = orginal

    failed, total = result
    info("Result %d of %d tests succeeded" % (total-failed, total))

    report = open(reportPath).read()
    report = "#FORMAT plain\n" + report

    mc = xmlrpclib.MultiCall(wiki)
    mc.applyAuthToken(authToken)

    metas = dict()
    metas["overallvalue"] = ["%d/%d" % (total-failed, total)]
    mc.SetMeta(picked[0], metas, "repl", True)
    mc.putPage(picked[0] + "/comment", report)

    try:
        results = [r for r in mc()]
    except xmlrpclib.Fault, fault:
        if fault.faultString.find("You did not change") == -1:
            sys.exit(str(fault))

    for result in results:
        if result == "SUCCESS":
            continue

        info(repr(result))

    info("Removing tempdir %s" % path)
    os.chdir(cwd)
    shutil.rmtree(path)

    time.sleep(1)
