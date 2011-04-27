# -*- coding: utf-8 -*-
"""
    Tests for Graphingwiki

    @copyright: 2008 by Ossi Herrala <oherrala@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import unittest
import re, sys
from xmlrpclib import ServerProxy, Error, Binary
from MoinMoin import log
from MoinMoin.script import MoinScript


# server_url = "https://mytestuser:mytestpass@localhost/collab/wiki?action=xmlrpc2"
server_url = "https://localhost/collab/wiki?action=xmlrpc2"

def start_server():
    MoinScript(argv=["server", "standalone"]).run()

class GwikiTestCase(unittest.TestCase):
    '''Generic class with setUp() and tearDown() methods to create and
    delete page.'''

    def setUp(self):
        '''Create a page into wiki so we have a place to run test. Test page
        is named "Gwiki Unit Test %s" where %s is a test method name.'''
        self.server = ServerProxy(server_url)
        self.pageName = "Gwiki Unit Test %s" % self.id()
        self.server.putPage(self.pageName, '{{{%s}}}' % self.shortDescription())

    def tearDown(self):
        '''Remove a page from wiki after test is done.'''
        self.server.DeletePage(self.pageName)


class TestSetMeta(GwikiTestCase):
    '''Tests for SetMeta(...) call.'''

    def setUp(self):
        GwikiTestCase.setUp(self)
        self.metaKey = "testiMeta"   # Default metaKey to use in tests.
                                     # Might be overwritten per test case.
        self.metaData = ["dumdidaa"] # Default metaData to use in tests.

    def tearDown(self):
        '''Tear down.. Check the metadata from page and fail if not found.'''
        res = self.server.getPage(self.pageName)
        for md in self.metaData:
            # Check that all metadata is there
            findMeta = re.compile(r"\s*%s:: %s" % (self.metaKey, md))
            self.assert_(findMeta.search(res), "%s:: %s in '%s'" % (self.metaKey, md, res))
        GwikiTestCase.tearDown(self)

    def testAdd1(self):
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add')

    def testAdd2(self):
        self.metaData = ["desdi", "dadaa"]
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add')

    def testAdd3(self):
        self.metaKey = "testi foo"
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add')

    def testReplace1(self):
        self.metaData = ["desdi", "dadaa"]
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace2(self):
        self.server.SetMeta(self.pageName, {self.metaKey: ['456']}, 'add')
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace3(self):
        self.server.SetMeta(self.pageName, {self.metaKey: ['456']}, 'repl')
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace4(self):
        self.metaKey = "testi foo"
        self.server.SetMeta(self.pageName, {self.metaKey: ['foobar']}, 'add')
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace5(self):
        self.metaKey = "testi:foo"
        self.server.SetMeta(self.pageName, {self.metaKey: ['foobar']}, 'add')
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace6(self):
        self.metaKey = u"☠☠☠☠☠☠☃☃☃☃☃äääöööÄÄÄÖÖÖ€€€¶‰"
        self.server.SetMeta(self.pageName, {self.metaKey: ['foobar']}, 'add')
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace7(self):
        self.metaKey = u"“بسملة”"
        self.server.SetMeta(self.pageName, {self.metaKey: ['foobar']}, 'add')
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testAddCategories1(self):
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add', False, 'add', ['CategoryUnitTest'])

    def testAddCategories2(self):
        self.server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add', True, 'add', ['CategoryUnitTest'])


class TestGetMeta(GwikiTestCase):
    '''Tests for GetMeta(...) call.'''

    def testGet1(self):
        self.server.GetMeta(self.pageName, False)

    def testGet2(self):
        self.server.GetMeta(self.pageName, True)


class TestPageCreation(GwikiTestCase):
    '''Tests where page will be created in some way or another. The page
    will be deleted after the test.'''
    def setUp(self):
        GwikiTestCase.setUp(self)
        self.pageName = "Gwiki Unit Test %s" % self.id()

    def tearDown(self):
        '''Remove a page from wiki after test is done.'''
        self.server.DeletePage(self.pageName)

    def testAddCategories1(self):
        self.server.SetMeta(self.pageName, {}, 'add', False, 'add', ['CategoryUnitTest'], "HelpTemplate")

    def testAddCategories2(self):
        self.server.SetMeta(self.pageName, {}, 'add', True, 'add', ['CategoryUnitTest'], "HelpTemplate")

    def testAddCategories3(self):
        self.server.SetMeta(self.pageName, {'testMeta': ["desdi dadaa"]}, 'add', False, 'add', ['CategoryUnitTest'], "HelpTemplate")

    def testAddCategories4(self):
        self.server.SetMeta(self.pageName, {'testMeta': ["desdi dadaa"]}, 'add', True, 'add', ['CategoryUnitTest'], "HelpTemplate")


class TestDeletePage(GwikiTestCase):
    def setUp(self):
        GwikiTestCase.setUp(self)
        self.pageName = "Gwiki Unit Test %s" % self.id()
        self.server.putPage(self.pageName, '{{{%s}}}' % self.shortDescription())

    def testDelete1(self):
        self.server.DeletePage(self.pageName)

    def testDelete2(self):
        self.server.DeletePage(self.pageName, u'DELETE PAGE')

    def testDelete3(self):
        self.server.DeletePage(self.pageName)
        try:
            self.server.DeletePage(u'liipalaapasivujotaeioleolemassa')
        except Error, v:
            # Should check that we have correct error here
            return


class TestParsing(GwikiTestCase):
    def setUp(self):
        GwikiTestCase.setUp(self)
        self.pageName = "Gwiki Unit Test %s" % self.id()

    def tearDown(self):
        '''Remove a page from wiki after test is done.'''
        self.server.DeletePage(self.pageName)

    def testGetMeta1(self):
        '''Parser should not find meta tags inside {{{source code}}}
        block.'''
        pageContents = """
{{{
 foo:: bar
}}}
"""
        self.server.putPage(self.pageName, pageContents)
        res = self.server.GetMeta(self.pageName, True)
        self.assert_(not res[0])

    def testMetaData1(self):
        '''Parse link in meta data'''
        pageContents = """
  link:: http://www.google.com/
