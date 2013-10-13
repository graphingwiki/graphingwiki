# -*- coding: utf-8 -*-"
"""
    ioclist action plugin to MoinMoin/Graphingwiki
     - Make a wiki page with metas on indicators of compromise
     - Currently supports IPv4 and IPv6 addresses

    @copyright: 2013 by Juhani Eronen <exec@iki.fi>
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

from MoinMoin.Page import Page
from MoinMoin.action import do_show

from graphingwiki import values_to_form
from graphingwiki.editing import edit_meta, save_template

import re
import socket as _socket

IPV4_RE = re.compile('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')

# Regexp from http://forums.intermapper.com/viewtopic.php?t=452
# Tested against https://bitbucket.org/intermapper/ipv6-validator/
IPV6_RE = re.compile("(?<![\w:\.])((?:(?:(?:[0-9A-Fa-f]{1,4}:){7}(?:[0-9A-Fa-f]{1,4}|:))|(?:(?:[0-9A-Fa-f]{1,4}:){6}(?::[0-9A-Fa-f]{1,4}|(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(?:(?:[0-9A-Fa-f]{1,4}:){5}(?:(?:(?::[0-9A-Fa-f]{1,4}){1,2})|:(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(?:(?:[0-9A-Fa-f]{1,4}:){4}(?:(?:(?::[0-9A-Fa-f]{1,4}){1,3})|(?:(?::[0-9A-Fa-f]{1,4})?:(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(?:(?:[0-9A-Fa-f]{1,4}:){3}(?:(?:(?::[0-9A-Fa-f]{1,4}){1,4})|(?:(?::[0-9A-Fa-f]{1,4}){0,2}:(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(?:(?:[0-9A-Fa-f]{1,4}:){2}(?:(?:(?::[0-9A-Fa-f]{1,4}){1,5})|(?:(?::[0-9A-Fa-f]{1,4}){0,3}:(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(?:(?:[0-9A-Fa-f]{1,4}:){1}(?:(?:(?::[0-9A-Fa-f]{1,4}){1,6})|(?:(?::[0-9A-Fa-f]{1,4}){0,4}:(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(?::(?:(?:(?::[0-9A-Fa-f]{1,4}){1,7})|(?:(?::[0-9A-Fa-f]{1,4}){0,5}:(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(?:%.+)?)(?![\w:\.])")

def is_ipv4(ip):
    try:
        _socket.inet_aton(ip)
    except (ValueError, _socket.error):
        return False
    return True

def is_ipv6(ip):
    try:
        _socket.inet_pton(_socket.AF_INET6, ip)
    except (ValueError, _socket.error):
        return False
    return True
    
def execute(pagename, request):
    _ = request.getText
    form = values_to_form(request.values)
    msgs = list()

    newpage = form['name'][0]
    if not newpage:
        request.theme.add_msg(_("IOCList page name not set!"), 'error')
        request.page.send_page()
        return
    template = form['template'][0]
    if not template:
        template = "IOCListTemplate"
    allow_overlap = form['allow_overlap'][0]
    if not allow_overlap:
        allow_overlap = "no"
    
    ips = IPV4_RE.findall(form['ips'][0])
    ips = filter(is_ipv4, ips)
    ips = set(ips)

    ipv6 = IPV6_RE.findall(form['ips'][0])
    ipv6 = filter(is_ipv6, ipv6)
    ips.update(set(ipv6))

    graphdata = request.graphdata
    vals_on_keys = graphdata.get_vals_on_keys()

    new_ips = list()
    for ip in ips:
        if ip not in vals_on_keys.get('ip', list()):
           new_ips.append(ip)

    old_ips = ', '.join(ips.difference(new_ips))
    if old_ips:
        if allow_overlap == 'no':
            msgs.append(_("The following IOC already listed: %s.") % 
                        old_ips)
        else:
            msgs.append(
                _("The following IOC already listed: %s. Adding anyway.")%
                old_ips)

    if allow_overlap != 'no':
        new_ips = ips

    if not new_ips:
        request.theme.add_msg(_("No new IOC!"), 'error')
        request.page.send_page()
        return

    if not Page(request, newpage).exists():
        msgs.append(_("Creating page %r with template %r") % 
                              (newpage, template))
        msgs.append(save_template(request, newpage, template))

    msgs.append(_("Added %s IOC") % (len(new_ips)))

    edit_meta(request, newpage, {}, {'ip': list(new_ips)})
    msg = ''
    for line in msgs:
        msg += line + request.formatter.linebreak(0)

    request.theme.add_msg(msg)
    do_show(pagename, request)
