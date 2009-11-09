"""
Vulntracking utils
"""

import logging
import shelve

def main():
    s = shelve.open("vulns.shelve", "c", protocol=2)

    import nvd
    nvd.parse_nvd_data(open('nvdcve-2.0-2009.xml'), s)

    import certfivulns
    certfivulns.update_vulns(s)

    import emergingthreats
    emergingthreats.update_vulns(s)

    import metasploitsvn
    metasploitsvn.update_vulns(s)

    import milw0rm
    milw0rm.update_vulns(s)

    import osvdb
    osvdb.update_vulns(s)

    s.close()

if __name__ == "__main__":
    main()

