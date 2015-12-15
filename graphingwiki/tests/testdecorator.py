# -*- coding: utf-8 -*-
import traceback
import sys
from copy import copy


"""
            a tool for easier test-documentation
        
            @copyright: 2008 by Pauli Rikula <prikula@ee.oulu.fi>
            @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

#TODO: trace exceptionin yhteyteen
#TODO: se wikitulostus...

def tryStr(s):
    out = ""
    try:
        out += str(s)
       
    except:
        try:
            outL = []
            for i in s:
                print "i", i
                outL.append(tryStr(i))
            out += str(outL)
        except Exception, e:
            out += str(e)
    return out

class FncInfo:
    def __init__(self, fnc=None, fId=0, longName=None, categories=None, metadatas=None ):
        self.fnc = fnc
        self.fId = fId
        self.longName = longName
        self.categories = categories
        self.metadatas = metadatas
        self.docStr = fnc.__doc__
    
    
    def __str__(self):
        return tryStr(self.__dict__)
    
    
    #def setId(self,fId):
    #    self.fId = fId
        
    

class ExecutionTree:
    def __init__(self, fncInfo=None, executionId=0, stackPoint = 0, params=None):
        """
           fcn : pointer to executed function. takes the name of the function using this.
             TODO: might need a fix, because does not work with the rest of th program if
                   fcn.__name__ is set to something during the execution of the program 
           fId : the tuple (fcn.__name__, fId) is an unique function identifier.
                 if fId != 0 there is exsist another function or method which name is fcn.__name__  
           params: a tuple (args, kw), where args is the parameters without key and kw is a dictionary of parameters with a key
        """
        
        self.fncInfo = fncInfo
        self.params = tryStr(params)

        self.excdesc = None
        self.executionSummary = None
        self.exception = None
        self.returnValues = None
        
        self.executionId = executionId
        self.stackPoint = stackPoint
    
    def add(self, a):
        if self.executionSummary == None:
            self.executionSummary = [ ]
        self.executionSummary.append(a)

    def yieldChilds(self):
        yield self
        if self.executionSummary != None:
            for i in self.executionSummary:
                for j in i.yieldChilds():
                    yield j
                
    
    def __str__(self):
        out = """
 * %s : %s --> (exception: %s, returnvalues %s)
"""%(self.fncInfo,
     str(self.params),
     str((type(self.exception), str(self.exception), str(self.excdesc) )),
     str(self.returnValues)
     )
        if self.executionSummary != None:
            for i in self.executionSummary:
                out += str(i).replace("""
""", """
  """)
        return out
    
    def setException(self, e, excdesc ):
        self.exception = e
        self.excdesc = excdesc 

    def setReturnValues(self, returnValues):
        self.returnValues = str(returnValues)

    
    
    
class ExecPntr:
    def __init__(self, root = None, ExecutionTree = ExecutionTree):
        
        self.ExecutionTree = ExecutionTree
        if root == None:
            root = self.ExecutionTree()
        self.initValues(root)
        
        self.removedStack = []
        
        @self.executionDecorator()
        def NULLFUNC():
            return
        
        del NULLFUNC
        
        print "NULLSTACK", self.removedStack
        self.initValues(root)

    def initValues(self, root):
        self.pntr = root
        self.root = root
        self.stack = []
        self.fncInfos = {}
        self.nextExecutionId = 1
        
    def getFncId(self, fnc):
        nId = self.fncInfos.get(fnc, None)
        return nId
    
    def noteFcnInfo(self,fnc=None,longName=None, categories=None, metadatas=None ):
        info =  self.fncInfos.get(fnc, None)
        if info == None:
            fId =  len(self.fncInfos) +1
            info = FncInfo( fnc=fnc, fId = fId, longName=longName, categories=categories, metadatas=metadatas)
            self.fncInfos[fnc] = info
        return info
    
    def getStack(self):
        offset = -1
        myStack = traceback.extract_stack()
        returned = []
        for i in range(len(myStack)):
            j = myStack[offset - i][:3]
            if j not in self.removedStack:
                returned.append(j)    
            if myStack[offset -i][2] == '<module>':
                break
        returned.reverse()
        if len(self.removedStack) == 0:
            self.removedStack = copy(returned)
        return returned    
    
    def branch(self, fncInfo, args, kw):
        executionId = self.nextExecutionId
        self.nextExecutionId += 1
        newtree = self.ExecutionTree(fncInfo = fncInfo, executionId = executionId, params = (args, kw), stackPoint = len(self.stack) +1)
        self.pntr.add(newtree)
        self.stack.append(self.pntr)
        self.pntr = newtree
    
    def goBack(self, exp =None, returnValues = None, excdesc = None):
        if exp != None:
            self.pntr.setException(exp, excdesc)
        self.pntr.setReturnValues(returnValues)
        self.pntr = self.stack.pop()
    
    def executionDecorator(self, *categories, **metadatas):
        def ExecutionTreeLog(fnc):
            lname = str(self.getStack())[1:-1]
            fncInfo = self.noteFcnInfo(fnc=fnc, longName=lname, categories=categories, metadatas=metadatas)
            def decorator(*args, **kw):                
                log = self
                log.branch(fncInfo, args,kw)
                try:
                    returnValues = fnc(*args,**kw)
                except Exception, e:
                    log.goBack(exp = e, excdesc = traceback.format_exc())
                    raise
                log.goBack(returnValues = returnValues)
                return returnValues
            
            return decorator
        return ExecutionTreeLog
    
    def __str__(self):
        restOut = ""
        for i in self.fncInfos.values():
            restOut += """
%s"""%(i)
        return """
Traceback:

"""+str(self.root) + """


categories and datas:

%s
"""%restOut





if __name__ == "__main__":
    p = ExecPntr()
    
    @p.executionDecorator()
    def hello(a,b, c = "foo",d = "bar"):
        """
        docdocdoc
        """
        print "Hello, world!", a, b
        return a,b,c,d
    
    
    
    
    @p.executionDecorator("terve", type = "foobar", date=1234, sfas="fsf")
    def hello2(a,b, c = "foo",d = "bar"):
        """docdocdoc"""
        print "Hello, world!", a, b
        hello(1,2)
        hello(2,2)
    
    
    
    
    class FooCalss:
        @p.executionDecorator("testi")
        def __init__(self, foobar = 444):
            self.kkk = foobar
        @p.executionDecorator("testi")
        def fooFcn(self,kekkis):
            @p.executionDecorator("testi")
            def foofoo():
                return
            return
    
    
    @p.executionDecorator()
    def double():
        pass
    
    
    
    @p.executionDecorator()
    def double():
        print "."
        pass
    
    
    @p.executionDecorator("exception...")
    def exc():
        raise ValueError
    
    

    @p.executionDecorator("exception catch")
    def tryExc():
        try:
            exc()
        except ValueError:
            pass

    
    
    c = FooCalss()
    c.fooFcn(1)
    
    hello2(1, 2, c = 0, d = 1)#, treeLogPntr = p)

    tryExc()

    double()

    print "-" * 80
    
    print p


