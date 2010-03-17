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

def uploadFile(collab, page_name, file, file_name, verbose=False):
    try:
        file_obj = open(file, "rb")
    except IOError, msg:
        raise IOError(msg)
    except TypeError:
        try:
            file_obj = cStringIO.StringIO(file)
        except IOError, msg:
            raise IOError(msg)
        except RuntimeError, msg:
            raise RuntimeError(msg)
    parts_uploaded = False
    for current, total in collab.putAttachmentChunked(page_name, file_name, file_obj):
        percent = 100.0 * current / float(max(total, 1))
        status = current, total, percent
        if verbose:
            sys.stdout.write("\rNOTE: Sent %d/%d bytes (%.02f%%) " % status)
            sys.stdout.write("of %s" % file_name)
            sys.stdout.flush()
        parts_uploaded = True
    if verbose:
        if parts_uploaded == True:
            sys.stdout.write("\n")
        else:
            sys.stdout.write("NOTE: Already uploaded %s\n" % file_name)
    sys.stdout.flush()
    file_obj.close()
    return parts_uploaded

def downloadFile(collab, page, attachment, dpath, verbose=False):
    fp = os.path.join(dpath, attachment)
    try:
        file = open(fp, "wb")
    except IOError:
        error = "ERROR: Couldn't open " + fp + " for writing."
        raise IOError(error)
    if verbose:
        print "NOTE: Downloading", attachment
    for data, current, total in collab.getAttachmentChunked(page, attachment):
        percent = 100.0 * current / float(max(total, 1))
        status = current, total, percent
        file.write(data)
        if verbose:
            sys.stdout.write("\rreceived %d/%d bytes (%.02f%%)" % status)
            sys.stdout.flush()
    if verbose:
        sys.stdout.write("\n")
    sys.stdout.flush()
    file.close()

