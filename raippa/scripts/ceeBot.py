import os, sys, time, datetime, subprocess, tempfile, shutil, xml

from optparse import OptionParser

from opencollab.wiki import CLIWiki
import opencollab.wiki

class testCase(object):
    def __init__(self):
        self.cmdline = str()
        self.inputs = list()
        self.outputs = list()
        self.infiles = dict()
        self.outfiles = dict()
        self.switches = str()

    def __repr__(self):
        value = str()
        value += '%s ' % str(self.cmdline) 
        value += '%s ' % str(self.inputs) 
        value += '%s ' % str(self.outputs) 
        value += '%s ' % str(self.infiles) 
        value += '%s ' % str(self.outfiles) 
        return value

def runtests(tests, scriptpath):
    success, total = 0, 0
    report = str()
    for test in tests:
        if test.infiles:
            for infile in test.infiles:
                open(infile, 'w').write(test.infiles[infile])
                                             
        if test.outfiles:
            for outfile in test.outfiles:
                open('_'+outfile, 'w').write(test.outfiles[outfile])
                
        open('test.txt', 'w').writelines([x+'\n' for x in test.outputs])
        if test.inputs:
            open('output.txt', 'w').writelines([x + '\n' for x in test.inputs])
            output = 'output.txt'
        else:
            output = '/dev/null'


        command = os.path.join(scriptpath, 'ctest.bash -p "./program %s" -i %s -o test.txt' % (test.cmdline, output))

        if test.outfiles:
            command = command + ' ' + ' '.join(['-f _%s %s' % (x, x) for x in test.outfiles.keys()])
            command =  command.replace('test.txt', '/dev/null')

        ctestprocess = subprocess.Popen(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        report += ctestprocess.stdout.read()
        ctestprocess.wait()
        if ctestprocess.returncode == 0:
            success +=1
        total += 1
        if test.infiles:
            for infile in test.infiles:
                os.remove(infile)
                                             
        if test.outfiles:
            for outfile in test.outfiles:
                os.remove('_'+outfile)
                
    return success, total, report


def info(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [i] %s" % (date, msg)

def parsecontent(content):
    testcases = list()
    case = None
    for line in content.split('\n'):
        if line.startswith('#'):
            pass
        elif line.startswith('./program'):
            if case:
                testcases.append(case)
            case = testCase()
            _, switches = line.split('./program')
            case.cmdline = switches
        elif line.startswith(':'):
            _, filename = line.split(':')
            case.infiles[filename] = str() 
        elif line.startswith('>'):
            case.infiles[filename] += line[1:] + '\n'
        elif line.startswith('|'):
            _, filename = line.split('|')
            case.outfiles[filename] = str() 
        elif line.startswith('<'):
            case.outfiles[filename] += line[1:] + '\n'
        else:
            case.outputs.append(line)
    testcases.append(case)
    
    return "-lm", testcases

def compile(code, switches):

    path = tempfile.mkdtemp()
    os.chdir(path)
    
    open('file.c', 'w').write(code.encode('utf-8'))

    executablePath = os.path.join(path, "program")

    process = subprocess.Popen('gcc -Wall %s file.c -o program' % switches, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)

    report = process.stdout.read()
    process.wait()

    if process.returncode != 0:
        return path, False, report

    return path, True, report

def main():
    parser = OptionParser()
    parser.add_option("-u", "--url-to-wiki", dest="url",
                      help="connect to URL", metavar="URL", default = None)
    parser.add_option("-c", "--course", dest="course",
                      help="look for answers in course COURSE", metavar="COURSE", default = None)
    parser.add_option("-f", "--config-file", dest="file",
                      help="read credentials from FILE", metavar="FILE")

    (options, args) = parser.parse_args()
    
    if args:
        sys.stderr.write('NO!\n')
        sys.exit(1)

    if not options.url:
        sys.stderr.write('You must specify a wiki to connect!\n')
        sys.exit(1)
    url = options.url

    if not options.course:
        sys.stderr.write('Please select a course!\n')
        sys.exit(1)
    course = options.course

    if not options.file:
        wiki = CLIWiki(options.url)
        wiki.authenticate()
    else:
        wiki = CLIWiki(options.url, config = options.file)


    scriptpath = os.getcwd()
    while True:
        
        pages = wiki.getMeta('CategoryHistory, overallvalue=pending, course=%s' % course)

        info('found %d pages' % (len(pages)))
        for page in pages:
            info('%s: picked %s' % (url, page))
            wiki.setMeta(page, {'overallvalue' : ['picked']}, True)
            metas = pages[page]
            question = metas['question'].single(None)
            if not question:
                sys.stderr.write('no question page!\n')
                sys.exit(1)
            question = question.strip('[]')
            try:
                sourcecode = wiki.getPage(page + '/file')
            except xml.parsers.expat.ExpatError:
                sourcecode = "DO NOT RETURN SILLY FILES!"
            sourcecode = '\n'.join(sourcecode.split('\n')[1:])
            answers = wiki.getMeta('CategoryAnswer, question=%s' % question)

            if not answers:
                sys.stderr.write('no aswers!\n')
                sys.exit(1)
            answer = answers[answers.keys()[0]]['true'].single(None).strip('[]')
            info('Fetcing tests from %s' % answer)
            content = wiki.getPage(answer)
            switches, tests = parsecontent(content)

            path, success, report = compile(sourcecode, switches)
            
            if not success:
                info('Compilation FAILED')
                try:
                    wiki.putPage(page + '/comment', '{{{\nCOMPLIATION FAILED:\n' + report + '\n}}}')
                except opencollab.wiki.WikiFault:
                    info('no change')
                wiki.setMeta(page, {'overallvalue' : ['False'],
                                    'comment': ['[[%s/comment]]' % page]}, True)
                shutil.rmtree(path)
                continue

            info('Compilation SUCCESS')
            report = "{{{\nCOMPILATION WAS SUCCESSFUL:\n" + report
            report += '----\n'
            
            success, total, testreport = runtests(tests, scriptpath)
            info('score: %d/%d' % (success, total))
            report += testreport
            report += '}}}'
            try:
                wiki.putPage(page + '/comment', report)
            except opencollab.wiki.WikiFault, e:
                print e
                try:
                    wiki.putPage(page + '/comment', 'Your program failed. Your program propably printed something silly. Unfortunately we cannot show what your program printed.')
                except opencollab.wiki.WikiFault, e:
                    print e
                
            wiki.setMeta(page, {'overallvalue' : ['%d/%d' % (success, total)],
                                'comment': ['[[%s/comment]]' % page]}, True)
            info('done')
            shutil.rmtree(path)
        time.sleep(10.0)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write('Kekkis\n')
        sys.exit(1)
