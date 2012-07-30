import re
import os
import time
import xmlrpclib

from MoinMoin import config
from MoinMoin.Page import Page
from MoinMoin.PageEditor import PageEditor

from graphingwiki.editing import metatable_parseargs, get_metas
from graphingwiki.editing import set_metas

from MoinMoin.macro.spanner import Spanner

from M2Crypto import BIO, Rand, SMIME

CERT_BASE = "/etc/pki/tls/"

SECONDS_IN_DAY = 24 * 60 * 60

DEFAULTS = {
    "key": os.path.join(CERT_BASE, "private/example.key"),
    "cert": os.path.join(CERT_BASE, "certs/example.crt"),

    # Hardcode default minimum and maximum cookie length to a day and a month
    "min_ttl": 1,
    "max_ttl": 30,
    "default_duration": 365,

    "acls": "#acl %s:admin,read,write FacilitatorGroup:admin,revert,read,write All:none\n",

    "bookkeeping_page_template": """

----
CategoryBookkeeping"""
}

# Utility functions for bookkeeping

def ownPutPage(request, pagename, pagetext):
    if not request.user.may.write(pagename):
        return False

    page = PageEditor(request, pagename)
    try:
        msg = page.saveText(pagetext, 0)
    except page.SaveError, msg:
        pass

    page.getPageLinks(request)

    return True

def timeToString(x):
    return "<<DateTime(%d)>>" % x

def stringToTime(x):
    result = re.match("\<\<DateTime\(([0-9]+)\)\>\>", x)
    if result:
        return int(result.group(1))

    return 0

def logCookieRequest(request, cfg, username, (issued, expires, target), version):
    pagename = username + "/Bookkeeping"

    if cfg["acls"] and not request.user.may.admin(pagename):
        return xmlrpclib.Fault(1, "User is not allowed to admin bookkeeping page")

    bookkeepingPage = Page(request, pagename) 
    if not bookkeepingPage.exists():
        if cfg["acls"]:
            acls = cfg["acls"] % username
        else:
            acls = ""
        if ownPutPage(request, pagename, acls + cfg["bookkeeping_page_template"]) is False:
            return xmlrpclib.Fault(1, "User is not allowed to edit bookkeeping page")

    cleared = dict()
    metas = {target: ["%s %s" % (timeToString(issued), timeToString(expires))],
             "gwikicategory": ["CategoryBookkeeping"]}
    if version:
        metas["Version"] = [version]
        cleared[pagename] = ["Version"]

    result = set_metas(request, cleared, dict(), {pagename: metas})
    if isinstance(result, xmlrpclib.Fault):
        return xmlrpclib.Fault(1, "Failed to edit bookkeeping page: " + repr(result))

    return None 

def countUsage(request, page, key):
    metas = get_metas(request, page, [key], checkAccess=False)
    spans = Spanner()

    values = metas[key]
    for value in values:
        value = value.strip().split()
        if len(value) != 2:
            continue

        start, end = value
        start = stringToTime(start)
        end = stringToTime(end)
        if not (start and end):
            continue

        spans.addSpan(start, end)

    total = sum(map(lambda (start, end): end-start, spans))
    total /= float(60*60*24)
    return total

def countOwned(request, page, key):
    metas = get_metas(request, page, [key], checkAccess=False)
    total = 0

    values = metas[key]
    for value in values:
        value = value.strip().split()
        if len(value) != 2:
            continue

        ts, amount = value
        try:
            amount = int(amount)
        except ValueError:
            amount = 0

        total += amount

    return total

def getPurchases(request, page, key):
    metas = get_metas(request, page, [key], checkAccess=False)
    first = 2**32
    last = 0

    values = metas[key]
    if len(values) == 0:
        return 0, 0

    for value in values:
        value = value.strip()
        ts = stringToTime(value)

        first = min(first, ts)
        last = max(last, ts)

    return first, last

# Actual cookie creation code

