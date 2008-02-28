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
    delete page, and run test in between.'''

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

    def testAdd1(self):
        metaKey = "testiMetaData"
        metaData = ["desdi dadaa"]
        server.SetMeta(self.pageName, {metaKey: metaData}, 'add')
        res = server.getPage(self.pageName)
        findMeta = re.compile(r"\s*%s:: %s" % (metaKey, metaData.pop()))
        self.assert_(findMeta)

    def testAdd2(self):
        server.SetMeta(self.pageName, {'testMeta': ["desdi", "dadaa"]}, 'add')

    def testReplace1(self):
        server.SetMeta(self.pageName, {'testMeta': ['456']}, 'replace')

    def testReplace2(self):
        server.SetMeta(self.pageName, {'testMeta': ['456']}, 'add')
        server.SetMeta(self.pageName, {'testMeta': ['123']}, 'replace')

    def testReplace3(self):
        server.SetMeta(self.pageName, {'testMeta': ['456']}, 'replace')
        server.SetMeta(self.pageName, {'testMeta': ['123']}, 'replace')

    def testAddCategories1(self):
        server.SetMeta(self.pageName, {}, 'add', False, 'add', ['CategoryUnitTest'])

    def testAddCategories2(self):
        server.SetMeta(self.pageName, {}, 'add', True, 'add', ['CategoryUnitTest'])


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
#     def testAddPage(self):
#         from random import randrange
#         def rStr(l): return "".join([chr(randrange(256)) for i in range(randrange(1,l+1))])
#         pageName = rStr(256)
#         try:
#             server.putPage(pageName, rStr(65535))
#             server.getPage(pageName)
#         except Error, v:
#             return


if __name__ == '__main__':
    unittest.main()
