"""
Vulntracking utils
"""

import shelve
import sys
import scrapeutil

def main():
    import nvd, certfivulns, emergingthreats, milw0rm, osvdb, redhat_rhsa, metasploitsvn, core, immunity
    vulnshelf = shelve.open("vulns.shelve", "c", protocol=2)
    scraperlist = map(lambda sname: sys.modules[sname], sys.argv[1:])
    if not scraperlist:
        scraperlist = filter(lambda m: hasattr(m, 'update_vulns'),
                             sys.modules.values())
        scraperlist.remove(scrapeutil)
        print 'doing nvd'
        import nvd
        nvd.parse_nvd_data(open('nvdcve-2.0-2008.xml'), vulnshelf)
        nvd.parse_nvd_data(open('nvdcve-2.0-2009.xml'), vulnshelf)

    for scraper in scraperlist:
        print 'doing', scraper,
        sys.stdout.flush()
        tname, tcontent = getattr(scraper, 'wiki_template', (None, None))
        if tname and tcontent:
            vulnshelf[tname] = tcontent
                
        scraper.update_vulns(vulnshelf)
        print '- done'

    vulnshelf[scrapeutil.generic_vuln_template[0]] = scrapeutil.generic_vuln_template[1]
    vulnshelf.close()


if __name__ == "__main__":
    main()

