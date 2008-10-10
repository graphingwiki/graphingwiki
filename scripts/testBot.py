# -*- coding: utf-8 -*-
"""
    @copyright: 2008 by Mika Seppänen 
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import os
import sys
import xmlrpclib
import doctest

import shutil
import tempfile
import time

utils = """# -*- coding: utf-8 -*-
import subprocess
import errno
import signal
import os

class Timeout(Exception):
    pass

def handler(signum, frame):
    raise Timeout

def runProgram(myInput="", myFile='ratkaisu.py', printReturnValue = False, parameters = []):
    signal.signal(signal.SIGALRM, handler)
    p = subprocess.Popen(["python", myFile] + parameters, shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin = subprocess.PIPE)
    signal.alarm(30)
    try:
        result = p.communicate(myInput)
    except Timeout:
        result = ("Timeout!", "Timeout!")
        os.kill(p.pid, signal.SIGKILL)
    except OSError, e:
        if e.errno == errno.EPIPE:
            result = (p.stdout.read(), p.stderr.read())
        else:
            raise

    signal.alarm(0)

    if printReturnValue:
        return result + (p.returncode,) 

    return result

def writefile(fName, fCont): f = open(fName,"w"); f.write(fCont); f.close()
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

class GraphingWiki(object):
    def __init__(self, url, user, password):
        self.credentials = (user, password)
        self.authToken = ""
        self.proxy = xmlrpclib.ServerProxy(url + "?action=xmlrpc2")
        self.doAuth()

    def doAuth(self):
        self.authToken = self.proxy.getAuthToken(*self.credentials)

    def request(self, retryCount, name, *args):
        if retryCount <= 0:
            return

        mc = xmlrpclib.MultiCall(self.proxy)
        mc.applyAuthToken(self.authToken)
        getattr(mc, name)(*args)

        results = iter(mc())

        try:
            results.next()
        except xmlrpclib.Fault, fault:
            if "Expired token." in fault.faultString:
                self.doAuth()
                return self.request(retryCount - 1, name, *args)

        return results.next()

def pickHistoryPage(wiki, course):
    result = wiki.request(3, "GetMeta", "CategoryHistory, overallvalue=pending, course=%s" % course, False)

    header = result[0]
    pages = result[1:]
    info("Found %d history pages waiting for checking" % len(pages))

    for page in pages:
        pagename = page[0]
        metaList = page[1:]
        metas = dict()

        for key, values in zip(header, metaList):
            metas[key] = values

        return (pagename, metas)

    return None 

password = open("password").read().strip()
course = "Course/521141P_Autumn2008"

wiki = GraphingWiki("http://www.raippa.fi/", "bot", password)

while True:
    picked = pickHistoryPage(wiki, course)

    if picked is None:
        time.sleep(10)
        continue

    info("Picked %s." % picked[0])

    metas = dict()
    metas["overallvalue"] = ["picked"]

    try:
        wiki.request(3, "SetMeta", picked[0], metas, "repl", True)
    except xmlrpclib.Fault, fault:
        if "You did not change" in fault.faultString:
            sys.exit(str(fault))
   
    metas = picked[1]

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
    solution = stripFormat(wiki.request(3, "getPage", file))

    info("Fetching right answer from %s" % question)
    result = wiki.request(3, "GetMeta", "CategoryAnswer, question=%s" % question, False)

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
    tests = stripFormat(wiki.request(3, "getPage", tests))

    path = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(path)
    sys.path.append(path)
    info("Created tempdir %s" % path)

    open(os.path.join(path, "tests.txt"), "w").write(tests)
    open(os.path.join(path, "tarkistaUtils.py"), "w").write(utils)


    open(os.path.join(path, "ratkaisu.py"), "w").write("pass\n")

    reportPath = os.path.join(path, "reportTrivial.txt")
    orginal = sys.stdout
    sys.stdout = open(reportPath, "w")

    doctest.master = None
    result = doctest.testfile("tests.txt")
    sys.stdout.close()
    sys.stdout = orginal

    failed, total = result
    trivialTests = total - failed
    info("Found %d trivial tests" % (trivialTests))


    open(os.path.join(path, "ratkaisu.py"), "w").write(solution)

    reportPath = os.path.join(path, "report.txt")
    orginal = sys.stdout
    sys.stdout = open(reportPath, "w")

    doctest.master = None
    result = doctest.testfile("tests.txt")
    sys.stdout.close()
    sys.stdout = orginal

    failed, total = result
    succeeded = total - failed
    succeeded = max(succeeded - trivialTests, 0)
    total = total - trivialTests

    info("Result %d of %d tests succeeded" % (succeeded, total))

    report = open(reportPath).read()
    report = report.replace("\\n", "\n")
    report = "#FORMAT plain\n" + report

    metas = dict()
    metas["overallvalue"] = ["%d/%d" % (succeeded, total)]

    try:
        wiki.request(3, "SetMeta", picked[0], metas, "repl", True)
        wiki.request(3, "putPage", picked[0] + "/comment", report)
    except xmlrpclib.Fault, fault:
        if "You did not change" in fault.faultString:
            pass

    info("Removing tempdir %s" % path)
    os.chdir(cwd)
    shutil.rmtree(path)

    time.sleep(1)
