# -*- coding: utf-8 -*-
"""
    @copyright: 2009 Lari Huttunen, Marko Laakso
    @license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""
import md5
import os
import sys
import cStringIO

def hashFile(f):
    """
    Expect a file name or a cStringIO.StringIO object.
    """
    try:
        data = f.read()
    except AttributeError:
        fobj = file(f,'rb')
        data = fobj.read()
        fobj.close()
    return md5.new(data).hexdigest()

def uploadFile(collab, page_name, file, file_name):
    try:
        file_obj = open(file, "rb")
    except(IOError, TypeError):
        file_obj = cStringIO.StringIO(file)
    parts_uploaded = False
    for current, total in collab.putAttachmentChunked(page_name, file_name, file_obj):
        percent = 100.0 * current / float(max(total, 1))
        status = current, total, percent
        sys.stdout.write("\rSent %d/%d bytes (%.02f%%) " % status)
        sys.stdout.write("of %s" % file_name)
        sys.stdout.flush()
        parts_uploaded = True
    if parts_uploaded == True:
        sys.stdout.write("\n")
    else:
        sys.stdout.write("Already uploaded %s\n" % file_name)
    sys.stdout.flush()
    file_obj.close()
    return parts_uploaded

def downloadFile(collab, dpath, page, attachment):
    fp = os.path.join(dpath, attachment)
    try:
        file = open(fp, "wb")
    except IOError:
        error = "Couldn't open " + fp + " for writing."
        sys.exit(error)
    sys.stdout.write("Downloading %s\n" % attachment)
    for data, current, total in collab.getAttachmentChunked(page, attachment):
        percent = 100.0 * current / float(max(total, 1))
        status = current, total, percent
        file.write(data)
        sys.stdout.write("\rreceived %d/%d bytes (%.02f%%)" % status)
        sys.stdout.flush()
    sys.stdout.write("\n")
    sys.stdout.flush()
    file.close()

