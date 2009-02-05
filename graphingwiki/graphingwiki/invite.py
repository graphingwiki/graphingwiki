import string
import random
import re

from MoinMoin import user
from MoinMoin.Page import Page
from MoinMoin.mail.sendmail import encodeAddress
from MoinMoin import config

class InviteException(Exception):
    pass

class AmbiguousInvite(InviteException):
    def __init__(self, found):
        message = "Found several possible users to invite." % len(found)
        super(AmbiguousInvite, self).__init__(message)
        self.found = found

def user_may_invite(myuser, page):
    if not hasattr(myuser.may, "invite"):
        return False
    return myuser.may.read(page) and myuser.may.invite(page)

def check_inviting_enabled(request):
    if not hasattr(request.user.may, "invite"):
        raise InviteException("No invite permissions configured.")
    if not hasattr(request.cfg, "mail_from"):
        raise InviteException("No admin email address configured.")
    if not hasattr(request.cfg, "invite_sender_default_domain"):
        raise InviteException("No invite sender default domain configured.")
    if getattr(request.cfg, "mail_sendmail", None):
        return
    if getattr(request.cfg, "mail_smarthost", None):
        return
    raise InviteException("No outgoing mail service configured.")

def generate_password(length=8):
    characters = string.letters + string.digits
    return u"".join([random.choice(characters) for _ in range(length)])

def find_users_by_email(request, email):
    email = email.lower()
    found = list()

    for uid in user.getUserList(request):
        myuser = user.User(request, uid)
        myuser.load_from_id()
        if not (myuser.valid and user.isValidName(request, myuser.name)):
            continue

        if email == myuser.email.lower():
            found.append(myuser)

    return found

def invite_user_by_email(request, page, email, new_template, old_template, 
                         **extra_variables):
    check_inviting_enabled(request)

    if not user_may_invite(request.user, page):
        raise InviteException("No permissions to invite to page '%s'." % page)

    page_url = Page(request, page).url(request)
    page_url = request.getQualifiedURL(page_url)

    mail_from = request.user.name
    if "@" not in mail_from:
        mail_from += "@" + request.cfg.invite_sender_default_domain

    variables = dict(extra_variables)
    variables.update(PAGENAME=page, 
                     PAGEURL=page_url,
                     ADMINEMAIL=request.cfg.mail_from,
                     INVITERUSER=request.user.name,
                     INVITEREMAIL=mail_from)

    found = find_users_by_email(request, email)
    if len(found) > 1:
        raise AmbiguousInvite(found)

    if found:
        old_user = found[0]
        variables.update(INVITEDUSER=old_user.name,
                         INVITEDEMAIL=old_user.email)
        sendmail(request, old_template, variables)
    else:
        password = generate_password()        

        # FIXME: should we do "if user.isValidName(email)"?
        new_user = user.User(request, None, email, password)
        new_user.email = email
        new_user.aliasname = ""
        new_user.password = password

        variables.update(INVITEDUSER=new_user.name,
                         INVITEDEMAIL=new_user.email,
                         INVITEDPASSWORD=password)        
        sendmail(request, new_template, variables)
        
        new_user.save()

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

def sendmail(request, template, variables):
    import os, smtplib, socket
    from email import message_from_string
    from email.Message import Message
    from email.Charset import Charset, QP
    from email.Utils import formatdate, make_msgid

    DEFAULT_HEADERS = dict()
    DEFAULT_HEADERS["To"] = "@INVITEDEMAIL@"
    DEFAULT_HEADERS["From"] = "@INVITEREMAIL@"

    ENCODING = "utf-8"

    template = u"\r\n".join(template.splitlines())
    template = replace_variables(template, variables)
    template = template.encode(ENCODING)
    message = message_from_string(template)

    for key, value in DEFAULT_HEADERS.iteritems():
        if key in message:
            continue
        message[key] = replace_variables(value, variables)

    charset = Charset(ENCODING)
    charset.header_encoding = QP
    charset.body_encoding = QP
    message.set_charset(charset)

    ## Moin does this: work around a bug in python 2.4.3 and above.
    ## Should we do too?
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

    if request.cfg.mail_sendmail:
        try:
            pipe = os.popen(request.cfg.mail_sendmail, "w")
            pipe.write(message.as_string())
            status = pipe.close()
        except:
            raise InviteException("Mail not sent.")

        if status:
            raise InviteException("Sendmail returned status '%d'." % status)
        return

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
            mail_to = message["To"]
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