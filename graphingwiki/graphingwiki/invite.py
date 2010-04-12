import string
import random
import re

from MoinMoin import user
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.mail.sendmail import encodeAddress

from graphingwiki.editing import parse_categories

class InviteException(Exception):
    pass

def user_may_invite(myuser, page):
    if not hasattr(myuser.may, "invite"):
        return False
    return myuser.may.read(page) and myuser.may.invite(page)

def check_inviting_enabled(request):
    return
    if not hasattr(request.user.may, "invite"):
        raise InviteException("No invite permissions configured.")
    if not hasattr(request.cfg, "mail_from"):
        raise InviteException("No admin email address configured.")
    if not hasattr(request.cfg, "invite_sender_default_domain"):
        raise InviteException("No invite sender default domain configured.")
    ## FIXME: Disabled sendmail support for now.
    # if getattr(request.cfg, "mail_sendmail", None):
    #     return
    if getattr(request.cfg, "mail_smarthost", None):
        return
    raise InviteException("No outgoing mail service configured.")

def generate_password(length=8):
    characters = string.letters + string.digits
    return u"".join([random.choice(characters) for _ in range(length)])

class GroupException(Exception):
    pass

def add_user_to_group(request, myuser, group, create_link=True, comment=""):
    if not wikiutil.isGroupPage(request, group):
        raise GroupException("Page '%s' is not a group page." % group)
    if not (request.user.may.read(group) and request.user.may.write(group)):
        raise GroupException("No permissions to write to page '%s'." % group)

    member_rex = re.compile(ur"^ \* +(?:\[\[)?(.+?)(?:\]\])? *$", re.UNICODE)
    page = PageEditor(request, group)
    text = page.get_raw_body()

    _, head, tail = parse_categories(request, text)

    insertion_point = len(head)
    for lineno, line in enumerate(head):
        match = member_rex.match(line)
        if not match:
            continue

        if match.group(1).lower() == myuser.name.lower():
            return

        insertion_point = lineno + 1

    if create_link:
        template = " * [[%s]]"
    else:
        template = " * %s"
    head.insert(insertion_point, template % myuser.name)

    text = "\n".join(head + tail)

    if comment:
        page.saveText(text, 0, comment=comment)
    else
        page.saveText(text, 0)

def invite_user_to_wiki(request, page, email, new_template, old_template, **custom_vars):
    check_inviting_enabled(request)
    if not user_may_invite(request.user, page):
        raise InviteException("No permissions to invite from '%s'." % page)

    page_url = request.getBaseURL()    
    return _invite(request, page_url, email, new_template, old_template, **custom_vars)

def invite_user_to_page(request, page, email, new_template, old_template, **custom_vars):
    check_inviting_enabled(request)
    if not user_may_invite(request.user, page):
        raise InviteException("No permissions to invite from '%s'." % page)

    page_url = Page(request, page).url(request, relative=False)
    page_url = request.getQualifiedURL(page_url)
    return _invite(request, page_url, email, new_template, old_template, **custom_vars)

def _invite(request, page_url, email, new_template, old_template, **custom_vars):
    mail_from = request.user.email
    if "@" not in mail_from:
        mail_from += "@" + request.cfg.invite_sender_default_domain

    variables = dict(custom_vars)
    variables.update(PAGEURL=page_url,
                     ADMINEMAIL=request.cfg.mail_from,
                     INVITERUSER=request.user.name,
                     INVITEREMAIL=mail_from)
    
    old_user = user.get_by_email_address(request, email)
    if old_user:
        variables.update(INVITEDUSER=old_user.name,
                         INVITEDEMAIL=old_user.email)
        sendmail(request, old_template, variables)
        return old_user

    if not user.isValidName(request, email):
        raise InviteException("Can not create a new user, '%s' is not a valid username." % email)

    password = generate_password()        
    new_user = user.User(request, None, email, password)
    new_user.email = email
    new_user.aliasname = ""
    new_user.password = password

    variables.update(INVITEDUSER=new_user.name,
                     INVITEDEMAIL=new_user.email,
                     INVITEDPASSWORD=password)        
    sendmail(request, new_template, variables, lambda x: x.lower() == email.lower())

    variables.update(INVITEDPASSWORD="******")
    sendmail(request, new_template, variables, lambda x: x.lower() != email.lower())
        
    new_user.save()
    return new_user

