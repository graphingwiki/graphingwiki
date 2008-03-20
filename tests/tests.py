# -*- coding: utf-8 -*-
"""
    Tests for Graphingwiki

    @copyright: 2008 by Ossi Herrala <oherrala@ee.oulu.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import unittest
import re
from xmlrpclib import ServerProxy, Error

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
        findMeta = re.compile(r"\s*%s:: %s" % (self.metaKey, self.metaData.pop()))
        self.assert_(findMeta.search(res))
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
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'replace')

    def testReplace2(self):
        server.SetMeta(self.pageName, {self.metaKey: ['456']}, 'add')
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'replace')

    def testReplace3(self):
        server.SetMeta(self.pageName, {self.metaKey: ['456']}, 'replace')
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'replace')

    def testReplace4(self):
        self.metaKey = "testi foo"
        server.SetMeta(self.pageName, {self.metaKey: ['foobar']}, 'add')
        server.SetMeta(self.pageName, {self.metaKey: self.metaData}, 'replace')

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
