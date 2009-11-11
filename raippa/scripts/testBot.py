# -*- coding: utf-8 -*-
"""
    @copyright: 2008 by Mika Seppänen, Rauli Puuperä, Erno Kuusela
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import socket
import os
import sys
import datetime
import subprocess
import xmlrpclib
import re
import shutil
import tempfile
import time
import traceback

from optparse import OptionParser

from opencollab.wiki import CLIWiki
import opencollab.wiki

orig_feed = xmlrpclib.ExpatParser.feed

def monkey_feed(self, data):
    return orig_feed(self, re.sub(ur'[\x00-\x08\x0b-\x19]', '?', data))
xmlrpclib.ExpatParser.feed = monkey_feed

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
    #signal.signal(signal.SIGALRM, handler)
    p = subprocess.Popen(["python", myFile] + parameters, shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE, stdin = subprocess.PIPE)
    #signal.alarm(30)
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

    #signal.alarm(0)

    if printReturnValue:
        return result + (p.returncode,) 

    return result

def writefile(fName, fCont): f = open(fName,"w"); f.write(fCont); f.close()
"""

run = """import os
import sys
import doctest
import signal
import os

class Timeout(Exception):
    pass

def handler(signum, frame):
    os.system("touch handler-called")
    raise Timeout  

signal.signal(signal.SIGALRM, handler)

signal.alarm(20)

sys.path.append(os.getcwd())

result = doctest.testfile("tests.txt")

signal.alarm(0)

sys.stderr.write(repr(result) + "\\n")
"""

