# -*- coding: utf-8 -*-
"""
    @copyright: 2009 Lari Huttunen
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import re, sys, getpass, imaplib, email, cStringIO
from opencollab.meta import Metas
from opencollab.util.file import hashFile
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

def getMessages(mailbox):
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
        metas[cpage]["RFC822 MESSAGE"].add('[[attachment:%s.txt]]' % cpage)
        metas[cpage]["TYPE"].add("SPAM")
        metas[cpage]["msg"].add(msg)
    return metas

def parseURLs(metas):
    new_metas = Metas()
    new_metas = metas
    href = re.compile('(href|HREF)=(3D)?\"')
    tag = re.compile('\">?.*$')
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
    new_metas = Metas()
    new_metas = metas
    for cpage in metas:
        msg = metas[cpage]['msg'].single()
        tos = msg.get_all('to', [])
        ccs = msg.get_all('cc', [])
        resent_tos = msg.get_all('resent-to', [])
        resent_ccs = msg.get_all('resent-cc', [])
        all_recipients = getaddresses(tos + ccs + resent_tos + resent_ccs)
        for r in all_recipients:
            metas[cpage]["RECIPIENT"].add(r[1])
        reply_to = msg.get_all('reply-to', [])
        if reply_to:
            metas[cpage]["SENDER"].add(reply_to[0])
        msg_from = msg.get_all('from', []).pop()
        metas[cpage]["FROM"].add(msg_from)
        date = msg.get_all('date')
        metas[cpage]["DATE"] = date
    return new_metas

