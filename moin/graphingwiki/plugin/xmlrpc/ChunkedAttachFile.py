import xmlrpclib
import md5

from graphingwiki.editing import check_attachfile

CHUNK_SIZE = 1024 * 1024

def runChecked(func, request, pagename, filename, *args, **keys):
    # Checks ACLs and the return value of the called function.
    # If the return value is None, return Fault

    _ = request.getText
    if not request.user.may.read(pagename):
        return xmlrpclib.Fault(1, _("You are not allowed to access this page"))

    result = func(request, pagename, filename, *args, **keys)
    if result is None:
        return xmlrpclib.Fault(2, "%s: %s" % (_("Nonexisting attachment"),
                                              filename))

    return result

def info(request, pagename, filename):
    try:
        fpath, exists = check_attachfile(request, pagename, filename)
        if not exists:
            return None

        stream = open(fpath, "rb")
        digest = md5.new()

        data = stream.read(CHUNK_SIZE)
        while data:
            digest.update(data)
            data = stream.read(CHUNK_SIZE)

        digest = digest.hexdigest()
        size = stream.tell()
        stream.close()
    except:
        return None

    return [digest, size]

def load(request, pagename, filename, start, end):
    try:
        fpath, exists = check_attachfile(request, pagename, filename)
        if not exists:
            return None

        stream = open(fpath, "rb")
        stream.seek(start)
        data = stream.read(max(end-start, 0))
        stream.close()
    except:
        return None

    return xmlrpclib.Binary(data)

def execute(xmlrpcobj, pagename, filename, action='info', 
            start=None, end=None):
    request = xmlrpcobj.request
    _ = request.getText

    pagename = xmlrpcobj._instr(pagename)

    if action == 'info':
        success = runChecked(info, request, pagename, filename)
    elif action == 'load' and None not in (start, end):
        success = runChecked(load, request, pagename, filename, start, end)
    else:
        success = xmlrpclib.Fault(3, _("No method specified or invalid span"))

    return success
