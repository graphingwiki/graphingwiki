import time
import calendar
import base64
import xmlrpclib

from MoinMoin.user import User
from MoinMoin.Page import Page
from graphingwiki.editing import set_metas, get_metas
from graphingwiki.invite import invite_user_to_wiki, add_user_to_group, InviteException, GroupException

CURRENCY = "EUR"
PRICE_KEY = "Price (%s)" % CURRENCY
GROUP_KEY = "Group page"
NEW_TEMPLATE_KEY = "Invite new template"
OLD_TEMPLATE_KEY = "Invite old template"

def _load_template(request, name):
    if not request.user.may.read(name):
        raise InviteException("You are not allowed to read template page '%s'." % name)

    page = Page(request, name)
    if not page.exists():
        raise InviteException("Template page '%s' does not exist." % name)

    return page.get_raw_body()

def _get_meta_keys(request, page, *keys):
    result = list()
    metas = get_metas(request, page, keys)

    for key in keys:
        values = metas.get(key, list())
        if not values:
            raise ValueError("license page '%s' is not valid (no key '%s')" % (page, key))
        result.append(values[0])

    return result

def execute(xmlrpcobj, fields):
    assert "custom" in fields
    assert "mc_gross" in fields
    assert "tax" in fields
    assert "shipping" in fields
    assert "mc_currency" in fields

    request = xmlrpcobj.request
    timestamp = int(calendar.timegm(time.gmtime()))

    custom = map(base64.b64decode, fields.get("custom", "").split(";"))
    if len(custom) != 2:
        raise ValueError("invalid custom field (%s)" % custom)
        
    licensePage, userId = custom
    licensePage.decode("utf-8")
    if not userId:
        email = fields["payer_email"]
    else:
        user = User(request, userId)
        email = user.email
    assert email

    currency_code = fields.get("mc_currency", None)
    if currency_code != CURRENCY:
        raise ValueError("invalid currency code (%s)" % currency_code)
        
    mc_gross = float(fields.get("mc_gross", "0.00"))
    tax = float(fields.get("tax", "0.00"))
    shipping = float(fields.get("shipping", "0.00"))

    required_amount, group_page, new_template_page, old_template_page = _get_meta_keys(request, licensePage, PRICE_KEY, GROUP_KEY, NEW_TEMPLATE_KEY, OLD_TEMPLATE_KEY)
    try:
        required_amount = float(required_amount)
    except ValueError:
        raise ValueError("license page %s is not valid (price not a number)" % licensePage)
    if ("%.02f" % required_amount) != ("%.02f" % (mc_gross - tax - shipping)):
        raise ValueError("invalid amount (%.02f total - %.02f tax - %.02f shipping = %.02f, expected %.02f)" % (mc_gross, tax, shipping, mc_gross - tax - shipping, required_amount))

    download_url = Page(request, licensePage).url(request, querystr="action=GetCookie", relative=False)
    download_url = request.getQualifiedURL(download_url)
    try:
        new_template = _load_template(request, new_template_page)
        old_template = _load_template(request, old_template_page)
        user = invite_user_to_wiki(request, group_page, email, new_template, old_template, DOWNLOADURL=download_url)
    except InviteException, ie:
        return xmlrpclib.Fault(1, unicode(ie))
    try:
        add_user_to_group(request, user, group_page)
    except GroupException, ge:
        return xmlrpclib.Fault(2, unicode(ge))

    shopPage = "%s/Shopkeeping" % user.name
    added = dict()
    added[shopPage] = dict()
    added[shopPage][licensePage] = ["<<DateTime(%d)>>" % timestamp]
    added[shopPage]["gwikicategory"] = ["CategoryShopkeeping"]
    added[shopPage]["gwikitemplate"] = ["ShopkeepingTemplate"]

    success, message = set_metas(request, dict(), dict(), added)
    if not success:
        return xmlrpclib.Fault(3, message)
