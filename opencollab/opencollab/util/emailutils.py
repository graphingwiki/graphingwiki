# -*- coding: utf-8 -*-
"""
    @copyright: 2009 Lari Huttunen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import re, sys, getpass, imaplib, email, cStringIO, copy, mimetypes, HTMLParser
from opencollab.meta import Metas
from opencollab.util.file import hashFile, uploadFile
from opencollab.util.regexp import *
from email.Iterators import body_line_iterator
try:
    import email.utils
    from email.utils import getaddresses
except:
    import email.Utils
    from email.Utils import getaddresses

def imapsAuth(imaps_server, imaps_user, imaps_pass):
    try:
        mailbox = imaplib.IMAP4_SSL(imaps_server)
    except imaplib.socket.gaierror:
        error = 'ERROR: No address associated with hostname: ' + imaps_server
        sys.exit(error)
    if imaps_pass is None:
        imaps_pass = getpass.getpass()
    try:
        mailbox.login(imaps_user, imaps_pass)
    except:
        error = 'ERROR: Login failed: authentication failure'
        sys.exit(error)
    return mailbox

def getMessagesAndUpload(mailbox, collab):
    metas = Metas()
    mailbox.select()
    try:
        typ, data = mailbox.search(None, 'UNSEEN')
    except:
        error = 'ERROR: Search failed'
        sys.exit(error)
    for num in data[0].split():
        try:
            typ, data = mailbox.fetch(num, '(RFC822)')
        except:
            error = 'ERROR: Fetch failed'
            sys.exit(error)
        msg = email.message_from_string(data[0][1])
        msg_obj = cStringIO.StringIO(data[0][1])
        cpage = hashFile(msg_obj)
        epoch = int(time())
        metas[cpage]["ATTRIBUTION"].add('<<DateTime(%s)>>' % epoch)
        metas[cpage]["RFC822 Message"].add('[[attachment:%s.txt]]' % cpage)
        metas[cpage]["TYPE"].add("SPAM")
        metas[cpage]["msg"].add(msg)
        uploadFile(collab, cpage, data[0][1], cpage + '.txt')
        counter = 1
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            ext = mimetypes.guess_extension(part.get_content_type())
            if not ext:
                ext = '.bin'
                filename = 'part-%03d%s' % (counter, ext)
            counter += 1
            ctype = part.get_content_type()
            if ctype == 'text/plain':
                metas[cpage]["text"].add(part.get_payload(decode=True))
            elif ctype == 'text/html':
                metas[cpage]["html"].add(part)
            else:
                ufile = part.get_payload(decode=True)
                if ufile:
                    metas[cpage]["Attachment"].add('[[attachment:%s]]' % filename)
                    uploadFile(collab, cpage, ufile, filename)
    return metas

def lexifyAndParseURLs(metas):
    punct = re.compile('[\.,:;]')
    oddball = re.compile('[\xab\xbb\x92\xa9]')
    new_metas = copy.deepcopy(metas)
    for cpage in metas:
        for text in metas[cpage]["text"]:
            shred = []
            shred = text.split()
            for token in shred:
                if url_all_re.search(token):
                    new_metas[cpage]['SPAM URL'].add(token)
                else:
                    try:
                        token = unicode(token, "utf-8")
                    except:
                        try:
                            token = unicode(token, "iso-8859-1")
                        except:
                            token = "UNSUPPORTED-CHARSET"
                    token = punct.sub('', token)
                    token = token.lower()
                    new_metas[cpage]["Lexeme"].add(token) 
    return new_metas

# From http://pleac.sourceforge.net/pleac_python/webautomation.html
class html(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self._plaintext = ""
        self._ignore = False
    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._ignore = True
    def handle_endtag(self, tag):
        if tag == "script":
            self._ignore = False
    def handle_data(self, data):
        if len(data)>0 and not self._ignore:
            self._plaintext += data
    def get_plaintext(self):
        return self._plaintext
    def error(self,msg):
        # ignore all errors
        pass

def parseURLs(html_content):
    href = re.compile('(href|HREF)=(3D)?\"')
    tag = re.compile('\'\">?.*$')
    gtlt = re.compile('[<>]')
    urls = []
    for line in html_content:
            tokens = line.split()
            for token in tokens:
                if url_all_re.search(token):
                    token = href.sub(' ', token) 
                    token = tag.sub(' ', token)
                    token = gtlt.sub(' ', token)
                urls.append(token)   
    return urls

def parseHTML(metas):
    new_metas = copy.deepcopy(metas)
    for cpage in metas:
        for html_part in metas[cpage]["html"]:
            page_html = html_part.get_payload(decode=True)
            parser = html()
            try:
                parser.feed(page_html)
            except:
                print "HTML parse error, salvaging URLs in: ", cpage
                urls = parseURLs(page_html)
                for url in urls:
                    new_metas[cpage]["SPAM URL"].add(url)
            else:
                parser.close()  # force processing all data
                new_metas[cpage]["text"].add(parser.get_plaintext())
    return new_metas

def parseMetaData(metas):
    #new_metas = Metas()
    new_metas = copy.deepcopy(metas)
    gtlt = re.compile('[<>]')
    for cpage in metas:
        msg = metas[cpage]['msg'].single()
        tos = msg.get_all('to', [])
        ccs = msg.get_all('cc', [])
        resent_tos = msg.get_all('resent-to', [])
        resent_ccs = msg.get_all('resent-cc', [])
        all_recipients = getaddresses(tos + ccs + resent_tos + resent_ccs)
        for r in all_recipients:
            new_metas[cpage]["Recipient"].add(r[1])
        reply_to = msg.get_all('reply-to', [])
        if reply_to:
            new_metas[cpage]["Sender"].add(reply_to[0])
        msg_from = msg.get_all('from', []).pop()
        new_metas[cpage]["From"].add(msg_from)
        date = msg.get_all('date', []).pop()
        new_metas[cpage]["Date"].add(date)
        subject = msg.get_all('subject',[]).pop()
        subject = email.Header.decode_header(subject).pop()
        if subject[1] is not None:
            subject = unicode(subject[0], subject[1])
        else:
            subject = unicode(subject[0], 'utf-8')
        new_metas[cpage]["Subject"].add(subject)
        rpath = msg.get_all('return-path', []).pop()
        rpath = gtlt.sub('', rpath)
        new_metas[cpage]["Return-Path"].add(rpath)
    return new_metas

