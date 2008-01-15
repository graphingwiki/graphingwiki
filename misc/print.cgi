#!/usr/bin/env python 

import cgi, os, re, urllib, sys
import cgitb; cgitb.enable()
from base64 import b64encode

baseurl = 'http://localhost/cgi-bin/print.cgi?proto='

# TODO
# - nicer structure
# - options for using other visualisers (neato, fdp, twopi, circo)
# - Maybe workaround IE like this:
#   http://www.lsc.ufsc.br/~luizd/base64-to-mhtml/workaround.html 

def sanitise_dict(dict):
    safechars = re.compile('[^a-zA-Z0-9,-]')
    # leaves only desired values, Warning: inplace modification!
    for key in dict.keys():
        newitems = []
        olditems = dict[key]
        dict[key] = newitems
        for item in olditems:
            val_item = safechars.sub('', item)
            newitems.append(val_item)
        val_key = safechars.sub('', key)
        if val_key != key:
            dict[val_key] = dict[key]
            del dict[key]

def grab_cmdline_from_cgi():
    cmdline = ""

    rawcgi = cgi.parse()
    sanitise_dict(rawcgi)
    url = urllib.urlencode(rawcgi, 'doseq')
    url = re.sub('(%2c)|(%2C)', ',', url)

    if len(url) > 0:
        for i in url.split('&'):
            cmdline += '--' + i + ' '

    return cmdline

#print "Content-type: text/plain\n\n"
#print grab_cmdline_from_cgi()
#form = cgi.FieldStorage()
#sys.exit(1)

cmdline = grab_cmdline_from_cgi()

r = os.popen("./drawdot.cgi " + cmdline)
dot = r.read()
stat = r.close()

if stat:
    print "Content-type: text/plain\n\n" + dot
    sys.exit(2)

w,r = os.popen2("dot -T cmap")
w.write(dot)
w.close()
mappi = r.read()
r.close()

w,r = os.popen2("dot -T png")
w.write(dot)
w.close()
img = r.read()
r.close()

# Amazing error handling
if not img:
    print "Content-Type: text/plain\n\nError forming graph\n";
    sys.exit(2)

imgbase = "data:image/png;base64," + b64encode(img)

#page = """Content-Type: multipart/related; boundary="bound"; type="text/html"
#
#--bound
page = """Content-Type: text/html

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
"http://www.w3.org/TR/1999/REC-html401-19991224/loose.dtd">

<html>
<body>

<img border=0 src=""" + '"' + imgbase + '"' + """ alt="visualisation" usemap="#G">

<map id="G" name="G">
""" + mappi + """
</map>

</body>
</html>
"""
# --bound
# Content-Location: image.png
# Content-Type: image/png
# Content-Transfer-Encoding: base64

# """ + imgbase + """
# --bound--
# """

print page
