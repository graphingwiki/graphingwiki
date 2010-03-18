# -*- coding: utf-8 -*-
"""
    @copyright: 2008 by Mika Seppänen, Rauli Puuperä, Erno Kuusela
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

#TODO
# handle situations where there is no outputpage
# run programs without shell
# catch httplib.CannotSendRequest 
# stdout + stderr not the other way around

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
import ConfigParser
import string
import signal

from optparse import OptionParser

import opencollab.wiki
import opencollab.util

outputtemplate = '''
{{{
%s
}}}
----
 testname:: %s
 file::
----
CategoryTestOutput
'''

ok_chars = string.printable
# remove some printable characters that cause problems in xmlrpc
ok_chars = ok_chars.replace('\x0b', '').replace('\x0c', '')
def esc(in_s): 
    out_s = ''   
    for c in in_s:
        if c not in ok_chars:
            out_s += '\\x' + hex(ord(c)).zfill(4)
        else:
            out_s += c
    return out_s


#rmlrpc is broken. this monkey patch should fix it
orig_feed = xmlrpclib.ExpatParser.feed

def monkey_feed(self, data):
    return orig_feed(self, esc(data))
xmlrpclib.ExpatParser.feed = monkey_feed

def error(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [error] %s" % (date, msg)

def info(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [info] %s" % (date, msg)

def removeLink(line):
    if line.startswith('[['): return line[13:-2]
    return line

def run(arg, input, tempdir, timeout):

    #open files for stdout and stderr
    outpath = os.path.join(tempdir, '__out__')
    errpath = os.path.join(tempdir, '__err__')
    inpath = os.path.join(tempdir, '__in__')
    
    outfile = open(outpath, "w")
    errfile = open(errpath, "w")
    
    open(inpath, 'w').write(input)
    infile = open(inpath, 'r')
 
    p = subprocess.Popen('ulimit -f 50;' + arg, shell=True, stdout=outfile, stderr=errfile, stdin=infile)
    
    timedout = True
    for i in range(timeout):
        if p.poll() is not None:
            timedout = False
            break
        time.sleep(1)
        
    # if timeout then kill 
    if timedout:
        info('Timed out!')
        os.kill(p.pid, signal.SIGTERM)
        time.sleep(2)
        p.poll()
        try:
            os.kill(p.pid, signal.SIGKILL)
        except OSError:
            info('Killed by SIGTERM')
            pass
        else:
            info('Killed by SIGKILL')
        
    outfile.close()
    errfile.close()
    
    error = open(errpath).read()
    output = open(outpath).read()
    
    #clean files
    os.remove(outpath)
    os.remove(errpath)
    os.remove(inpath)

    return output, error, timedout
    
def run_test(codes, args, input, input_files, tempdir, timeout=10):

    for filename, content in input_files.items():
        info('Writing input file %s' % filename)
        open(os.path.join(tempdir, filename), 'w').write(content)

    for filename, content in codes.items():
        open(os.path.join(tempdir, filename), 'w').write(content)
      
    error = str()
    output = str()

    timedout = False
    for arg in args.split('&&'):
        run_output, run_error, run_timedout = run(arg, input, tempdir, timeout)
        error += run_error
        output += run_output
        timedout = timedout or run_timedout
    
    files = dict()
    
    for filename in os.listdir(tempdir):
        content = open(os.path.join(tempdir, filename)).read()
        if len(content) > 1024*100:
            content = '***** THIS FILE was over 100kB long *****\nThis test failed\n'
            info('file %s is too big' % filename)
        files[filename] = content

    #clean all files (input files, code files, and outputfiles)

    for filename in os.listdir(tempdir):
        os.remove(os.path.join(tempdir, filename))

    return output, error, timedout, files

def checking_loop(wiki):
    wikiname = wiki.host + ''.join(wiki.path.rsplit('?')[:-1])

    while True:
        #Get all new history pages with pending status
        info('Lookig for pages in %s' % wikiname)
        picked_pages = wiki.getMeta('CategoryHistory, overallvalue=pending')
        info('Found %d pages' % len(picked_pages))

        if not picked_pages:
            info('Sleeping')
            time.sleep(10)
            continue

        #go thgrough all new pages
        for page in picked_pages:
            info('%s: picked %s' % (wikiname, page))

            tempdir = tempfile.mkdtemp()
            info("Created tempdir %s" % tempdir)
            os.chdir(tempdir)


            #change the status to picked
            wiki.setMeta(page, {'overallvalue' : ['picked']}, True)

            metas = picked_pages[page]
            user = metas['user'].single().strip('[]')

            # get the attachment filename from the file meta
            info('Writing files')
 
            codes = dict()
            
            for filename in metas['file']:
                attachment_file = removeLink(filename)
                #get the source code
                info("Fetching sourcode from %s" % attachment_file)
                try:
                    code = wiki.getAttachment(page, attachment_file)
                except opencollab.wiki.WikiFault, e:
                    if 'There was an error in the wiki side (Nonexisting attachment' in e.args[0]:
                        code = ''
                    else:
                        raise
                # get rid of the _rev<number> in filenames
                codes[re.sub('(_rev\d+)', '', removeLink(filename))] = code

            revision = re.search('_rev(\d+)', removeLink(filename)).group(1)

            #if there is wrong amount of question page linksd, leave
            #the returned assignment as picked so that other
            #assignments can be checked. 

            if len(metas['question']) != 1:
                error('Invalid meta data in %s! There we %d values!\n' 
                      % (page, len(metas['question'])))
                continue
            
            #get the question pagenmae
            question = metas['question'].single(None)
            if not question:
                error('NO QUESTION PAGE IN HISTORY %s!' % page)
                continue
            
            question = question.strip('[]')
            
            #find associataed answerpages
           
            answer_pages = wiki.getMeta(question +'/options').values()[0]['answer']
            info("Found %d answer pages" % len(answer_pages))

            regex = re.compile('{{{\s*(.*)\s?}}}', re.DOTALL)

            wrong = list()
            right = list()
            outputs = list()

            for answer_page in [x.strip('[]') for x in answer_pages]:
                info('getting answers from %s' % answer_page)
                answer_meta = wiki.getMeta(answer_page).values()[0]
                testname = answer_meta['testname'].single()
                
                outputpage = None
                inputpage = None

                if 'output' in answer_meta:
                    outputpage = answer_meta['output'].single().strip('[]')
                    outfilesatt = wiki.listAttachments

                if 'input' in answer_meta:
                    inputpage =  answer_meta['input'].single().strip('[]')

                try:
                    args = answer_meta['parameters'].single()
                except ValueError:
                    error('No params!')
                    continue

                input = ''
                
                input_files = dict()

                if inputpage:
                    content = wiki.getPage(inputpage)
                    input = regex.search(content).group(1)
                    input_meta = wiki.getMeta(inputpage)
                    filelist = input_meta[inputpage]['file']
                    for attachment in filelist:
                        filename = removeLink(attachment)
                        content = wiki.getAttachment(inputpage, filename)

                        input_files[filename] = content

                output = ''

                if outputpage:
                    content = wiki.getPage(outputpage)
                    output = regex.search(content).group(1)

                    output_meta = wiki.getMeta(outputpage)
                  
                    # get output files
                    output_files = dict()

                    filelist = output_meta[outputpage]['file']

                    for attachment in filelist:
                        filename = removeLink(attachment)
                        content = wiki.getAttachment(outputpage, filename)
                        output_files[filename] = content
                
                info('Running test')
                stu_output, stu_error, timeout, stu_files = run_test(codes, args, input, input_files, tempdir)


                #FIXME. Must check that editors in raippa do not add
                #newlines in output. If not. These lines can be removed
                stu_output = stu_output.lstrip('\n')
                output = output.lstrip('\n')

                stu_output = stu_error + stu_output

                if timeout:
                    stu_output = stu_output + "\n***** TIMEOUT *****\nYOUR PROGRAM TIMED OUT!\n\n"

                if len(stu_output) > 1024*100:
                    stu_output = "***** Your program produced more than 100kB of output data *****\n(Meaning that your program failed)\nPlease check your code before returning it\n" 
                    info('Excess output!')

                passed = True
                if stu_output != output:
                    passed = False 

                # compare output files
                for filename, content in output_files.items():
                    if filename not in stu_files:
                        info("%s is missing" % filename)
                        passed = False
                        break

                    if content != stu_files[filename]:
                        info("Output file does not match")
                        passed = False
                        break

                if passed:
                    info("Test %s succeeded" % testname)
                    right.append(testname)
                else:
                    info("Test %s failed" % testname)
                    wrong.append(testname)

                #put user output to wiki. 

                stu_outputpage = user + '/' + outputpage

                outputs.append('[[%s]]' % stu_outputpage)
                try:
                    wiki.putPage(stu_outputpage, outputtemplate % (esc(stu_output), testname))

                    #clean old attachments before adding new ones
                    for old_attachment in wiki.listAttachments(stu_outputpage):
                        wiki.deleteAttachment(stu_outputpage, old_attachment)

                    for ofilename, ocontent in stu_files.items():
                        wiki.putAttachment(stu_outputpage, ofilename, esc(ocontent), True)
                    
                except opencollab.wiki.WikiFault, error_message:
                    # It's ok if the comment does not change
                    if 'There was an error in the wiki side (You did not change the page content, not saved!)' in error_message:
                        pass
                    elif 'There was an error in the wiki side (Attachment not saved, file exists)' in error_message:
                        pass
                    else:
                        raise

                # put output file metas to output page

                wiki.setMeta(stu_outputpage, {'file' : ['[[attachment:%s]]' % esc(x) for x in stu_files.keys()]})


            info('Removing ' + tempdir)
            shutil.rmtree(tempdir)

            metas = dict()
            
            #clear old info
            info('Clearing old metas')
            wiki.setMeta(page, {'wrong': [], 'right': []}, True)

            if len(wrong) == 0:
                metas['overallvalue'] = ['success']
            else:
                metas['overallvalue'] = ['failure']

            if outputs:
                metas['output'] = outputs

            if wrong:
                metas['wrong'] = wrong

            if right:
                metas['right'] = right

            info('Setting new metas')
            #add metas
            wiki.setMeta(page, metas, True)
            
            info('Done')
            time.sleep(10)

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
            wiki = opencollab.wiki.CLIWiki(options.url)
        except socket.error, e:
            sys.stderr.write(e + '\n')
            sys.exit(1)

    else:
        config = ConfigParser.RawConfigParser()
        config.read(options.file)
        uname = config.get('creds', 'username')
        passwd = config.get('creds', 'password')
        while True:
            try:
                wiki = opencollab.wiki.CLIWiki(options.url, uname, passwd)
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
    