def signCookie(cfg, input):
    buffer = BIO.MemoryBuffer(input)

    s = SMIME.SMIME()
    s.load_key(cfg["key"], cfg["cert"])
    p7 = s.sign(buffer)

    buffer = BIO.MemoryBuffer(input)

    out = BIO.MemoryBuffer()
    out2 = BIO.MemoryBuffer()
    p7.write(out2)
    s.write(out, p7, buffer)
    result = out.read()
    if not result.endswith('\n'):
        result += '\n'
    for line in result.split('\n'):
        if line.startswith('Content-Type'):
            boundary = line.split('boundary="')[1].rstrip('"')
            break
    content_type = """Content-Type: application/x-pkcs7-signature; name="smime.p7s"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="smime.p7s"
"""
    result += "--%s\n%s\n%s\n--%s--\n" % (boundary, content_type, 
                                          out2.read(), boundary)

    return xmlrpclib.Binary(result)

def createCookieString(values):
    lines = list()
    for key, value in values.iteritems():
        lines.append(" %s:: %s" % (key, value))
    cookie = "\n".join(lines)
    return cookie.encode("iso-8859-1")

def getIntMeta(metas, key, default):
    value = metas.get(key)
    if value:
        try:
            value = int(value[0])
        except ValueError:
            value = default
    else:
        value = default

    return value

def reformatMetaDict(metas):
    output = dict()
    for key, values in metas.iteritems():
        key = key
        value = ", ".join(values)
        output[key] = value

    return output

def execute(xmlrpcobj, page, ttl=None, version=""):
    request = xmlrpcobj.request

    cfg = dict()
    for key, value in DEFAULTS.iteritems():
        cfg[key] = getattr(request.cfg, "cookie_" + key, value)

    if ttl is None:
        ttl = cfg["min_ttl"] * SECONDS_IN_DAY

    # Check if user has right to read page
    if not request.user.may.read(page):
        return xmlrpclib.Fault(1, "You are not allowed get this license.")

    # Encode the pagename and username properly (?)
    username = request.user.name
    pagename = page

    if not username:
        return xmlrpclib.Fault(1, "Unknown user")

    pagelist, metakeys, _ = metatable_parseargs(request, page, get_all_keys=True)
    metas = get_metas(request, page, metakeys, checkAccess=False)

    typeValue = metas.get("Type", [])
    if len(typeValue) == 0:
        licenseType = "cookie"
    else:
        licenseType = typeValue[0]

    if licenseType == "capped":
        usedCookies = countUsage(request, username + "/Bookkeeping", page)
        ownedCookies = countOwned(request, username + "/Shopkeeping", page)
        availableCookies = ownedCookies - usedCookies

    minTTL = getIntMeta(metas, "Minimum check-out period (days)", cfg["min_ttl"])
    maxTTL = getIntMeta(metas, "Maximum check-out period (days)", cfg["max_ttl"])

    minTTL *= SECONDS_IN_DAY
    maxTTL *= SECONDS_IN_DAY

    # Cap the cookie ttl between minTTL and maxTTL
    ttl = min(max(ttl, minTTL), maxTTL)

    if licenseType == "capped":
        ttl = min(ttl, availableCookies * SECONDS_IN_DAY)
        availableCookies -= ttl / SECONDS_IN_DAY

    if ttl <= 0:
        return xmlrpclib.Fault(1, "You don't have any cookies left!")

    if licenseType == "traditional":
        first, last = getPurchases(request, username + "/Shopkeeping", page)
        if first == 0 and last == 0:
            return xmlrpclib.Fault(1, "No purchased licenses found!")

        duration = getIntMeta(metas, "Duration (days)", cfg["default_duration"])
        issued = first
        expires = last + duration * SECONDS_IN_DAY
    else:
        # Start and end times for the cookie
        issued = int(time.time())
        expires = issued + ttl

    cookieData = reformatMetaDict(metas)
    cookieData["collabname"] = request.cfg.interwikiname
    cookieData["pagename"] = pagename
    cookieData["username"] = username
    cookieData["issued"] = int(issued)
    cookieData["expires"] = int(expires)

    if licenseType == "capped":
        cookieData["availableCookies"] = "%.02f" % availableCookies

    cookie = createCookieString(cookieData)

    failure = logCookieRequest(request, cfg, username, (issued, expires, pagename), version)
    if failure:
        return failure 
    
    return signCookie(cfg, cookie)