def error(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [error] %s" % (date, msg)

def info(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [info] %s" % (date, msg)

def removeLink(line):
    if line.startswith('[['):
        return line[13:-2]
    return line

def parseTests(content):
    #Match the stuff between {{{ and }}} the docttest should be there
    test_regex = re.compile('{{{\s*(.*)\s*}}}', re.DOTALL)
    return test_regex.search(content).groups()[0]

def run_runpy(tempdir, timeout=10):
    ofn = os.path.join(tempdir, "out.txt")
    efn = os.path.join(tempdir, "err.txt")
    of = open(ofn, "w")
    ef = open(efn, "w")
    p = subprocess.Popen(["python", "run.py"], shell=False, stdout=of, stderr=ef, stdin=open("/dev/null"))
    timedout=1
    for i in range(10):
        if p.poll() is not None:
            timedout=0
            break
        time.sleep(1)
    of.close()
    ef.close()
    if timedout:
        os.kill(p.pid, 9)
    return open(ofn).read(), open(efn).read(), timedout


def checkAnswer(code, tests):
    #This is mostly legacy stuff from previous version. I'm not 100%
    #sure what it does :)

    path = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(path)
    info("Created tempdir %s" % path)

    open(os.path.join(path, "tests.txt"), "w").write(tests)
    open(os.path.join(path, "tarkistaUtils.py"), "w").write(utils)
    open(os.path.join(path, "run.py"), "w").write(run)

    open(os.path.join(path, "ratkaisu.py"), "w").write("pass\n")

    stdout, stderr, timedout = run_runpy(path)
    compiled = os.path.join(path, "ratkaisu.pyc")
    if os.path.exists(compiled):
        os.remove(compiled)

    try:
        failed, total = map(lambda x: int(x), stderr.strip().strip("()").split(", "))
    except ValueError:
        failed = total = trivialTests = 0
    else:
        trivialTests = total - failed
    info("Found %d trivial tests" % (trivialTests))

    open(os.path.join(path, "ratkaisu.py"), "w").write(code)

    stdout, stderr, timedout = run_runpy(path)

    info("Removing tempdir %s" % path)
    os.chdir(cwd)
    shutil.rmtree(path)

    try:
        failed, total = map(lambda x: int(x), stderr.strip().strip("()").split(", "))
    except ValueError:
        failed = total
        succeeded = 0

    succeeded = total - failed
    succeeded = max(succeeded - trivialTests, 0)
    total = total - trivialTests

    if not stdout:
        stdout = 'Timeout! Your program propably was stucked in an infinete loop.\n'

    return succeeded, total, stdout, stderr

def checking_loop(wiki):
    url = wiki.host

    while True:
        #Get all new history pages with pending status
        info('Lookig for pages')
        picked_pages = wiki.getMeta('CategoryHistory, overallvalue=pending')
        info('Found %d pages' % len(picked_pages))

        if not picked_pages:
            info('No pages. Sleeping')
            time.sleep(10)
            continue
        
        #go thgrough all new pages
        for page in picked_pages:
            info('%s: picked %s' % (url, page))

            #change the status to picked
            wiki.setMeta(page, {'overallvalue' : ['picked']}, True)

            metas = picked_pages[page]
            
            # get the attachment filename from the file meta
            attachment_file = metas['file'].single()
            attachment_file = removeLink(attachment_file)
            #get the source code
            info("Fetching sourcode from %s" % attachment_file)
            try:
                code = wiki.getAttachment(page, attachment_file)
            except opencollab.wiki.WikiFault, e:
                if 'There was an error in the wiki side (Nonexisting attachment' in e.args[0]:
                    code = ''
                else:
                    raise

            #if there is wrong amount of question page linksd, leave
            #the returned assignment as picked so that other
            #assignments can be checked. 

            if len(metas['question']) != 1:
                error('Invalid meta data in %s! There were %d values!\n' 
                      % (page, len(metas['question'])))
                continue
            
            #get the question pagenmae
            question = metas['question'].single(None)
            question = question.strip('[]')

            #find associataed answerpages
            answer_meta = wiki.getMeta('CategoryAnswer, question=%s' 
                                       % question)

            #Get the page name
            answer_page = answer_meta.keys()[0]
            info('Getting answer from %s' % answer_page)

            #get the tests
            tests = parseTests(wiki.getPage(answer_page))
            
            succeeded, total, stdout, stderr = checkAnswer(code, tests)
            info("Result %d of %d tests succeeded" % (succeeded, total))

            report = stdout.replace("\\n", "\n")
            report = '''{{{
        %s
        }}}''' % report
            
            metas = dict()
            
            if succeeded == total or succeeded > 0:
                metas['overallvalue'] = ['success']
            else:
                metas['overallvalue'] = ['failed']

            #wrong = amount of failed tests, right = succeeded tests
            metas['wrong'] = [str(total - succeeded)]
            metas['right'] = [str(succeeded)]
                    
            metas["comment"] = ["[[%s]]" % (page + "/comment")]

            #add metas
            wiki.setMeta(page, metas, True)
            
            # "add" the page to comment category. This is propably
            # silly maybe this should be done using setMeta
            report = report + '\n----\nCategoryBotComment'

            # Put the comment page
            try:
                wiki.putPage(page + "/comment", report)
            except opencollab.wiki.WikiFault, error_message:
                # It's ok if the comment does not change
                if 'There was an error in the wiki side (You did not change the page content, not saved!)' in error_message:
                    pass
                else:
                    raise
            info('Done')
            time.sleep(5)

def main():

    parser = OptionParser()
    parser.add_option("-u", "--url-to-wiki", dest="url",
                      help="connect to URL", metavar="URL", default = None)
    parser.add_option("-f", "--config-file", dest="file",
                      help="read credentials from FILE", metavar="FILE")

    (options, args) = parser.parse_args()
    
    if args:
        sys.stderr.write('Invalid arguments! Use -h for help\n')
        sys.exit(1)

    if not options.url:
        sys.stderr.write('You must specify a wiki to connect!\n')
        sys.exit(1)
    url = options.url

    if not options.file:
        try:
            wiki = CLIWiki(options.url)
        except socket.error, e:
            sys.stderr.write(e + '\n')
            sys.exit(1)
       
        success = wiki.authenticate()

    else:
        while True:
            try:
                wiki = CLIWiki(options.url, config = options.file)
            except socket.error, e:
                error(e)
                time.sleep(10)
            else:
                break
                
    if not wiki.token:
        sys.stderr.write('Auhtentication failure\n')
        sys.exit(1)

    while True:
        try:
            checking_loop(wiki)
        except opencollab.wiki.WikiFailure:
            error('WIKI PROBLEMS')
            traceback.print_exc()
        except socket.error:
            error('CONNECTION PROBLEMS')
            traceback.print_exc()
        #except KeyboardInterrupt:
        #    raise
        #    sys.exit(0)
        time.sleep(10)
        

if __name__ == '__main__':
    main()
