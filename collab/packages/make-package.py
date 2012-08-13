import zipfile
import sys
import time
import os

def createPackage(dirName, packageName):
    manifest = open(os.path.join(dirName, "MOIN_PACKAGE"), "r")
    manifestLines = list()

    archived = list()
    visibility = set()

    for line in manifest:
        line = line.strip()
        if not line:
            continue
        
        split = line.split("|")
        key, rest = split[0], split[1:]
        
        if key in ("InstallPlugin", 
                   "CopyThemeFile", 
                   "AddRevision",
                   "AddAttachment",
                   "ReplaceUnderlay"):
            archived.append(rest[0])

        if key == "InstallPlugin":
            visibility.add(rest[1])
        elif key == "ReplaceUnderlay":
            visibility.add("global")
        elif key == "AddRevision":
            visibility.add("local")
            
        manifestLines.append(line)

    timeStamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    manifestLines.append("Print|Installed %s" % packageName)
    manifestLines.append("Print|Packaged %s" % timeStamp)

    if visibility == set(["local"]):
        manifestLines.append("AddRevision|%s|%s" % (packageName, packageName))
    elif visibility == set(["global"]):
        manifestLines.append("ReplaceUnderlay|%s|%s" % (packageName, packageName))
    else:
        sys.exit("Unsupported visibility.\n")

    packagePage = ""
    packagePage += " name:: %s\n" % packageName
    packagePage += " packaged:: %s\n" % timeStamp
    packagePage += "----\n"
    packagePage += "CategoryPackage\n"

    zipFile = zipfile.ZipFile(packageName + ".zip", "w")
    zipFile.writestr("MOIN_PACKAGE", "\n".join(manifestLines))
    zipFile.writestr(packageName, packagePage)
    for fileName in archived:
        joinedName = os.path.join(dirName, fileName)
        zipFile.write(joinedName, fileName)
    zipFile.close()

if __name__ == "__main__":
    for dirName in sys.argv[1:]:
        _, packageName = os.path.split(dirName)
        
        template = "Packaging directory %s into package %s.zip"
        print template % (dirName, packageName)

        createPackage(dirName, packageName)

