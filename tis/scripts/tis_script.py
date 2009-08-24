#!/usr/bin/python
# -*- coding: utf-8 -*-
# $Id: butler.py,v 1.4 2007/08/29 06:06:06 msailio Exp msailio $

"""
This server prepares the next malware in the folder to be examined.

It needs to log the following events:
 - The IP address of the client
 - the name of the malware
 - signal time
"""

#""" Adopted from 'Programmin Python' (page 550)  """

import SocketServer, time, sys, os, string, subprocess, signal, shutil
myHost = ''
myPort = 45552 #b1f0

debug = True
test = False

if( test ):
    malwareFolder = '.'
    processedMalwareFolder = '.'
    malwareArchive = 'archive/'
    tcpdump = "/usr/local/bin/ouspg-tcpdump"
    eth_address = "eth0"
else:
    malwareFolder = '/var/www/malwarezor' # folder where the malware is located on the butler ubuntu.
    processedMalwareFolder = '/Malpractice/prosessed' # after a malware is processed, we move it to here. on Ubuntu
    malwareArchive = '/Malpractice/archive/'
    tcpdump = "tcpdump"
    eth_address = "eth1"

mwFolder = "/media/cdrom1/"

def now():
    return time.ctime( time.time() )

#def start_TCP_dump( filename, address ):
#    #the address is a string with ('ip.ip.ip.ip', port ), and we want only the ip
#    client_ip = string.split( address, "," )
#    client_ip = client_ip[0].strip( "('" )
#    if( debug ): print "Client_ip:" + client_ip
#    command = ( tcpdump , "-i" + eth_address, "-w"+ filename, "host " + client_ip )
#    if( debug ): print "Command is:"+ str( command ) + os.linesep
#    Dumper = subprocess.Popen( command )
#    if( debug ): print "Dumper pid:" + str( Dumper.pid )
#    return Dumper

#def pcapCleaner( filename ):
#    if( os.path.isfile( filename ) != 0 ):
#        #lets use tcpdump to uncipher the .pcap data
#        command = ( tcpdump, "-r"+ filename )
#        dyykkari = subprocess.Popen( command )
#        ( dyyk_stdin, dyyk_stderr ) = dyykkari.communicate( None )
#        if( debug ): print "Dyyk_stdin:" + os.linesep + str( dyyk_stdin ) + os.linesep        
#    else:
#        print "File " + filename +" not found."
#    return

class MyClientHandler( SocketServer.BaseRequestHandler ):
    def handle( self ):
        os.system( "rm /var/www/malwarezor/*" ) 
        #mount malware cd
        os.system( "mount /media/cdrom1" )
        print "Moving malware to share position"
        directory = os.listdir( mwFolder )
        if( len( directory ) > 0 ):
            mw_sample = directory[0]
            shutil.copyfile( mwFolder + "/" + mw_sample, malwareFolder + "/" + mw_sample )
        else:
            print "No malware to analyze. Exiting"
            sys.exit( 1 )
        client_name = str( self.client_address )
        #check malware folder, if there is a malware ready to be investigated
        directories = os.listdir( malwareFolder )
        # There should be only unhandeled malware exes in malwareFolder
        # We could keep the queued malwares in another folder, and now
        # move them to "processing" status, but there is not much use,
        # except for knowing exactly what maltsus are in operation. In
        # normal system usage the queue should be empty (or at least short).
        if( debug ):print "Unanalyzed malware:" + str( directories )
        if( directories.count > 1 ):
            malwareSampleName = directories[0]
            #so there is some crap here to look at
            self.request.send( malwareSampleName )#send mw name to the client
        else:
            self.request.close()
        self.request.recv( 1024 ) #should block until connection is closed with /EOF
        if( test ): pass
        else:
            pass
            # if( debug ): print "Move examined mw to>" + malwareArchive + malwareSampleName + str( now() )
            # os.rename( malwareFolder + "/"+ malwareSampleName, malwareArchive + malwareSampleName + str( now() ) )
        #end TCPdump, close file,
        #       os.kill( DumpObj.pid, signal.SIGKILL )
        #       os.wait()
        # Read the log, and find the paydirt from it
        #       pcapCleaner( dumplogname )
        os.system( "umount /media/cdrom1" )
        if( debug ): print "finished up"
            
class MalServer( SocketServer.ThreadingTCPServer ):
    allow_reuse_address = True

#make a threaded server, listen and handle clients forever
print "The butler is online. Listening at" + str( myHost ) +":" + str( myPort )
myaddr = ( myHost, myPort )
os.system( "umount /media/cdrom1" )
try:
    server = MalServer( myaddr, MyClientHandler )
except SocketServer.socket.error:
    print "Unable to init the server"
    sys.exit( 4 )
server.serve_forever()
