# -*- coding: utf-8 -*-
"""
    Tests for Graphingwiki

    @copyright: 2008 by Ossi Herrala <oherrala@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import unittest
import re
from xmlrpclib import ServerProxy, Error, Binary

# Server URL
server = ServerProxy("http://localhost:8080/?action=xmlrpc2")


class GwikiTests(unittest.TestCase):
    '''Generic class with setUp() and tearDown() methods to create and
    delete page.'''

    def setUp(self):
        '''Create a page into wiki so we have a place to run test. Test page
        is named "Gwiki Unit Test %s" where %s is a test method name.'''
        self.pageName = "Gwiki Unit Test %s" % self.id()
        server.putPage(self.pageName, '{{{%s}}}' % self.shortDescription())

    def tearDown(self):
        '''Remove a page from wiki after test is done.'''
        server.DeletePage(self.pageName)


class TestSetMeta(GwikiTests):
    '''Tests for SetMeta(...) call.'''

    def setUp(self):
        GwikiTests.setUp(self)
        self.metaKey = "testiMeta"   # Default metaKey to use in tests.
                                     # Might be overwritten per test case.
        self.metaData = ["dumdidaa"] # Default metaData to use in tests.

    def tearDown(self):
        '''Tear down.. Check the metadata from page and fail if not found.'''
        res = server.getPage(self.pageName)
        for md in self.metaData:
            # Check that all metadata is there
            findMeta = re.compile(r"\s*%s:: %s" % (self.metaKey, md))
            self.assert_(findMeta.search(res), "%s:: %s in '%s'" % (self.metaKey, md, res))
        GwikiTests.tearDown(self)

    def testAdd1(self):
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add')

    def testAdd2(self):
        self.metaData = ["desdi", "dadaa"]
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add')

    def testAdd3(self):
        self.metaKey = "testi foo"
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add')

    def testReplace1(self):
        self.metaData = ["desdi", "dadaa"]
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace2(self):
        server.SetMeta(self.pageName, {self.metaKey: ['456']}, 'add')
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace3(self):
        server.SetMeta(self.pageName, {self.metaKey: ['456']}, 'repl')
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace4(self):
        self.metaKey = "testi foo"
        server.SetMeta(self.pageName, {self.metaKey: ['foobar']}, 'add')
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace5(self):
        self.metaKey = "testi:foo"
        server.SetMeta(self.pageName, {self.metaKey: ['foobar']}, 'add')
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace6(self):
        self.metaKey = u"☠☠☠☠☠☠☃☃☃☃☃äääöööÄÄÄÖÖÖ€€€¶‰"
        server.SetMeta(self.pageName, {self.metaKey: ['foobar']}, 'add')
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testReplace7(self):
        self.metaKey = u"“بسملة”"
        server.SetMeta(self.pageName, {self.metaKey: ['foobar']}, 'add')
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'repl')

    def testAddCategories1(self):
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add', False, 'add', ['CategoryUnitTest'])

    def testAddCategories2(self):
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'add', True, 'add', ['CategoryUnitTest'])


class TestGetMeta(GwikiTests):
    '''Tests for GetMeta(...) call.'''

    def testGet1(self):
        server.GetMeta(self.pageName, False)

    def testGet2(self):
        server.GetMeta(self.pageName, True)


class TestPageCreation(unittest.TestCase):
    '''Tests where page will be created in some way or another. The page
    will be deleted after the test.'''
    def setUp(self):
        self.pageName = "Gwiki Unit Test %s" % self.id()

    def tearDown(self):
        '''Remove a page from wiki after test is done.'''
        server.DeletePage(self.pageName)

    def testAddCategories1(self):
        server.SetMeta(self.pageName, {}, 'add', False, 'add', ['CategoryUnitTest'], "HelpTemplate")

    def testAddCategories2(self):
        server.SetMeta(self.pageName, {}, 'add', True, 'add', ['CategoryUnitTest'], "HelpTemplate")

    def testAddCategories3(self):
        server.SetMeta(self.pageName, {'testMeta': ["desdi dadaa"]}, 'add', False, 'add', ['CategoryUnitTest'], "HelpTemplate")

    def testAddCategories4(self):
        server.SetMeta(self.pageName, {'testMeta': ["desdi dadaa"]}, 'add', True, 'add', ['CategoryUnitTest'], "HelpTemplate")


class TestDeletePage(unittest.TestCase):
    def setUp(self):
        self.pageName = "Gwiki Unit Test %s" % self.id()
        server.putPage(self.pageName, '{{{%s}}}' % self.shortDescription())

    def testDelete1(self):
        server.DeletePage(self.pageName)

    def testDelete2(self):
        server.DeletePage(self.pageName, u'DELETE PAGE')

    def testDelete3(self):
        server.DeletePage(self.pageName)
        try:
            server.DeletePage(u'liipalaapasivujotaeioleolemassa')
        except Error, v:
            # Should check that we have correct error here
            return


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.pageName = "Gwiki Unit Test %s" % self.id()

    def tearDown(self):
        '''Remove a page from wiki after test is done.'''
        server.DeletePage(self.pageName)

    def testGetMeta1(self):
        '''Parser should not find meta tags inside {{{source code}}}
        block.'''
        pageContents = """
{{{
 foo:: bar
}}}
"""
        server.putPage(self.pageName, pageContents)
        res = server.GetMeta(self.pageName, True)
        self.assert_(not res[0])

    def testMetaData1(self):
        '''Parse link in meta data'''
        pageContents = """
  link:: http://www.google.com/
"""
        server.putPage(self.pageName, pageContents)
        res = server.GetMeta(self.pageName, True)
        self.assert_(res)


class TestAttachFile(GwikiTests):
    '''Tests for AttachFile(...) call.'''
    
    #Syntax:  AttachFile(<pagename>, <attachment name>, <action> = ("delete" |  "save" | "list" | "load"), <content>, <overwrite> = (True | False) )
    def testSaveLoadDeleteWithNiceData(self):
        niceData = "jee\n"
        response1 = server.AttachFile(self.pageName, "niceData", "save",Binary(niceData), False)
        exception = None
        try:
            response1_2 = server.AttachFile(self.pageName, "niceData", "save",Binary(niceData), False)
        except Exception, e:
            exception = e
        response1_3 = server.AttachFile(self.pageName, "niceData", "save",Binary(niceData), True)

        response2 = server.AttachFile(self.pageName, "niceData", "load",Binary(""), False)
        response3 = server.AttachFile(self.pageName, "niceData", "delete",Binary(""), False)
        
        self.assertEqual(response2, niceData)
        self.assert_(exception != None)        

# class TestRandomPages(unittest.TestCase):
#     def setUp(self):
#         self.pageName = rStr(16) # A magic number
#         self.pageCont = rStr(65535) # Another magic number

#     def testAddPage(self):
#         try:
#             server.putPage(self.pageName, self.pageCont)
#             server.getPage(self.pageName)
#             # server.DeletePage(self.pageName)
#         except Error, v:
#             self.fail(v)

# def rStr(l):
#     from random import randrange
#     return "".join([chr(randrange(256)) for i in range(randrange(1,l+1))])

if __name__ == '__main__':
    unittest.main()