"""
        self.server.putPage(self.pageName, pageContents)
        res = self.server.GetMeta(self.pageName, True)
        self.assert_(res)


class TestAttachFile(GwikiTestCase):
    '''Tests for AttachFile(...) call.'''
    
    #Syntax:  AttachFile(<pagename>, <attachment name>, <action> = ("delete" |  "save" | "list" | "load"), <content>, <overwrite> = (True | False) )
    def testSaveLoadDeleteWithNiceData(self):
        niceData = "jee\n"
        response1 = self.server.AttachFile(self.pageName, "niceData", "save",Binary(niceData), False)
        exception = None
        try:
            response1_2 = self.server.AttachFile(self.pageName, "niceData", "save",Binary(niceData), False)
        except Exception, e:
            exception = e
        response1_3 = self.server.AttachFile(self.pageName, "niceData", "save",Binary(niceData), True)

        response2 = self.server.AttachFile(self.pageName, "niceData", "load",Binary(""), False)
        response3 = self.server.AttachFile(self.pageName, "niceData", "delete",Binary(""), False)
        
        self.assertEqual(response2, niceData)
        self.assert_(exception != None)        

# class TestRandomPages(GwikiTestCase):
#     def setUp(self):
#         GwikiTestCase.setUp(self)
#         self.pageName = rStr(16) # A magic number
#         self.pageCont = rStr(65535) # Another magic number

#     def testAddPage(self):
#         try:
#             self.server.putPage(self.pageName, self.pageCont)
#             self.server.getPage(self.pageName)
#             # self.server.DeletePage(self.pageName)
#         except Error, v:
#             self.fail(v)

# def rStr(l):
#     from random import randrange
#     return "".join([chr(randrange(256)) for i in range(randrange(1,l+1))])

if __name__ == '__main__':
    if len(sys.argv) == 2:
        # kludge against unittest eating and choking on all args
        server_url = sys.argv[1]
        del sys.argv[1]

    unittest.main()
