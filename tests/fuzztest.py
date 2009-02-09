# -*- coding: utf-8 -*-
"""
    Tests for Graphingwiki

    @copyright: 2008 by Pauli rikula <prikula@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

#python sys.settrace 

#pprint objektien tulostusta nätisti


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


import getpass
from wiki import GraphingWiki, AuthorizationRequired
from meta import Meta, Integer


"""for test documentation"""
from testdecorator import ExecPntr, ExecutionTree

#TODO: fix the format string
class WExecutionTree(ExecutionTree):
    def toPage(self, connection, sessionName):
        childs = ""
        if self.executionSummary != None:
            for i in self.executionSummary:
                childs += """
  step:: [[%s]]
"""%("%s/step_%05d"%(sessionName, i.executionId))
        
        fId = 0
        if self.fncInfo != None:
            fId = self.fncInfo.fId
        
        fnc = """
  function:: [[%s/fnc_%05d]]
"""%(sessionName,fId)
        
        stcpnt = """
  stackpoint:: %d
"""%self.stackPoint
        
        categories = """
CategoryExecutionStep
Category%s
"""%sessionName
        try:
            connection.putPage("%s/step_%05d"%(sessionName, self.executionId), fnc + stcpnt + childs + categories)
        except Exception, e:
            print e
    

class WExecPntr(ExecPntr):
    def __init__(self, url, sessionId = 0):
        self.url = url
        ExecPntr.__init__(self, ExecutionTree = WExecutionTree)
        self.connection = None
        self.sessionId = sessionId
        

    def connect(self):
        self.connection = CLIWiki(self.url)
        try:
            self.connection.putPage( "page_front_page",u"""
= Test =

[[ExecutionTrace]]

[[MethodDescriptions]]

""")
        except Exception, e:
            print e

    def putTrace(self):
        #    self.connection.putPage( "Session-%d/ExecutionTrace"%self.sessionId, unicode(str(self.root)) )
        for i in self.root.yieldChilds():
            i.toPage(self.connection, "Session_%d"%self.sessionId)
            #self.connection.putPage( "Session-%d/ExecutionTrace/step-%d"%(self.sessionId, i.executionId), str(i))
    
    def putFncInfos(self):     
        for i in self.fncInfos.itervalues():
            try:
                self.connection.putPage( "Session_%d/fnc_%05d"%(self.sessionId, i.fId), str(i) )
            except Exception, e:
                print e
    
p = WExecPntr("http://localhost:8081")



class CLIWiki(GraphingWiki):
    #@p.executionDecorator("CategoryResultWikiInitialization")
    def request(self, name, *args):
        while True:
            try:
                result = GraphingWiki.request(self, name, *args)
            except AuthorizationRequired:
                username = raw_input("Username:")
                password = getpass.getpass("Password:")

                self.setCredentials(username, password)
            else:
                return result
    
    #@p.executionDecorator("CategoryResultWikiInitialization")
    def putPage(self, *args, **kw):
        GraphingWiki.putPage(self,*args, **kw)



p.connect()

# Server URL
serverAddr = "http://localhost:8080/?action=xmlrpc2"


# xmlrpc timeouts
putPageTimeout = 10*60#10 * 60
getPageHTMLTimeout = 10*60#10 * 60
deletePageTimeout = 10*60#10 * 60

#wiki install setup
wikiInstallTries = 30
wikiInitWait = 10


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

    #wiki = CLIWiki(url)
    
    #sys.stdout.write("\rconnecting & precalculating chunks...")
    #sys.stdout.flush()

    print testPages(["basic", "asdfasdf", "123","should fail" ],[u"""#format plain
""" + u"a"*10,"asdfasdf","123", """<<RaiseException('f','o','o bar')>>"""],serverAddr)

    print p

    p.putTrace()
    p.putFncInfos()
