#s!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, md5
import email.Parser
import string, re
import types, time
import urlparse, getpass, xmlrpclib
from editing import xmlrpc_attach
# Jussin xmlrpc attachment
import AttachFile as xmlAttacher

#omia importteja
# from its1_runner import makeDictCountInstance
# from its1_runner import makeWikiTableFromDict

debug = True
# wikiName = "http://dyn57/gwiki"
# wikiName = "http://gw13.virtues.fi:10014/gwiki/"
wikiName = "http://pan0228.panoulu.net/"
'''
urlList = list()
attachmentList = list()
wikiPageContent = ""
'''
## sanityzeFileName( str )
# Is given a string, that has arbitrary characters.
# SanityzeFN removes dangerous characters
# and replaces empty spaces with _
# Returns str

def sanityzeFileName( filename ):
    removelist = ( ',', '.', ';', ':', '\\', '/', '*', '?', '$', '#' )
    filename = filename.replace( ' ', '_' )
    for character in removelist:
        filename = filename.replace( character, '' )
    #We want to keep the filetype as it was, so lets put a .XXX to the end: Ugly hak
    filename += "." + filename[-3:]
    if debug: print "Parsed filename is " + filename
    return filename


def main():
    #init stuff
    urlList = list()
    attachmentList = list()
    wikiPageContent = ""
    spamWikiPageName = ""
    #init Wiki
    print "SpamTrap\n"
    print "Give username and password for the used wiki:" + os.linesep
    print wikiName
    scheme, netloc, path, _, _, _ = urlparse.urlparse( wikiName )
    username = raw_input("Username:")
    password = getpass.getpass("Password:")
    print "Give password for moving the spam to malpractice:" + os.linesep
    bunkpassword = getpass.getpass("Bunker Password:")
    netloc = "%s:%s@%s" % (username, password, netloc)
    action = "action=xmlrpc2"
    url = urlparse.urlunparse((scheme, netloc, path, "", action, ""))
    #print 'xxxxx', url
    logWiki = xmlrpclib.ServerProxy(url)
    
    maildir = "/home/msailio/Mail/spamtrap/new/"
    savedir = "/home/msailio/Mail/spamtrap/malign_suspects/"
    # maildir = "/home/vpopmail/domains/mydomain.com/support/Maildir/cur"
    # cntr = 0
    while( True ):
        for files in os.listdir(maildir):
            print "loop begings files:" + str( os.listdir(maildir) )
            # time.sleep( 1 )
            #cntr += 1
            urlList = list()
            attachmentList = list()
            MalwareHashString = 'empty'
            # counter = 0
            print os.path.join(maildir, files)

            #GET FILE
            fp = open(os.path.join(maildir, files), "rb")
            p = email.Parser.Parser()
            msg = p.parse(fp)
            # print( str( msg ) )
            fp.close()

            # print msg.get("Content-Type")
            # LOOK AT MESSAGE
            for part in msg.walk():
                #FETCH DA ATTACHMENTS (if they r cute)
                contentType = part.get("Content-Type")
                '''
                if( debug ):
                    print str( contentType )
                    print type( contentType )
                '''
                # I wills kludgeon your FACE!    
                if( contentType == None):
                    break
                contentType = contentType.split( ';' )
                contentTypeShort = contentType[0].split( '/' )
                if( contentTypeShort[0] == "application" ):
                    #if( debug ): print "Tää me halutaan"
                    exec_name = contentType[1].split( '\"' )
                    payload = part.get_payload( decode=1 )
                    # print payload
                    my_hash = md5.md5( payload )
                    filename = "mws_" + str( my_hash.hexdigest() ) + sanityzeFileName( str( exec_name[1] ) )
                    #filename += "." + filename[-3]
                    if debug: print "Parsed filename is " + filename
                    # counter += 1
                    attachmentList += filename
                    fp = open( os.path.join(savedir, filename), "wb" )
                    # print os.path.join(savedir, filename)
                    fp.write( payload )
                    fp.close()
                    #hash is different. Must kludgeon it in da face!
                    fp = open( os.path.join(savedir, filename), "rb" )
                    malwarefile = fp.read()
                    fp.close()
                    my_new_hash = md5.md5( malwarefile )


                    
                    command = 'scp ' + os.path.join(savedir, filename) + ' its1:/export/research/ouspg/development/frontier/prototyping/c10/malpractice/script/mwfolder/.'
                    #print command
                    os.system( command )
                    MalwareHashString = str( my_new_hash.hexdigest() )

                    #FETCH DA URLS (No fatties though)
                    # '''
                    # 12:54 < matlok> miRko, esim cat /var/mail/`whoami` | perl -i -pe 
                    #      "s/^.*?([a-z][a-z]*:\/\/[a-z0-9.\/?%]*).*$/LINK \1/" | grep 
                    #      "^LINK" | sort | uniq -c | sort
                    # '''
                else:
                    payload = str( part.get_payload( decode = 1 ) )
                    stuffByLines = payload.split( '\n' )
                    for line in stuffByLines:
                        our_match = re.match( '[a-z][a-z]*:\/\/[a-z0-9.\/?%]*', line )
                        if( our_match != None ):
                            if( debug ): print "URL found:" + our_match.string
                            # TODO: Trimm this shit
                            urlList.append( our_match.string )
                        '''    
                        if( line.find( 'http://' ) >= 0 ):
                            if( debug ): print "URL found:" + line
                            # TODO: Trimm this shit
                            urlList.append( line )
                        '''

            if( debug ): print "\n*****"
            print "\n"
            # print str( msg )        
            # if( cntr > 10 ): break
            # add the spam into the wiki as a attachment
            spamWikiPageName = md5.md5( str( msg ) )
            spamWikiPageName = spamWikiPageName.hexdigest()
            wikiPageContent += "= " + spamWikiPageName +" ="

            tmp_time = time.gmtime()
            timestr = str()
            for i in range(6):
                if( tmp_time[i] < 10 ):
                    timestr += "0" + str( tmp_time[i] ) + "-"
                else:
                    timestr += str( tmp_time[i] ) + "-"
            timestr += "UTC"
            
            wikiPageContent += "\n Spamtraptime:: " + timestr + "+\n"

            # add the found URL:s in the wikipage
            wikiPageContent += "\n----\n== URLs: ==\n"
            for urlInstance in urlList:
                wikiPageContent += " SpamUrlFound:: [\"" + urlInstance + "\"]\n"

            # if found malware
            if( MalwareHashString != 'empty' ):
                wikiPageContent += "\n== Payload ==\n Payload:: [\"" + MalwareHashString + "\"]\n"
                print MalwareHashString

            
            # NEEDS INTERFACE FOR SURLPER!

            # add the found Attachments to            
            wikiPageContent += "\n\n"
            for attachmentFound in attachmentList:
                wikiPageContent += " SpamAttachmentFound::[\"" + attachmentFound + "\"]\n "

            # Attachments (like the mail)
            wikiPageContent += "\n== Attachment ==\n"
            wikiPageContent += "\n[attachment:"+ spamWikiPageName +"]\n"

            # Mark this as spam
            wikiPageContent += "----\n ##Should maybe have some meaningful metadata, like "

            #End stuff
            wikiPageContent += "----\n[[LinkedIn]]\n----\nCategorySpamSample"

            #Send the wikipage to the wiki
            try:
                if( logWiki.putPage( spamWikiPageName, wikiPageContent ) ):
                    if( debug ):
                        print "Made gwiki page: " + spamWikiPageName
                else:
                    print "Making gwikipage failed."
            except:
                print "wiki.putPage error"

            wikiPageContent = ''


            # add the e-mail as a attachment to the wikipage
            emailfile = open(os.path.join(maildir, files), "rb")
            email_innards = emailfile.read()
            emailfile.close()
            xmlrpc_attach( wikiName, spamWikiPageName, spamWikiPageName, username, password, 'save', email_innards, True )

            # check if this spams URL:s already have pages, if not, make 'em
            # or not
            '''
            wikiPageList = logWiki.getAllPages()
            for urli in urlList:
                if( wikiPageList.count( urli ) == 0 ):
                    urliName = str( urli.replace( "/", "" ) )
                    wikiPageContent = "## Malpractice autocreated wikipage, for URL \n"
                    wikiPageContent += "= "+ urliName +" =\n"
                    wikiPageContent += " MalpracticeType:: URL\n"
                    wikiPageContent += "----\n[[LinkedIn]]\n----\nCategoryHostName"
                    logWiki.putPage( "URL_"+ urliName , wikiPageContent )
                    wikiPageContent = ""
                    '''
            #move e-mail to cleared
            os.system( 'mv ' + maildir + '/' + files + " " + savedir )
        print ".",
        time.sleep( 60 )
        

# Runner        
if __name__ == '__main__':
    main()



## Multiple layers of encoding?
