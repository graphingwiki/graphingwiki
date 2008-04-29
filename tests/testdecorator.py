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



class ExecutionTree:
    def __init__(self, fcn,fId, params):
        """
           fcn : pointer to executed function. takes the name of the function using this.
             TODO: might need a fix, because does not work with the rest of th program if
                   fcn.__name__ is set to something during the execution of the program 
           fId : the tuple (fcn.__name__, fId) is an unique function identifier.
                 if fId != 0 there is exsist another function or method which name is fcn.__name__  
           params: a tuple (args, kw), where args is the parameters without key and kw is a dictionary of parameters with a key
        """
        
        self.fcn = fcn
        self.fId = fId
        self.params = tryStr(params)

        self.excdesc = None
        self.executionSummary = None
        self.exception = None
        self.returnValues = None

    
    def add(self, a):
        if self.executionSummary == None:
            self.executionSummary = []
        self.executionSummary.append(a)
    
    def __str__(self):
        name = "Root"
        longName = "Root"
        returnValues = []
        if self.fcn != None:
            name = self.fcn.__name__
        out = """
%s_%s:%s --> (exception: %s, returnvalues %s)
"""%(name, str(self.fId),
     str(self.params),
     str((type(self.exception), str(self.exception), str(self.excdesc) )),
     str(self.returnValues)
     )
        if self.executionSummary != None:
            for i in self.executionSummary:
                out += str(i).replace("""
""", """
|-""")
        return out
    
    def setException(self, e, excdesc ):
        self.exception = e
        self.excdesc = excdesc 

    def setReturnValues(self, returnValues):
        self.returnValues = str(returnValues)
    
    
class ExecPntr:
    def __init__(self, root = ExecutionTree(None,None,None)):
        #execution Pntr
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
        
        self.fcnDatas = {}
        
        self.nameIds = {}
    
    def noteNameId(self, n, longName):
        nameDict = self.nameIds.setdefault(n, {})
        nId = nameDict.setdefault(longName, len(nameDict))
        return nId
    
    def getStack(self):
        offset = -1
        myStack = traceback.extract_stack()
        #print "Trace"
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
    
    
    def __str__(self):
        restOut = ""
        for i in self.fcnDatas.items():
            restOut += """
Long Name: %s
%s
"""%(i[0],str(i[1]))
        return """
Traceback:

"""+str(self.root) + """


categories and datas:

%s
"""%restOut
    
    
    def branch(self, fcn, fId, args, kw):
        newtree = ExecutionTree(fcn, fId, (args, kw))
        self.pntr.add(newtree)
        self.stack.append(self.pntr)
        self.pntr = newtree
    
    def goBack(self, exp =None, returnValues = None, excdesc = None):
        if exp != None:
            self.pntr.setException(exp, excdesc)
        self.pntr.setReturnValues(returnValues)
        self.pntr = self.stack.pop()
    
    def executionDecorator(self, *categories, **metadatas):
        def ExecutionTreeLog(fcn):
            name = fcn.__name__
            lname = (name, str(self.getStack())[1:-1])
            fId = fId = self.noteNameId(*lname)
            self.fcnDatas[lname] = {"fId":fId, "docStr":fcn.__doc__, "categories":categories, "metadatas":metadatas}
            def decorator(*args, **kw):                
                log = self
                log.branch(fcn, fId, args,kw)
                try:
                    returnValues = fcn(*args,**kw)
                except Exception, e:
                    log.goBack(exp = e, excdesc = traceback.format_exc())
                    raise
                log.goBack(returnValues = returnValues)
                return returnValues
            
            decorator.__name__ = name
            decorator.__doc__ = fcn.__doc__
            decorator.className = fcn.__class__
            return decorator
        return ExecutionTreeLog



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


