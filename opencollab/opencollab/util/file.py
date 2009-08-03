# -*- coding: utf-8 -*-

import md5
import os
import sys
import cStringIO

def hashFile(f):
    """
    Expect a file name or a cStringIO.StringIO object.
    """
    try:
        fobj = f.read()
        hash = md5.new(fobj.hexdigest())
    except AttributeError:
        fobj = file(f,'rb')
        hash = md5.new(fobj.read()).hexdigest()
    fobj.close();
    return hash

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
