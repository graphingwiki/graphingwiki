from wiki import CLIWiki
from meta import Meta

def main():
    import os
    import sys
    import optparse

    parser = optparse.OptionParser()
    parser.add_option("-o", "--output",
                      dest="output",
                      default=None,
                      metavar="OUTPUT",
                      help="save the file to name OUTPUT in the wiki")

    parser.set_usage("%prog [options] WIKIURL PAGENAME FILENAME")

    options, args = parser.parse_args()
    if len(args) != 3:
        parser.error("wiki url, pagename and filename have to be defined")

    url, page, path = args

    if options.output is None:
        _, filename = os.path.split(path)
    else:
        filename = options.output

    file = open(path, "rb")
    wiki = CLIWiki(url)
    
    sys.stdout.write("\rconnecting & precalculating chunks...")
    sys.stdout.flush()

    for current, total in wiki.putAttachmentChunked(page, filename, file):
        percent = 100.0 * current / float(max(total, 1))
        status = current, total, percent

        sys.stdout.write("\rsent %d/%d bytes (%.02f%%)" % status)
        sys.stdout.flush()

    sys.stdout.write("\ndone\n")
    sys.stdout.flush()

    file.close()

if __name__ == "__main__":
    main()
