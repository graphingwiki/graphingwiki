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

import opencollab.wiki
import opencollab.util

#rmlrpc is broken. this monkey patch should fix it
orig_feed = xmlrpclib.ExpatParser.feed

def monkey_feed(self, data):
    return orig_feed(self, re.sub(ur'[\x00-\x08\x0b-\x19]', '?', data))
xmlrpclib.ExpatParser.feed = monkey_feed

def error(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [error] %s" % (date, msg)

def info(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [info] %s" % (date, msg)

def removeLink(line):
    #For old fashined history pages. Previously the file wasnot a
    #link but now it is. This can removed in the next iteration
    if line.startswith('[['): return line[13:-2]
    return line

def run_runpy(tempdir, timeout=10):
    #open files for stdout and stderr
    outpath = os.path.join(tempdir, "out.txt")
    errpath = os.path.join(tempdir, "err.txt")
    outfile = open(outpath, "w")
    errfile = open(errpath, "w")

    p = subprocess.Popen(["python", "run.py"], shell=False, stdout=outfile, stderr=errfile, stdin=open("/dev/null"))
 
   timedout = 1

    for i in range(timeout):
        if p.poll() is not None:
            timedout=0
            break
        time.sleep(1)

    outfile.close()
    errfile.close()

    if timedout:
        os.kill(p.pid, 9)

    return open(outfile).read(), open(errfile).read(), timedout

def readConfig(file):
    opts = opencollab.util.parseConfig(file)
    return opts


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

            path = tempfile.mkdtemp()
	    cwd = os.getcwd()
	    os.chdir(path)
	    
            info("Created tempdir %s" % path)

            #change the status to picked
            wiki.setMeta(page, {'overallvalue' : ['picked']}, True)

            metas = picked_pages[page]

            # get the attachment filename from the file meta
            info('Writing files')
            for filename in rmetas['file']:
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

                open(filename, 'w').write(code)


            #if there is wrong amount of question page linksd, leave
            #the returned assignment as picked so that other
            #assignments can be checked. 

            if len(metas['question']) != 1:
                error('Invalid meta data in %s! There we %d values!\n' 
                      % (page, len(metas['question'])))
                continue
            
            #get the question pagenmae
            question = metas['question'].single(None)
            question = question.strip('[]')
            
            #find associataed answerpages
            
            answer_metas = wiki.getMeta(question +'/options').values()
            
            for _, link in [x, y.single() for x, y in answer_metas.items() if x‘ == 'answer'] 
            #Get the page name
            answer_page = answer_meta.keys()
            info('Getting answer from %s' % answer_page)

            
            
            stdout, stderr = checkAnswer(code, tests)
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
    #parse commandline parameters
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
                wiki = GraphingWiki(options.url)
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
        time.sleep(10)
        

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print 'Bye!'
    
