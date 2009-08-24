if __name__ == "__main__":
    import sys
    import xmlrpclib
    import urlparse
    import getpass
    import string
    import graphingwiki.editing
    from graphingwiki.editing import xmlrpc_conninit, xmlrpc_error, xmlrpc_connect
    import AttachFile as xmlAttacher

    scheme = "http"
    netloc = "dyn57"
    path = "gwiki"
    #scheme, netloc, path, _, _, _ = urlparse.urlparse(sys.argv[1])
    #if scheme.lower() != "https":
    #    raise TypeError, "allowed only for HTTPS"

    username = raw_input("Username:")
    password = getpass.getpass("Password:")
    netloc = "%s:%s@%s" % (username, password, netloc)

    action = "action=xmlrpc2"
    url = urlparse.urlunparse((scheme, netloc, path, "", action, ""))
    srcWiki = xmlrpclib.ServerProxy(url)

    unilist = list()

    #pagelist = srcWiki.getAllPages()
    #for page in pagelist:
    #if( type( page ) == unicode ):
    #    unilist.append( page )
    #print str( unilist )
    #page =  srcWiki.getPage("PutPageTestPage")
    page = "Testing xmlrpclib"
    pageName = "PageOfTest"
    #if( srcWiki.putPage( pageName, page + "tadaa" ) ):
    #    print "putPage Returned true"
    #else:
    #    print "putPage Returned false"
    # print str( srcWiki.getPage( pageName ) )
    mwname = 'MaltsuX'
    srcWiki, _ = xmlrpc_conninit(url, username, password)
                                                                     
    out = {'IpAddress': ['value1', 'value2'], 'CreationTime': [ '12.34.56'], 'MalwareName' : [ mwname ], 'DNS-query': ['www.foobar.com', 'www.absoluteass.org', 'www.politics.are.like.mil'] }
    print xmlAttacher.save_meta(srcWiki, url, 'page', out, True, '', '', 'MalwareTemplate' )
    #save_meta(srcWiki, wiki, key, out, createpage=True, category_edit='', catlist=[], template=''): 
