#coding=utf-8
'''
    @copyright: 2007 by Mirko Sailio
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
'''


import os, time
import sys
import urllib2
import string
from socket import *
#import socket
from urlparse import urlparse

debug = 'true'

port = 45552

remote_path = 'http://its0008.virtues.fi/'
remote_host = urlparse(remote_path)[1]

notify_addr = (remote_host, port)

s = socket( AF_INET, SOCK_STREAM )

try:
    s.connect( notify_addr )
except error:
    print "Unable to connect to socket:", remote_host, port
    sys.exit( 1 )
if( debug ): print "Connection made to:", remote_host, port

urlToSurlp = s.recv( 1024 )
if( debug ): print "Receaved mw-name:", urlToSurlp

s.close()

localcommand = "explorer "
os.system( localcommand + urlToSurlp )

time.sleep( 30 )
