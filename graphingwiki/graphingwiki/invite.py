# A module for inviting (new or existing) users to a wiki page by
# email and adding the user to a group.
# The email preparation and sending code of the original version of
# the graphingwiki.invite module contained modified parts from the
# MoinMoin 1.6 module MoinMoin.mail.sendmail.

import re
import string
import smtplib
from random import SystemRandom
from email import message_from_string
from email.Charset import Charset, QP
from email.Utils import getaddresses

from MoinMoin import user
from MoinMoin import wikiutil
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor
from MoinMoin.mail.sendmail import encodeAddress

from MoinMoin import log
logging = log.getLogger(__name__)

from graphingwiki.editing import parse_categories

class InviteException(Exception):
    pass

def user_may_invite(userobj, page):
    if not hasattr(userobj.may, "invite"):
        return False
    return userobj.may.read(page) and userobj.may.invite(page)

def check_inviting_enabled(request):
    if not hasattr(request.user.may, "invite"):
        raise InviteException("No invite permissions configured.")
    if not hasattr(request.cfg, "mail_from"):
        raise InviteException("No admin email address configured.")
    if not hasattr(request.cfg, "invite_sender_default_domain"):
        raise InviteException("No invite sender default domain configured.")
    if not getattr(request.cfg, "mail_smarthost", None):
        raise InviteException("No outgoing mail service configured.")

def generate_password(length=10):
    characters = string.letters + string.digits
    return u"".join([SystemRandom().choice(characters) for _ in range(length)])

class GroupException(Exception):
    pass

def add_user_to_group(request, userobj, group, create_link=True, comment=""):
    if not wikiutil.isGroupPage(group, request.cfg):
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

        if match.group(1).lower() == userobj.name.lower():
            return

        insertion_point = lineno + 1

    if create_link:
        template = " * [[%s]]"
    else:
        template = " * %s"
    head.insert(insertion_point, template % userobj.name)

    text = "\n".join(head + tail)
    page.saveText(text, 0, comment=comment)

    logging.info("%s added to group %s in wiki %s (invited by %s)" %
                 (userobj.name, group, request.cfg.interwikiname,
                  request.user.name))

def invite_user_to_wiki(request, page, email, new_template, old_template,
                        **custom_vars):
    check_inviting_enabled(request)
    if not user_may_invite(request.user, page):
        raise InviteException("No permissions to invite from '%s'." % page)

    page_url = request.getBaseURL()
    return _invite(request, page_url, email, new_template, old_template,
                   **custom_vars)

def invite_user_to_page(request, page, email, new_template, old_template,
                        **custom_vars):
    check_inviting_enabled(request)
    if not user_may_invite(request.user, page):
        raise InviteException("No permissions to invite from '%s'." % page)

    page_url = Page(request, page).url(request, relative=False)
    page_url = request.getQualifiedURL(page_url)
    return _invite(request, page_url, email, new_template, old_template,
                   **custom_vars)

def _invite(request, page_url, email, new_template, old_template,
            **custom_vars):
    mail_from = request.user.email
    if "@" not in mail_from:
        mail_from += "@" + request.cfg.invite_sender_default_domain

    variables = dict(custom_vars)
    variables.update(PAGEURL=page_url,
                     ADMINEMAIL=request.cfg.mail_from,
                     INVITERUSER=request.user.name,
                     INVITEREMAIL=mail_from,
                     SERVERURL=request.host_url)

    old_user = user.get_by_email_address(request, email)
    if old_user:
        variables.update(INVITEDUSER=old_user.name,
                         INVITEDEMAIL=old_user.email)
        send_message(request, prepare_message(old_template, variables))
        return old_user

    if not user.isValidName(request, email):
        raise InviteException("'%s' is not a valid username." % email)

    password = generate_password()
    new_user = user.User(request, None, email, password)
    new_user.email = email
    new_user.aliasname = ""
    new_user.password = password

    variables.update(INVITEDUSER=new_user.name,
                     INVITEDEMAIL=new_user.email,
                     INVITEDPASSWORD=password)
    send_message(request, prepare_message(new_template, variables),
                 lambda x: x.lower() == email.lower())

    variables.update(INVITEDPASSWORD="******")
    send_message(request, prepare_message(new_template, variables),
                 lambda x: x.lower() != email.lower())

    new_user.save()

    logging.info("New user %s added to wiki %s (invited by %s)" %
                 (new_user.name, request.cfg.interwikiname,
                  request.user.name))

    return new_user

