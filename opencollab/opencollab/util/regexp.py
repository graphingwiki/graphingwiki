# -*- coding: utf-8 -*-

import os
import sys
import csv
import re
from time import gmtime, strftime, time
import md5

tld = ["ac", "ad", "ae", "af", "ag", "ai", "al", "am", "an", "ao",
"aq", "ar", "as", "at", "au", "aw", "az", "ax", "ba", "bb", "bd",
"be", "bf", "bg", "bh", "bi", "bj", "bm", "bn", "bo", "br", "bs",
"bt", "bv", "bw", "by", "bz", "ca", "cc", "cd", "cf", "cg", "ch",
"ci", "ck", "cl", "cm", "cn", "co", "cr", "cs", "cu", "cv", "cx",
"cy", "cz", "de", "dj", "dk", "dm", "do", "dz", "ec", "ee", "eg",
"eh", "er", "es", "et", "eu", "fi", "fj", "fk", "fm", "fo", "fr",
"ga", "gb", "gd", "ge", "gf", "gg", "gh", "gi", "gl", "gm", "gn",
"gp", "gq", "gr", "gs", "gt", "gu", "gw", "gy", "hk", "hm", "hn",
"hr", "ht", "hu", "id", "ie", "il", "im", "in", "io", "iq", "ir",
"is", "it", "je", "jm", "jo", "jp", "ke", "kg", "kh", "ki", "km",
"kn", "kp", "kr", "kw", "ky", "kz", "la", "lb", "lc", "li", "lk",
"lr", "ls", "lt", "lu", "lv", "ly", "ma", "mc", "md", "mg", "mh",
"mk", "ml", "mm", "mn", "mo", "mp", "mq", "mr", "ms", "mt", "mu",
"mv", "mw", "mx", "my", "mz", "na", "nc", "ne", "nf", "ng", "ni",
"nl", "no", "np", "nr", "nu", "nz", "om", "pa", "pe", "pf", "pg",
"ph", "pk", "pl", "pm", "pn", "pr", "ps", "pt", "pw", "py", "qa",
"re", "ro", "ru", "rw", "sa", "sb", "sc", "sd", "se", "sg", "sh",
"si", "sj", "sk", "sl", "sm", "sn", "so", "sr", "st", "sv", "sy",
"sz", "tc", "td", "tf", "tg", "th", "tj", "tk", "tl", "tm", "tn",
"to", "tp", "tr", "tt", "tv", "tw", "tz", "ua", "ug", "uk", "um",
"us", "uy", "uz", "va", "vc", "ve", "vg", "vi", "vn", "vu", "wf",
"ws", "ye", "yt", "yu", "za", "zm", "zw", "aero", "biz", "cat", "com",
"coop", "info", "jobs", "mobi", "museum", "name", "net", "org", "pro",
"travel", "gov", "edu", "mil", "int"]

## Regular expressions

# This regexp is supposed to cover handles...
# No : in parentheses to avoid times to be grasped
handle_re  = re.compile(r'(?:\(|\w+Handle:\s+)([^\s:)]+\-[^\s:)]+)')

mail_re    = re.compile('([\w\-.%]+@(?:[\w\-%]+\.)+[\w\-%]+)', re.S)
maildom_re = re.compile('(@(?:[\w\-%]+\.)+[\w\-%]+)', re.S)
           
# Anything they have used for http://
scheme_re = r'(?:[a-zA-Z][\w ]*?)?'
hier_re = r'\:\s*/\s*/\s*'
begin_re = scheme_re + hier_re
passwd_re = r'(?:\w+\:\w+@)?'
# Anything they have used for . in domain names
dot_re = r'(?:\.|[\[<]dot[\]>])'
# End part of domain name: either valid tld or number
tld_re = '\s*(?:' + '|'.join(tld) + '|\d+)'
site_re = '(?:[\w\- ]+' + dot_re + ')+(?:' + tld_re +  ')?'
# Numeric port
port_re = r'(?:\:\d+)?'
# uri ends with /, ) or space
enduri_re = '[/)\s]'
allend_re = '/[^\s]*'

# URL is begin + domain [+ port +] + endpart
url_site_re = re.compile('%s%s(%s)%s%s' % (begin_re,passwd_re, site_re,
                                           port_re, enduri_re))
url_all_re = re.compile('(%s)(%s)(%s)(%s)(%s)(%s)?' % \
                        (scheme_re, hier_re, passwd_re,
                         site_re, port_re, allend_re))

dns_re = re.compile("^([\w\-]+(?:\.[\w\-]+)+)", re.M)

dig_start_re = re.compile('^([^\s]+)')
dig_end_re = re.compile('([^\s]+)$')
# Gets soa data (name-server email-addr sn ref ret ex min)
dig_soaref_re = re.compile("([\w\-\.]+)\s([/\w\-\.\\\@]+)" + \
                           "\s(\d+)(?:\sSerial)?\s(\d+)" +\
                           "(?:\sRefresh)?\s" +\
                           "(\d+)(?:\sRetry)?\s(\d+)" +\
                           "(?:\sExpire)?\s" +\
                           "(\d+)(?:\sMinimum)?$", re.I)
dig_ttl_re = re.compile("\.\s+(\d+)\s+")

ts_string = "%a, %d %b %Y %H:%M:%S +0000"

def utctimestamp(ts=None):
    return strftime(ts_string, gmtime(ts))

def utcepoch():
    return time()

def get_filetype(file):
    if os.path.isfile(file):
        return os.popen('file -b %s' % file).readlines()[0].rstrip()

def md5_digest(data):
    return md5.new(data).hexdigest()

## Charset conversions

def conv_win_uni(str):
    return unicode(str, 'cp1252')
