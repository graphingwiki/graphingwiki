"""
Vulntracking utils
"""

import shelve
import sys

def main():
    import nvd, certfivulns, emergingthreats, milw0rm, osvdb, redhat_rhsa
    scraperlist = [certfivulns, emergingthreats, milw0rm, osvdb, redhat_rhsa]

    vulnshelf = shelve.open("vulns.shelve", "c", protocol=2)

    print 'doing nvd'
    import nvd
    nvd.parse_nvd_data(open('nvdcve-2.0-2009.xml'), vulnshelf)

    for scraper in scraperlist:
        print 'doing', scraper,
        sys.stdout.flush()
        scraper.update_vulns(vulnshelf)
        print '- done'

    vulnshelf.close()



if __name__ == "__main__":
    main()