def replace_variables(text, variables):
    for name, variable in variables.iteritems():
        text = re.sub("@%s@" % name, variable, text)
    return text

def encode_address_field(message, key, encoding, charset):
    values = message.get_all(key, list())
    del message[key]

    for value in values:
        # encodeAddress expects unicode objects
        if not isinstance(value, unicode):
            value = value.decode(encoding)
        message[key] = encodeAddress(value, charset)

def prepare_message(template, variables, encoding="utf-8"):
    r"""Return a prepared email.Message object.

    >>> template = (u"Subject: @SUBJECT@\n"+
    ...             u"From: @FROM@\n"+
    ...             u"To: @TO@\n"+
    ...             u"BCC: @FROM@\n\n"+
    ...             u"Hello, @GREETED@!")
    >>> variables = dict(SUBJECT="Test",
    ...                  FROM="from@example.com",
    ...                  TO="to@example.com",
    ...                  GREETED="World")
    >>> message = prepare_message(template, variables)
    >>> message["SUBJECT"] == variables["SUBJECT"]
    True
    >>> message["TO"] == variables["TO"]
    True
    >>> message["FROM"] == message["BCC"] == variables["FROM"]
    True
    >>> message.get_payload()
    'Hello, World!'
    """

    template = u"\r\n".join(template.splitlines())
    template = replace_variables(template, variables)
    template = template.encode(encoding)
    message = message_from_string(template)

    DEFAULT_HEADERS = { "to": "@INVITEDEMAIL@", "from": "@INVITEREMAIL@" }
    for key, value in DEFAULT_HEADERS.iteritems():
        if key not in message:
            value = replace_variables(value, variables)
            if isinstance(value, unicode):
                value = value.encode(encoding)
            message[key] = value

    charset = Charset(encoding)
    charset.header_encoding = QP
    charset.body_encoding = QP
    message.set_charset(charset)

    encode_address_field(message, "from", encoding, charset)
    encode_address_field(message, "to", encoding, charset)
    encode_address_field(message, "cc", encoding, charset)
    encode_address_field(message, "bcc", encoding, charset)
    return message

def send_message(request, message, recipient_filter=lambda x: True):
    sender = message["from"]
    recipients = set()
    for field in ["to", "cc", "bcc"]:
        values = message.get_all(field, [])
        for _, address in getaddresses(values):
            if recipient_filter(address):
                recipients.add(address)

    smtp = smtplib.SMTP()
    try:
        try:
            smtp.connect(request.cfg.mail_smarthost)
            smtp.ehlo()

            try:
                smtp.starttls()
            except smtplib.SMTPException:
                pass
            else:
                smtp.ehlo()

            try:
                smtp.sendmail(sender, recipients, message.as_string())
                for recipient in recipients:
                    logging.info("%s invited %s to wiki %s" %
                                 (sender, recipients,
                                  request.cfg.interwikiname))
            except smtplib.SMTPSenderRefused, error:
                if not getattr(request.cfg, "mail_login", None):
                    raise error
                smtp.login(*request.cfg.mail_login.split(" ", 1))
                smtp.sendmail(sender, recipients, message.as_string())
        except Exception, exc:
            raise InviteException("Could not send the mail: %r" % exc)
    finally:
        try:
            smtp.quit()
        except Exception:
            pass

if __name__ == "__main__":
    import doctest
    doctest.testmod()
