import base64
from MoinMoin import config
from MoinMoin.Page import Page
from graphingwiki.editing import get_metas

SANDBOX_URL = "https://www.sandbox.paypal.com"
PRODUCTION_URL = "https://www.paypal.com"

TEMPLATE = """
<form action="%(paypal_url)s/cgi-bin/webscr" method="post">
<input type="hidden" name="cmd" value="_xclick">
<input type="hidden" name="business" value="%(business)s">
<input type="hidden" name="lc" value="US">
<input type="hidden" name="item_name" value="%(item_name)s">
<input type="hidden" name="amount" value="%(amount)s">
<input type="hidden" name="currency_code" value="%(currency_code)s">
<input type="hidden" name="no_note" value="1">
<input type="hidden" name="no_shipping" value="1">
<input type="hidden" name="custom" value="%(custom)s">
<input type="hidden" name="charset" value="%(charset)s">
<input type="hidden" name="return" value="%(return_page)s">
<input type="hidden" name="bn" value="PP-BuyNowBF:btn_buynowCC_LG.gif:NonHosted">
<input type="image" src="%(paypal_url)s/en_US/i/btn/btn_buynowCC_LG.gif" border="
0" name="submit" alt="">
<img alt="" border="0" src="%(paypal_url)s/en_US/i/scr/pixel.gif" width="1" heigh
t="1">
</form>
"""

CURRENCY = "EUR"
LABEL_KEY = "label"
RETURN_KEY = "Return page"
PRICE_KEY = "Price (%s)" % CURRENCY

def _get_meta_keys(request, page, *keys):
    result = list()
    metas = get_metas(request, page, keys)

    for key in keys:
        values = metas.get(key, list())
        if not values:
            raise ValueError("license page '%s' is not valid (no key '%s')" % (page, key))
        result.append(values[0])

    return result

def execute(macro, args):
    request = macro.request
    getText = request.getText

    if args is None or len(args.split(",")) < 2:
        return getText("not enough parameters")

    args = map(lambda x: x.strip(), args.split(","))
    business, licensePage = args[:2]

    additionals = dict()
    for value in args[2:]:
        keyAndValue = value.split("=")
        if len(keyAndValue) != 2:
            return getText("invalid argument: '%s'" % value)
        key, value = keyAndValue
        additionals[key.strip()] = value.strip()

    if additionals.get("sandbox", None) is not None:
        paypalUrl = SANDBOX_URL
    else:
        paypalUrl = PRODUCTION_URL

    userId = ""
    if request.user.valid:
        userId = request.user.id
    custom = "%s;%s" % tuple(map(base64.b64encode, (licensePage.encode("utf-8"), userId)))

    try:
        itemName, returnPage, amount = _get_meta_keys(request, licensePage, LABEL_KEY, RETURN_KEY, PRICE_KEY)
    except ValueError, ve:
        return getText(unicode(ve))

    returnPage = Page(request, returnPage).url(request)
    returnPage = request.getQualifiedURL(returnPage)

    keys = dict(paypal_url=paypalUrl,
                custom=custom,
                business=business,
                item_name=itemName,
                return_page=returnPage,
                amount=amount,
                charset=config.charset,
                currency_code=CURRENCY)

    return TEMPLATE % keys
