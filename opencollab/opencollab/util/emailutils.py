# -*- coding: utf-8 -*-
"""
    @copyright: 2009 Lari Huttunen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import re, sys, getpass, imaplib, email, cStringIO, copy
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
    return metas

def parseURLs(metas):
    #new_metas = Metas()
    new_metas = copy.deepcopy(metas)
    href = re.compile('(href|HREF)=(3D)?\"')
    tag = re.compile('\'\">?.*$')
    gtlt = re.compile('[<>]')
    for cpage in metas:
        msg = metas[cpage]['msg'].single()
        body = ""
        for line in body_line_iterator(msg, decode=True):
            body+=line
        tokens = body.split()
        for token in tokens:
            if url_all_re.search(token):
                token = href.sub('', token)
                token = tag.sub('', token)
                token = gtlt.sub('', token)
                new_metas[cpage]['SPAM URL'].add(token)
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