def replace_variables(text, variables):
    text = text.encode("utf-8")
    for name, variable in variables.iteritems():
        variable = unicode(variable).encode("utf-8")
        name = unicode(name).encode("utf-8")
        text = re.sub("@%s@" % name, variable, text)
    text = text.decode("utf-8")
    return text

def encode_address_field(message, key, charset):
    all_values = message.get_all(key, list())
    all_values = [encodeAddress(value, charset) for value in all_values]

    del message[key]

    for value in all_values:
        message[key] = value

def sendmail(request, template, variables, recipient_filter=lambda x: True):
    # Lifted and varied from Moin 1.6 code.

    import os, smtplib, socket
    from email import message_from_string
    from email.Message import Message
    from email.Charset import Charset, QP
    from email.Utils import formatdate, make_msgid, getaddresses

    DEFAULT_HEADERS = dict()
    DEFAULT_HEADERS["To"] = "@INVITEDEMAIL@"
    DEFAULT_HEADERS["From"] = "@INVITEREMAIL@"

    ENCODING = "utf-8"

    template = u"\r\n".join(template.splitlines())
    template = replace_variables(template, variables)
    template = template.encode(ENCODING)
    message = message_from_string(template)

    for key, value in DEFAULT_HEADERS.iteritems():
        # Headers must be unicode for encode_address_field. Must both
        # delete and set, see __setitem__ in 7.1.1 of the Python
        # library docs
        if key in message:
            msgval = message[key]
            del message[key]
            message[key] = msgval.decode('utf-8')
            continue

        message[key] = replace_variables(value, variables)

    charset = Charset(ENCODING)
    charset.header_encoding = QP
    charset.body_encoding = QP
    message.set_charset(charset)

    ## Moin does this: work around a bug in python 2.4.3 and above.
    ## Should we do this too?
    # payload = message.get_payload()
    # message.set_payload('=')
    # if message.as_string().endswith('='):
    #     payload = charset.body_encode(payload)
    # message.set_payload(payload)

    encode_address_field(message, "From", charset)
    encode_address_field(message, "To", charset)
    encode_address_field(message, "CC", charset)
    encode_address_field(message, "BCC", charset)
    message['Date'] = formatdate()
    message['Message-ID'] = make_msgid()

    ## FIXME: Disabled sendmail support for now.
    # if request.cfg.mail_sendmail:
    #     try:
    #         pipe = os.popen(request.cfg.mail_sendmail, "w")
    #         pipe.write(message.as_string())
    #         status = pipe.close()
    #     except:
    #         raise InviteException("Mail not sent.")
    # 
    #     if status:
    #         raise InviteException("Sendmail returned status '%d'." % status)
    #     return

    try:
        host, port = (request.cfg.mail_smarthost + ":25").split(":")[:2]
        server = smtplib.SMTP(host, int(port))
        try:
            server.ehlo()

            if request.cfg.mail_login:
                user, pwd = request.cfg.mail_login.split()
                try: # try to do tls
                    if server.has_extn('starttls'):
                        server.starttls()
                        server.ehlo()
                except:
                    pass
                server.login(user, pwd)

            mail_from = message["From"]
            mail_to = message.get_all("To", list()) + message.get_all("Cc", list()) + message.get_all("Bcc", list())
            mail_to = [address for (name, address) in getaddresses(mail_to)]
            mail_to = filter(recipient_filter, mail_to)
            mail_to = list(set(mail_to))
            if mail_to:
                server.sendmail(mail_from, mail_to, message.as_string())
        finally:
            try:
                server.quit()
            except AttributeError:
                # in case the connection failed, SMTP has no "sock" attribute
                pass
    except smtplib.SMTPException, e:
        raise InviteException("Mail not sent: %s." % str(e))
    except (os.error, socket.error), e:
        tmp = "Connection to mailserver '%(server)s' failed: %(reason)s."
        vars = dict(server=request.cfg.mail_smarthost, reason=str(e))
        raise InviteException(tmp % vars)
