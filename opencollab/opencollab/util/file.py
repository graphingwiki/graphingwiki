# -*- coding: utf-8 -*-

import md5
import os
import sys

def hashFile(filename):
    f = file(filename,'rb')
    hash = md5.new(f.read()).hexdigest()
    f.close();
    return hash

def uploadFile(collab, page_name, file):
    file_name = os.path.basename(file)
    try:
        file_obj = open(file, "rb")
    except IOError:
        sys.exit(IOError)
    parts_uploaded = False
    for current, total in collab.putAttachmentChunked(page_name, file_name, file):
        percent = 100.0 * current / float(max(total, 1))
        status = current, total, percent
        sys.stdout.write("\rSent %d/%d bytes (%.02f%%) " % status)
        sys.stdout.write("of %s" % filename)
        sys.stdout.flush()
        parts_uploaded = True
    if parts_uploaded == True:
        sys.stdout.write("\n")
    else:
        sys.stdout.write("Already uploaded %s\n" % filename)
    sys.stdout.flush()
    file.close()
    return parts_uploaded
