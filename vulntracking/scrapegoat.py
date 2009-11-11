"""
Vulntracking utils
"""

import shelve
import sys

def main():
    import nvd, certfivulns, emergingthreats, milw0rm, osvdb, redhat_rhsa, metasploitsvn, core, immunity
    vulnshelf = shelve.open("vulns.shelve", "c", protocol=2)
    if 0:
        scraperlist = [certfivulns, emergingthreats, milw0rm, osvdb, redhat_rhsa, metasploitsvn, core, immunity]

        print 'doing nvd'
        import nvd
        nvd.parse_nvd_data(open('nvdcve-2.0-2008.xml'), vulnshelf)
        nvd.parse_nvd_data(open('nvdcve-2.0-2009.xml'), vulnshelf)

        for scraper in scraperlist:
            print 'doing', scraper,
            sys.stdout.flush()
            scraper.update_vulns(vulnshelf)
            print '- done'
    else:
        #core.update_vulns(vulnshelf)
        #redhat_rhsa.update_vulns(vulnshelf)
        #metasploitsvn.update_vulns(vulnshelf)
        #milw0rm.update_vulns(vulnshelf)
        immunity.update_vulns(vulnshelf)

    vulnshelf.close()



if __name__ == "__main__":
    main()

