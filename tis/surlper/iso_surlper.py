#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
SURLPER
Secure url pillaging extreme roboto
"""
import graphingwiki.editing
import os, signal, time, md5, string, re
import sys, xmlrpclib, urlparse, getpass
#import SocketServer
# from sets import Set as set
from graphingwiki.editing import xmlrpc_attach
from graphingwiki.editing import xmlrpc_conninit, xmlrpc_error, xmlrpc_connect

# Jussin xmlrpc attachment
import AttachFile as xmlAttacher

# globalize :S
serverMayDie = False
urlToSurlp = ''


#class MyClientHandler( SocketServer.BaseRequestHandler ):
#    def handle( self ):
#        print "Contact"
#        client_name = str( self.client_address )
#        print client_name
#        self.request.send( urlToSurlp )#send mw name to the client
#        serverMayDie = True

        
#class SurlpServer( SocketServer.ThreadingTCPServer ):
#    allow_reuse_address = True


# Checks if wikipage of defined name exists in defined wikiPageList
#
# returns true on match
def checkWikiPageExcistance( wikiPageList, wikiPageName ):
    wikiPageExists = False
    for page in wikiPageList:
        if( type( page ) != unicode ):
            if( str( page ) == wikiPageName ):
                wikiPageExists = True
                print "Excisting wikipage with the same name found: " + wikiPageName
                break
            else:
                #if( debug ): print " - db: - " + str( page )
                pass
        #            Depends :: ["olut"]
    return wikiPageExists

## returns a string containing time now in UTC
#
def utctime():
    tmp_time = time.gmtime()
    timestr = str()
    for i in range(6):
        if( tmp_time[i] < 10 ):
            timestr += "0" + str( tmp_time[i] ) + "-"
        else:
            timestr += str( tmp_time[i] ) + "-"
    timestr += "UTC"
    return timestr

def surlper( urlToSurlp ):
    ## MAIN KAMPPAILU ALKAA
    print os.linesep +"* ** SURLPER ** *"
    print os.linesep + "Checking " + urlToSurlp

    # CONSTANTS (sort of)
    debug = True #debug printouts
    live = False #it's either a live- or a testrun

    wikiName = "http://pan0228.panoulu.net/"

    if( debug ):
        print " - db: -Debug information will be printed."
    if( live ):
        pass
    else:
        print "Mode: TEST MODE "





    #make iso
    isofilename = "isofile.osi"
    isofilehandle = open( isofilename, 'w' )
    isofilehandle.write( urlToSurlp )
    isofilehandle.close()
    surlper_image_folder = "/import/research/ouspg/public/vmware-images/malpractice/surlper/"
    isopath = surlper_image_folder + "/x.iso"
    
    command = "mkisofs"
    command_iso = ( "mkisofs", "-r", "-o", isopath, isofilename )
    exitcode = os.spawnvp( os.P_WAIT, command, command_iso )
    if exitcode:
        print "Iso creation exitcode:" , exitcode
    #os.wait()

    surlper_path = surlper_image_folder + "WinXPPro.vmx"

    analysisTime = 3 #in seconds
    command_list = [ "vmware-cmd", surlper_path, "start" ]

#    myPort = 45552
#    myHost = ''

    #INITS
    print "Give username and password for the used wiki:" + os.linesep
    print wikiName
    scheme, netloc, path, _, _, _ = urlparse.urlparse( wikiName )
    username = raw_input("Username:")
    password = getpass.getpass("Password:")
    srcWiki, _ = xmlrpc_conninit(wikiName, username, password)

    if( debug ):
        if( len( str( srcWiki.getPageInfo( "FrontPage" ) ) ) > 0 ):
            print " - db: -Wiki page connected"


    #start up the image
    exitcode = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list )
    if exitcode:
        print "Surlper, vmware-cmd failed on:" + str( exitcode )

    #give the surlper the url
#    myaddr = ( myHost, myPort )
#    print str( myaddr )
#    try:
#        server = SurlpServer( myaddr, MyClientHandler )
#    except SocketServer.socket.error:
#        print "SurlpServer failed to init. Crashing and burning."
#        sys.exit( 4 )
#    while( not serverMayDie ):
#        server.handle_request()## serve one request. SITF. Blocks.

    #let it roll, and take a nap meanwhile
    indexer = 0
    while( indexer < analysisTime ):
        indexer += 1
        if( indexer % 10 == 0 ):
            print "."
        else:
            print ".",
        time.sleep( 1 )

    #(harvest executables)
    #(report)
    #turn off and clean
    command_list[2] = "stop"
    command_list.append( "trysoft" )
    exitcode = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list )
    if exitcode:
        print "Surlper, vmware-cmd" + command_list + " failed on:" + str( exitcode )
        print "Going hard..."
        command_list[3] = "hard"
        exitcode = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list )
        if exitcode:
            print "Surlper shutdown failed. Ejecting..."
            exit( 1 )
    print "Finished"
    


if __name__ == "__main__":
    urlToSurlp = str( sys.argv[1] )## 0-script 1-opt1
    surlper( urlToSurlp )

