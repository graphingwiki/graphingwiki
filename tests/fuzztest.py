# -*- coding: utf-8 -*-
"""
    Tests for Graphingwiki

    @copyright: 2008 by Pauli rikula <prikula@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""


import unittest
import re
from xmlrpclib import ServerProxy, Error
import traceback

"""xmlrpc timeout, call of dev-install.sh"""
import signal
import subprocess 
import datetime

"""call of dev-install.sh"""
import os
import socket
import time
import re


from testdecorator import ExecPntr
# Server URL
serverAddr = "http://localhost:8080/?action=xmlrpc2"

# xmlrpc timeouts
putPageTimeout = 10*60#10 * 60
getPageHTMLTimeout = 10*60#10 * 60
deletePageTimeout = 10*60#10 * 60

#wiki install setup
wikiInstallTries = 30
wikiInitWait = 10

p = ExecPntr()

class CustomException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Timeout(CustomException):
    pass

class TestFail(CustomException):
    pass



@p.executionDecorator()
def xmlrpcWithSimpleTimeout( timeOut, description, function, *parameters):
    """
    Tests wiki over xmlrpc with timeout using some method of xmlrpc srverProxy.
    """
    def customHandler(signum, frame):
        raise Timeout, str(description)    
    out = None
    signal.signal(signal.SIGALRM, customHandler)
    signal.alarm(timeOut)
    try:
        out = function(*parameters)
    except Exception, e:
        signal.alarm(0)
        raise TestFail, e
    signal.alarm(0)
    return out



@p.executionDecorator()
def testPutGetHTMLDeletePage(server, pageName, pageString):
    xmlrpcWithSimpleTimeout(putPageTimeout, "putPage", server.putPage, pageName, pageString)
    out = xmlrpcWithSimpleTimeout(getPageHTMLTimeout, "getPageHTML", server.getPageHTML, pageName)
    xmlrpcWithSimpleTimeout(deletePageTimeout, "deletePage", server.DeletePage, pageName, "test page")


@p.executionDecorator("CategoryInitialization", metadatax = "sdfasdfa" )
def uglyKill():
    """kills every running moinmoin or dev-install.sh proceses 
    that has the same group id as main process"""
    ownid = os.getpid()
    owngid = os.getpgid(ownid)
    s = subprocess.Popen(["ps", "-ax"], stdout=subprocess.PIPE).communicate()[0]
    eka = True
    ind = 0
    for i in s.split("\n"):
        j = i.strip()
        j = re.split("\s+", j)
        if i.find("./dev-install.sh") != -1 or i.find("Python moin.py") != -1:
            pid = int(j[ind])
            gid = os.getpgid(pid)
            #print "killed", j, "pid", pid, "gids", owngid, gid
            if gid == owngid:
                try:
                    os.kill(pid, signal.SIGQUIT)
                except:
                    pass
            

@p.executionDecorator()
def testPages(pageNames, pageList, serverAddr):
    """pageset Put-, GetHTML-, delete-test"""
    uglyKill()
    popenObj  = subprocess.Popen("./dev-install.sh", shell=True)
    try:
        server = None
        wikiReady = False
        
        for i in range(wikiInstallTries):
            print "-"*60 
            server = ServerProxy(serverAddr)
            print "poll:", popenObj.poll()
            print "server", server
            time.sleep(wikiInitWait)
            try:
                testPutGetHTMLDeletePage(server, "InitializePage", "asdfasdf")
            except TestFail:
                continue
            wikiReady = True
            break
            
        if not wikiReady:
            uglyKill()  
            raise Timeout, "wikiInstallTries over %d"%wikiInstallTries
        
        for i, name in enumerate(pageNames):
            testPutGetHTMLDeletePage(server, name, pageList[i])
    except:
        print traceback.format_exc()
    del server

    uglyKill()




if __name__ == "__main__":
    print testPages(["basic", "asdfasdf", "123","should fail" ],[u"""#format plain
""" + u"a"*10,"asdfasdf","123", """<<RaiseException('f','o','o bar')>>"""],serverAddr)

    print p


