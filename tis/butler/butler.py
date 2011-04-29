#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Part of TIS. Use at your peril!

This script starts the needed tcpdump on the vmware server machine.
It also is responsible on starting the vm-images for TIS and VIC

At the moment only 1 TIS / VIC pair is supported

    @copyright: 2007 by Mirko Sailio
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>

"""
import graphingwiki.editing
import os, signal, time, md5, string, re
import sys, xmlrpclib, urlparse, getpass
# the following requirements are from graphingwiki opensource project. See also editing.py
from graphingwiki.editing import xmlrpc_attach
from graphingwiki.editing import xmlrpc_conninit, xmlrpc_error, xmlrpc_connect
# Jussin xmlrpc attachment
import AttachFile as xmlAttacher

# Functions

# Give list to makeDictCountInstance. It counts instances and makes a dict of it. Returns the dict
# ( 'foo', 'foo', 'bar', 'foo'} --> { 'foo': 3, 'bar': 1 }
def makeDictCountInstance( listWeHandle ):
    dictWeMade = dict()
    for listItem in listWeHandle:
        if( listItem not in dictWeMade ):
            dictWeMade[ listItem ] = 1
        else:
            dictWeMade[ listItem ] += 1
    return dictWeMade

# Make a wikiformat table from a dict
#
# parsing function
def makeWikiTableFromDict( dictWeUse, tableName, keyName, valueName ):
    localWikiPageContent = str()
    localWikiPageContent += "\n ||||<tablewidth=\"90%\" style=\"text-align: center\">'''"+ tableName +"'''||"
    localWikiPageContent += "\n ||'''"+ keyName +"'''||'''"+ valueName +"'''||"
    for dictItem in dictWeUse:
        localWikiPageContent += "\n || " + str( dictItem ) + "|| " + str( dictWeUse[ dictItem ] ) + "||"
    localWikiPageContent += "\n"
    return localWikiPageContent

# Checks the given hash against hash database, to find the uniqueness of the malware (or if we have
# analyzed it already)
# If it is unanalyzed, add it to the list.
# 
# returns True if common hash is found
def checkHash( mwhash ):
    md5archive = "./md5archive/live_md5archive.txt" ## requires checking / redirection to smarter media
    #get MD5
    md5FileHandle = open( md5archive, 'r+a' )
    hashline = md5FileHandle.readline() #first line is commentline
    hashMatchFound = False
    while( "" != hashline ):
        if( string.strip( hashline ) == str( mwhash ) ):
            print "*** Hash Match found, mw is previously known ***"
            hashMatchFound = True
        hashline = md5FileHandle.readline()
    if( hashMatchFound == False ):
        md5FileHandle.write( str( hash ) + os.linesep )
    md5FileHandle.close()
    return hashMatchFound    

# Checks if a domain is deemed benign.
#
# returns True, if domainName is a known benign address.
def domainBenignCheck( domainName ):
    check = False
    benignDomainNameList = ( "foo.invalid", "time.windows.com" )
    for benignName in benignDomainNameList:
        if( str( domainName ) == benignName ):
            check = True
            break
    return check

# Checks if IP is benign. This is done using a list of known ip:s that are visible in normal traffic.
#
# returns true, when IP is known to be benign.
def ipBenignCheck( ip_address ):
    check = False
    benignIpList = ( "192.168.123.255", "192.168.123.2", "239.255.255.250", "192.168.123.42", "129.255.255.1", "129.255.255.2", "129.255.255.3", "129.255.255.4", "129.255.255.5", "129.255.255.6", "129.255.255.7", "129.255.255.8", "129.255.255.9" , "129.255.255.10", "129.255.255.11" )
    for benignIp in benignIpList:
        if( str( ip_address ) == benignIp ):
            check = True
            break
    return check

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

#   Parse the results
#
#
def handle_packet( header, content ):
    wikiIrcPacketList = list()
    ircNickList = list()
    ircUserList = list()
    domainName_set = set()                 
    getList = list()
    text_content = str()

    temp_content = content.split( "\n" )
    for temp in temp_content:
        temp = temp.split( '  ' )
        if( len( temp ) > 1 ):
            text_content += temp[2]
    
    #check if the packet is a irc packet using port number 6667
    if( header.find( ".6667 " ) != -1 or
        header.find( ".6667:" ) != -1 ):
        wikiIrcPacketList.append( header + "\n" + content )

    ### IRC - NICKS!!!
    if( "NICK" in text_content ):
        ircNickList.append( header + "\n" + content )

    #All possible hardcoded ip:s
    ip_regexp =  re.findall(r'\d+\.\d+\.\d+\.\d+', header )

    #DNS queries?
    if( header.count( ".domain:" ) > 0 ):
        domain_temp = header.split( ".domain:" )
        domain_temp = domain_temp[1].split( " " )
        domain_name = domain_temp[4]
        domain_name = domain_name.strip( '.' )
        if( debug ): print " - db: -Domain found:" + domain_name
        domainName_set.add( domain_name )

    #GET:s 
    if( "GET" in text_content ):
        getList.append( header + "\n" + content )

    return [ wikiIrcPacketList, ircNickList, ircUserList, ip_regexp, domainName_set, getList ]

## parses SigBuster reports for metadata
#
#  give sigBusterReport (string containing SibBusteroutput)
#  returns list of matches
def SigBusterParsing( sigBusterReport ):
    parsedReport = list()
    sigBusterReport = sigBusterReport.split( "\n" )
    #inti = 0
    for line in sigBusterReport:
        #if( debug ):
        #    inti += 1
        #    print str( inti ) + " " + line
        ##entrypoint
        if( "Entry point was not found in the file" in line ):
            parsedReport.append( "EntrypointNotFound" )

        ## Seeming match for ep
        if( "seems to match with ep" in line ):
            parsedReport.append( "EPQuess " + line[17:25]  )
        
        ##alledged entrypoint
        if( "EP is allegedly at file offset" in line ):
            parsedReport.append("AlledgedEPAt " + line[-12:])
        ##No signature
        if( "Scanned total 1, of which 0 were valid PE files." in line ):
            parsedReport.append( "NotValidPE" )
        else:
        ##Signature found
            if( "Signature found" in line ):
                parsedReport.append( "SigFound"+line[ 15: ] ) #get the signaturename
        if( "Exploit detected:" in line ):
            parsedReport.append("ExploitDetected:" + line[18:])
    return parsedReport


def findDllsFromStrings( strings ):
    outputList = list()
    #print "strings: " + strings
    #find .dll strings
    list_of_lines = strings.split( "\n" )
    for stringLine in list_of_lines:
        if( '.DLL' in stringLine.upper() ):
            outputList.append( "[\"" + stringLine + "\"]" )
    #camelCase?

    return outputList


## MAIN KAMPPAILU ALKAA
print os.linesep +"* ** Malpractice ** *"

# CONSTANTS (sort of)
debug = True #debug printouts
live = True #it's either a live- or a testrun
reboot = True # let's make a mid run reboot
#wikiName = "https://www.clarifiednetworks.com/backstage/tools/ssfim/wiki/" #example
wikiName = "INSERT YOUR WIKINAME HERE"

if( debug ):
    print " - db: -Debug information will be printed."
if( live ):
    check_frequency = 60 #Check once in minute
    loop = 1
    removeMatch = True
    ## path for your virtual image cd-file .iso (where the malware is inserted into the virtual images)
    # isopath = "/research/ouspg/public/vmware-images/malpractice/malpractice_receiver/x.iso"
    isopath = "PATH TO YOUR ISO-FILE HERE"
    ourDummy = 0
    malwareFolder = "./mwfolder"
    storageFolder = "./mw_cemetary"
else:
    print "Mode: TEST MODE "
    removeMatch = False
    loop = 1
    isopath = "x.iso" # local
    number_of_dummies = 1
    ourDummy = 0
    malwareFolder = "./mwfolder"
    check_frequency = 3
    storageFolder = "./mw_cemetary_test"

## path to the internet simulating virtual image (tis) and victim image (vic)
tis_path = "/research/ouspg/public/vmware-images/malpractice/malpractice_receiver/Ubuntu-7.04-server-i386.vmx"
#vic_folder = "/research/ouspg/public/vmware-images/malpractice/victimTest3/"
vic_folder = "/import/research/ouspg/public/vmware-images/malpractice/vic2/WinXPPro/"
vic_path = vic_folder + "WinXPPro.vmx"
vic_redofile = vic_folder + "*REDO*"
vic_redo_graveyard = vic_folder + "redo_graveyard/"

analyze_time = 2 #in minutes
reboot = True # want a reboot in your analysis?
keepOldPages = False # No page overwrite?
command_list_tis = [ "vmware-cmd", tis_path, "start" ]
command_list_vic = [ "vmware-cmd", vic_path, "start" ]

#INITS
#start wiki connection (by: Cooz)
print "Give username and password for the used wiki:" + os.linesep
print wikiName
scheme, netloc, path, _, _, _ = urlparse.urlparse( wikiName )
username = raw_input("Username:")
password = getpass.getpass("Password:")
srcWiki, _ = xmlrpc_conninit(wikiName, username, password)

if( debug ):
    if( len( str( srcWiki.getPageInfo( "FrontPage" ) ) ) > 0 ):
        print " - db: -Wiki page connected"

while( loop ):

    if( live ):
        pass
    else:
        #When testing, going through only once
        loop = 0
        
    directories = os.listdir( malwareFolder )
    #once a minute check if theres new mw to analyse
    if( debug ): print " - db: -Directories: " + str( len( directories ) )
    if( len( directories ) == 0 ):
        if( debug ): print " - db: -No mw to grap."
        time.sleep( check_frequency )
    else:
        mw_sample = directories[0]
        keyRing = dict()
        tmp_time = time.gmtime()
        timestr = str()
        for i in range(6):
            if( tmp_time[i] < 10 ):
                timestr += "0" + str( tmp_time[i] ) + "-"
            else:
                timestr += str( tmp_time[i] ) + "-"
        timestr += "UTC"
        
        keyRing['CreationTime'] = [ timestr ]

        malwareSample = malwareFolder + "/" +  mw_sample
        print "MW detected: " + mw_sample
        keyRing['MalwareName'] = [ str( mw_sample ) ]
        keyRing['FileSize'] = [ str( os.path.getsize( malwareSample ) ) ]
        
        if debug: print str( keyRing['FileSize'] )
                 
        print "Initializing malpractice analysis"
        
        #Get the mw
        try:
            mwhandle = open( malwareSample, 'r' )
        except:
            print "opening mw failed:" + malwareSample
            print "Exiting"
            break
        mwfile = mwhandle.read()
        mwhandle.close( )
        #Read the strings from the file under analysis
        [strings_stdin, strings_stdout] = os.popen2( 'strings '+ malwareSample )
        strings = str( strings_stdout.read() )
        strings_stdin.close()
        os.wait()
        if( debug ): print " - db: -Strings checked."
        strings +=  str( strings_stdout.read() )
        ## if( debug ): print strings
        strings_stdout.close()

        ##make attributes of strings
        keyRing['StringAttributes'] = findDllsFromStrings( strings )

        ##print str( keyRing )
        
        ## print "MWFILE: " + str( mwfile )
        # MD5 hash
        md5hash = md5.md5( mwfile )
        hash = md5hash.hexdigest()
        
        wikiPageName = str( hash ) 
        hashMatchFound = checkHash( hash )
            
        if( hashMatchFound ):
            if( removeMatch ):
                os.remove( malwareFolder + "/" + mw_sample )
        else:
            # wikiPageContent += "\n MalwareMd5Hash:: " + hash
            keyRing['MalwareMd5Hash'] = [ str( hash ) ]
            if( debug ): print " - db: -MD5 hash: " +  hash
            mwfile = "/0" #scope stays for a while, so let's give trash

            ##Run Tonis Toolz
            #PATFINDER 0.3
            # print "Running PatFinder 0.3"
            # command =  "cp " + malwareSample + " temp/"
            # if debug: print " - db: " + command
            # os.system( command )
            # command = "java -jar toolz/PatFinder.jar -f temp/" 
            # if debug: print " - db: " + command
            # [strings_stdin, strings_stdout] = os.popen2( command )
            # strings_stdin.close()
            # os.wait()
            # patFinderOutput = str( strings_stdout.read() )
            # if debug: "- db:" + patFinderOutput
            # os.system( "rm ./temp/" + mw_sample )
            # print "\n\n\n" + patFinderOutput + "\n\n\n"
            # keyRing['PatFinderResults'] = [ str( patFinderOutput ) ]

            #SIGBUSTER 1.1.0
            ## Does not support remote execution (cannot find database), so we travel to /toolz, and execute
            # os.chdir( "toolz/" )
            # print os.path.abspath( "." )
            # print "SigBuster 1.0.5"
            # command = "java -jar SigBuster.jar -ed -f "
            # command += "../mwfolder/" + mw_sample
            # if debug: print " - db:" + command
            # [strings_stdin, strings_stdout] = os.popen2( command )
            # strings_stdin.close()
            # os.wait()
            # sigBusterOutput = str( strings_stdout.read() )
            # if debug: "- db:" + sigBusterOutput
            # keyRing['SigBusterResults'] = [ str( sigBusterOutput ) ]
            # if debug: print "\n"
            # os.chdir( ".." )

            # Make cdrom image containing only the malware. Remove the mw-file from thesystem
            command = "mkisofs"  # mkisofs -r -o x#.iso *log
            arg_list = ( "mkisofs", "-r", "-o", isopath, malwareFolder+"/"+mw_sample )

            if( debug ): print " - db: -Make ISO argument list: " + str( arg_list )
            exitcode = os.spawnvp( os.P_WAIT, command, arg_list )

            #initiate TIS
            exitcode = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_tis )
            if exitcode:
                print "TIS, vmware-cmd failed on:" + str( exitcode )
                
            # We need own config file for each image pointing to each dummy network
            # lets say, the configfiles are form n#_tis_config.vmx, where # shows
            # the number of the dummy network in use    
            # connect to dummy n, and initiate capture
            tcp_command = "/usr/local/bin/ouspg-tcpdump" ## own tcpdump script, used to evade running as su
            pcap_logname = "/tmp/"+hash +".pcap"
            arg_list = ( "ouspg-tcpdump", "-a", "-idummy" + str( ourDummy ), "-s0", "-w" + pcap_logname )
            if( debug ): print " - db: -TCPDUMP command:" + str( arg_list )
            tcppid = os.spawnvp( os.P_NOWAIT, tcp_command, arg_list )
            if( debug ): print " - db: -Pcap log is named: " + pcap_logname

            # initiate the victim image
            exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_vic )
            if exitcode:
                print "VIC, vmware-cmd failed on:" + str( exitcode )

            # # ## Start analysis!
            print "** Analysis started. **"
            if( live ):
                tic_count = 0
                if( reboot ):
                    analyze_time_multiplier = 3
                    print "** Infection run **"
                else:
                    analyze_time_multiplier = 6
                    print "** Analysis run **"
                
                while tic_count < analyze_time * analyze_time_multiplier: # 1(2)minute(s)
                    time.sleep( 10 )
                    print "ETA: " + str ( analyze_time * analyze_time_multiplier *  10 - tic_count * 10 ) + "s"
                    tic_count += 1
            else:
                time.sleep( 60 ) # sec (times shorter than this give lousy packetinfo)
            print "** Timer complete. **"

            #Reboot VIC?
            if( reboot ):
                if( debug ): print " - db: -Trying to do a reboot of VIC"
                command_list_vic[2] = "reset"
                command_list_vic.append( "trysoft" )
                exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_vic )
                shutdowncounter = 0
                while exit_code and shutdowncounter < 5:
                    print "Shut down of VIC failed: " + str( exit_code )
                    exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_vic )
                    time.sleep( 5 ) #Try again until VIC is shutdown
                    shutdowncounter += 1
                if( exit_code ):
                    print "Exitting without succesful restart, trying the hard way"
                    command_list_vic[3] = "hard"
                    exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_vic )
                    time.sleep( 15 )
                else:
                    time.sleep( 30 ) # wait for restart to finish
                    # # ## let's analysis!
                    print "** Analysis started. **"
                    if( live ):
                        tic_count = 0
                        while tic_count < analyze_time * 6:###  2 minutes
                            time.sleep( 10 )
                            print "ETA: " + str ( analyze_time * 60 - tic_count * 10 ) + "s"
                            tic_count += 1
                    else:
                        time.sleep( 60 ) # sec (times shorter than this give lousy packetinfo)
                command_list_vic.pop()
    
            print "** Shutting down TIS and VIC, and parsing data **"
            #Check the vm state
            if( debug ):
                command_list_tis[2] = "getstate"
                command_list_vic[2] = "getstate"
                exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_vic )
                if exit_code:
                    print " - db: -Exitcode for get vic state: " + str( exit_code )

                exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_tis )
                if exit_code:
                    print " - db: -Exitcode for get tis state:: " + str( exit_code )

            #then shut down the vm:s    
            command_list_tis[2] = "suspend"
            command_list_tis.append( "trysoft" )    
            command_list_vic[2] = "stop"
            command_list_vic.append( "trysoft" )
            exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_vic )
            shutdowncounter = 0
            while exit_code or shutdowncounter > 5:
                print "Shut down of VIC failed: " + str( exit_code )
                exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_vic )
                time.sleep( 5 ) #Try again until VIC is shutdown
                shutdowncounter += 1
            #time.sleep( 5 )
            #finally shut down the tcpdump
            time.sleep( 5 ) # takes a short while to shut down, we'll wait
            os.kill( tcppid, signal.SIGTERM )
            pid, status = os.waitpid( tcppid, 0 )

            pcap_tempfile =  "/tmp/" + hash +".tmp"

            # Add .pcap log into the wiki
            arg_list = " -r"+ pcap_logname +" > "+ pcap_tempfile +" -x"
            ## ##(tcp_child_out, tcp_child_in) = os.popen2( tcp_command + arg_list )
            # print "TCP debug arg_list:\n", tcp_command + arg_list
            # print "\nTCP debug pcap_logname:\n", pcap_logname
            ## ##print str( tcp_child_in )
            os.popen2( tcp_command + arg_list )
            os.wait()
            # time.sleep( 5 )#I will KLUDGEON you to DEATH!
            logfile = open( pcap_tempfile , 'r' )
            new_readfile = logfile.readline()

            # GO THROUGH THE .PCAP FILE
            #Initialize lists
            wikiIrcPacketList = list()
            ircNickList = list()
            ircUserList = list()
            ip_regSet = set()
            domainName_set = set()
            getList = list()
            content = "empty"
            header = str()
            #TCPDUMP .pcap packet innards:
            #08:	0x00a0:  2e6d 6963 726f 736f 6674 2e63 6f6d 0d0a  .microsoft.com.22:51.054549 IP 192.168.123.2.http > 192.168.123.42.1037: P 1483:1679(196) ack 834 win 5840
	    #        0x0000:  4500 00ec 4c03 4000 4006 768b c0a8 7b02  E...L.@.@.v...{.
	    #        0x0010:  c0a8 7b2a 0050 040d d9c0 6d1f 0327 4d23  ..{*.P....m..'M#
	    #        0x0020:  5018 16d0 9764 0000 4854 5450 2f31 2e31  P....d..HTTP/1.1
	    #        0x0030:  2034 3034 204e 6f74 2046 6f75 6e64 0d0a  .404.Not.Found..
	    #        0x0040:  4461 7465 3a20 5765 642c 2031 3920 4465  Date:.Wed,.19.De
	    #        0x0050:  6320 3230 3037 2030 383a 3030 3a31 3520  c.2007.08:00:15.
	    #        0x0060:  474d 540d 0a53 6572 7665 723a 2041 7061  GMT..Server:.Apa
	    #        0x0070:  6368 652f 312e 332e 3334 2028 5562 756e  che/1.3.34.(Ubun
	    #        0x0080:  7475 290d 0a4b 6565 702d 416c 6976 653a  tu)..Keep-Alive:
	    #        0x0090:  2074 696d 656f 7574 3d31 352c 206d 6178  .timeout=15,.max
	    #        0x00a0:  3d39 350d 0a43 6f6e 6e65 6374 696f 6e3a  =95..Connection:
	    #        0x00b0:  204b 6565 702d 416c 6976 650d 0a43 6f6e  .Keep-Alive..Con
	    #        0x00c0:  7465 6e74 2d54 7970 653a 2074 6578 742f  tent-Type:.text/
	    #        0x00d0:  6874 6d6c 3b20 6368 6172 7365 743d 6973  html;.charset=is
	    #        0x00e0:  6f2d 3838 3539 2d31 0d0a 0d0a            o-8859-1....
            
            while( new_readfile ):
                if( new_readfile[0] != "\t" ):
                    #it's a packet header, we have our contents solved, so lets analyzing
                    if( content != "empty" ):
                        [ wikiIrcPacketListTemp, ircNickListTemp, ircUserListTemp, ip_regexp, domainName_setTemp, getListTemp ] =  handle_packet( header, content )
                        wikiIrcPacketList.extend( wikiIrcPacketListTemp )
                        ircNickList.extend( ircNickListTemp )
                        ircUserList.extend( ircUserListTemp )
                        for tempset in domainName_setTemp:
                            domainName_set.add( tempset )
                        getList.extend( getListTemp )     
                        
                        for tempRegExp in ip_regexp:
                            ip_regSet.add( tempRegExp )
                    header = new_readfile
                    content = ""
                else:
                    #it's packet innards
                    # temp_content = readfile
                    # temp_content = temp_content.split( '  ' )
                    content += new_readfile + "\n"

                new_readfile = logfile.readline()

            [ wikiIrcPacketListTemp, ircNickListTemp, ircUserListTemp, ip_regexp, domainName_setTemp, getListTemp ] = handle_packet( header, content )
            wikiIrcPacketList.extend( wikiIrcPacketListTemp )
            ircNickList.extend( ircNickListTemp )
            ircUserList.extend( ircUserListTemp )
            for tempset in domainName_setTemp:
                domainName_set.add( tempset )
            getList.extend( getListTemp )     
            logfile.close()
            for tempRegExp in ip_regexp:
                ip_regSet.add( tempRegExp )


            ## SANITY CHECK
            if( debug ):
                pass

            # check if this hash points into a excisting wikipages
            wikiPageList = srcWiki.getAllPages() # replace with something close to sane!
            # There are pages, that are un ASCII:ble. These we do not need to
            # look into, as none of our pages are non ASCII. Problem with python version?
            wikiPageExists = False
            #def
            for page in wikiPageList:
                if( type( page ) != unicode ):
                    if( str( page ) == wikiPageName ):
                        wikiPageExists = True
                        if( debug ):
                            print " - db: -Excisting wikipage with the same name found: " + wikiPageName
                            break
                    else:
                        #if( debug ): print str( page )
                        pass
            
            if( wikiPageExists ):
                #error / add to excisting wikipages
                #if( debug): print "Page" + wikiPageName + "exists. No modifications made"
                if( debug ): print " - db: -Page " + wikiPageName + " exists."
            keyRing['IpAddress'] = list()   
            if( len( ip_regSet ) > 0 ):
                for ip_address in ip_regSet:
                    keyRing['IpAddress'].append( "[\""+ ip_address + "\"]" )
            
            # Add DNS queryset
            # wikiPageContent += "\n== DNS queries found in the capture ==\n"
            keyRing['DNS-query'] = list()
            if( len( domainName_set ) > 0 ):
                for domainName in domainName_set:
                    keyRing['DNS-query'].append( "[\"" + str( domainName ) + "\"]" )

            # Add GET commands

            #Add strings into the packet
            stringLengthBoundry = 7
            strings2 = strings.split( "\n" )
            stringDict = makeDictCountInstance( strings2 )

            '''
            STRINGS AT THE MOMENT ARE JUST ADDED IN PAGE ATTACHMENTS, AND NOT SHOWN
            #wikiPageContent += "|||| Strings ||\n"
            #wikiPageContent += "|| String || Instances ||\n"
            keyRing['Strings'] = list()
            for dictItem in stringDict:
                if( len( str( dictItem )) >= stringLengthBoundry ):
                    #wikiPageContent += "|| {{{ " + str( dictItem ) + " }}} || " +  str( stringDict[ dictItem ] ) + " ||\n"

            #wikiPageContent += makeWikiTableFromDict( makeDictCountInstance( strings ), "Strings" , "String", "Number of occations" )
            # wikiPageContent += "\n----\n"
            '''

            #Add irc packet log into wiki
            if( len( wikiIrcPacketList ) > 0):
                keyRing['ircPacketList'] = list()
                for ircLine in wikiIrcPacketList :
                    keyRing['ircPacketList'].append( str( ircLine ) )

            #Add PatChecker Metafication
            #patFinderOutput
            
            #Add SigBuster Metafication
            #sigBusterOutput

            if( len( ircNickList ) > 0 ):
                nickDict = makeDictCountInstance( ircNickList )

            if( len( ircUserList ) > 0 ):
                userDict = makeDictCountInstance( ircUserList )

            # ATTACHMENTS
            #Add link from page X to new wikipage
            #Add the .pcapdump to the wikipages
            # wikiPageContent += "\n== Attachment ==\n"
            # wikiPageContent += "\n[attachment:" + pcap_logname + "]\n"
            #Strings
            # wikiPageContent += "\n[attachment:strings.txt]\n"
            #REDO attachment
            #return#
            redofilecfg = vic_path
            redofilehandle = open( redofilecfg, 'r' )
            redofileline = redofilehandle.readline()
            redoline = str()
            while( redofileline != 0 ):
                if( redofileline.count( "ide0:0.redo" ) != 0  ):
                    if( debug ): print " - db: -Found REDO line:" + str( redofileline )
                    redoline = redofileline
                    break
                redofileline = redofilehandle.readline()
            redofilehandle.close
            redoline = redoline.split( '"' )
            if( debug ): print " - db: -redo filename: " + str( redoline )
            redofilename = redoline[1]
            
            '''
result = xmlrpc_connect(srcWiki.SetMeta, wiki, page, input, method, True, category_edit, catlist, template)

            '''

            '''
            ### NO MORE PUTPAGE
            #Send the wikipage to the wiki
            if( srcWiki.putPage( wikiPageName, wikiPageContent ) ):
                if( debug ):
                    print " - db: -Made gwiki page: " + wikiPageName
            else:
                print "Making gwikipage failed."
            '''
            
            ## keyRing['SigBusterFeatures'] = SigBusterParsing( sigBusterOutput ) ##uses 3rd party tool. Removed

            

            if( debug ): print "- db: -xmlAttacher.save_meta()"
            xmlAttacher.save_meta( srcWiki, wikiName, wikiPageName, keyRing, True, '', '', 'MalwareTemplate' )
                
                                           
            # add attachment
            # def save(request, pagename, filename, content, overwrite)
            if( debug ): " - db: -Attaching pcap file to wiki"
            pcapFileHandle = open( pcap_logname, 'r' )
            pcapfile = pcapFileHandle.read() #first line is commentline
            pcapFileHandle.close()
            xmlrpc_attach( wikiName, wikiPageName, pcap_logname, username, password, 'save', pcapfile, True )
            ### redofile was too large to be included atm
            # if( debug ): " - db: -Attaching REDO file to wiki"
            # redoFileHandle = open( "/research/ouspg/development/frontier/prototyping/c10/malpractice/vms/victim/redo_image/" + redofilename, 'r' )
            # redoFile = redoFileHandle.read()
            # redoFileHandle.close()
            # xmlrpc_attach( wikiName, wikiPageName, redofilename, username, password, 'save', redoFile, True )
            if( debug ): " - db: -Attaching strings file to wiki"
            xmlrpc_attach( wikiName, wikiPageName, "strings.txt", username, password, 'save', strings, True )
            if( debug ): " - db: -Attaching PatFinder file to wiki"
            xmlrpc_attach( wikiName, wikiPageName, "PatFinder.txt", username, password, 'save', patFinderOutput, True )
            if( debug ): " - db: -Attaching SigBuster results file to wiki"
            xmlrpc_attach( wikiName, wikiPageName, "SigBuster.txt", username, password, 'save', sigBusterOutput, True )  # result = xmlrpc_attach(wiki, page, fname, username, password,
            #                        'save', content, overwrite)

            #GET attachment
            getFileContent = str()
            for getLine in getList:
                getFileContent += getLine + "\n"

            xmlrpc_attach( wikiName, wikiPageName, "getlines.txt", username, password, 'save', getFileContent, True )
            
            #Check all found instances for existing wikipages
            # First DNS
            if( debug ): print " - db: -Checking for instance wikipages"
            for dnsName in domainName_set:
                # keepOldPages is false, when we want to rewrite pages
                if( checkWikiPageExcistance( wikiPageList, str( dnsName ) ) and keepOldPages ):
                    #no need for new page. Changes to old? Is Linked-in enough?
                    pass
                else:
                    wikiPageContent = "## Malpractice autocreated wikipage \n"
                    wikiPageContent += "== "+ str( dnsName ) +" ==\n"
                    wikiPageContent += " MalpracticeType:: HostName\n"
                    if( domainBenignCheck( str( dnsName ) ) ):
                        wikiPageContent +=" Benign:: Yes \n"
                    else:
                        wikiPageContent +=" Benign:: No \n"
                    wikiPageContent += "----\n[[LinkedIn]]\n----\nCategoryHostName"
                    srcWiki.putPage( str( dnsName ), wikiPageContent )
            #Then IpAddresses
            for ipAddress in ip_regSet:
                if( checkWikiPageExcistance( wikiPageList, str( ipAddress ) ) and keepOldPages ):
                    #no need for new page. Need changes to old? Is Linked-in enough?
                    pass
                else:
                    wikiPageContent = "## Malpractice autocreated wikipage \n"
                    wikiPageContent += "== "+ str( ipAddress ) +" ==\n"
                    wikiPageContent += " MalpracticeType:: IpAddress\n"
                    if( ipBenignCheck( str( ipAddress ) ) ):
                        wikiPageContent +=" Benign:: Yes \n"
                    else:
                        wikiPageContent +=" Benign:: No \n"
                    wikiPageContent += "----\n[[LinkedIn]]\n----\nCategoryIpAddress"
                    srcWiki.putPage( str( ipAddress ), wikiPageContent )
                    #setMeta
                    
            ##cleanup time
            exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_tis )
            if exit_code:
                print "Suspend of TIS failed: " + str( exit_code )
            os.remove( pcap_tempfile ) # testor
            os.remove( pcap_logname )
            #put victim REDO image into the wiki, and then delete REDO
            os.rename( malwareFolder + "/" + mw_sample, storageFolder + "/" + mw_sample )
            os.system( "mv " +  vic_redofile + " " + vic_redo_graveyard + "." )
            # There has been instances of the victim not shutting down, so we will
            # make a extra hard shutdown. This helps keeping the images in the right
            # state. The Victim sometimes cannot softly shutdown.
            command_list_vic[3] = "hard"
            exit_code = os.spawnvp( os.P_WAIT, "vmware-cmd", command_list_vic )
            # Return the control state to original
            command_list_tis[2] = "start"
            command_list_tis.pop()    
            command_list_vic[2] = "start"
            command_list_vic.pop()














